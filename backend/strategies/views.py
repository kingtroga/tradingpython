import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal
import pandas as pd
from datetime import datetime, timedelta


# ✅ NEW: lumibot import
# YahooData is the simplest drop-in replacement for yfinance historical bars.
# pip install lumibot
try:
    from lumibot.data_sources.yahoo_data import YahooData
    from lumibot.entities import Asset
except ImportError as e:
    raise ImportError(
        "Lumibot is required. Install with `pip install lumibot`.\n"
        f"Original error: {e}"
    )

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from .models import BacktestResult, Trade, DailyPortfolioSnapshot
from .serializers import (
    BacktestResultSerializer, 
    TradeSerializer, 
    DailyPortfolioSnapshotSerializer,
    BacktestCreateSerializer
)

class BacktestResultViewSet(viewsets.ModelViewSet):
    queryset = BacktestResult.objects.all()
    serializer_class = BacktestResultSerializer

    @action(detail=False, methods=['post'])
    def run_backtest(self, request):
        """Run a new backtest"""
        serializer = BacktestCreateSerializer(data=request.data)
        if serializer.is_valid():
            result = self._execute_backtest(serializer.validated_data)
            return Response(BacktestResultSerializer(result).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def trades(self, request, pk=None):
        """Get trades for a specific backtest"""
        backtest = self.get_object()
        trades = Trade.objects.filter(backtest=backtest)
        serializer = TradeSerializer(trades, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def daily_snapshots(self, request, pk=None):
        """Get daily snapshots for charts"""
        backtest = self.get_object()
        snapshots = DailyPortfolioSnapshot.objects.filter(backtest=backtest)
        serializer = DailyPortfolioSnapshotSerializer(snapshots, many=True)
        return Response(serializer.data)

    # ✅ NEW: Lumibot data download + normalization
    def _download_data_with_lumibot(self, symbol, start_date, end_date):
        """
        Fetch OHLCV data via Lumibot's YahooData and normalize to:
        index: DatetimeIndex (tz-naive)
        columns: ['Open','High','Low','Close','Adj Close','Volume'] (subset ok)
        """
        logger.info(f"Fetching data via Lumibot YahooData for {symbol} {start_date} -> {end_date}")

        ds = YahooData()

        # Convert incoming date or datetime to datetime (midnight)
        start_dt = start_date if isinstance(start_date, datetime) else datetime.combine(start_date, datetime.min.time())
        end_dt = end_date if isinstance(end_date, datetime) else datetime.combine(end_date, datetime.min.time())

        # Lumibot wants a 'length' (# of bars) + timestep, not start/end.
        # We'll over-fetch by a small buffer, then slice the exact date range.
        # Count *calendar* days between, add buffer, and let Yahoo fill only trading days.
        days = (end_dt - start_dt).days + 1
        length = max(days + 5, 30)  # small buffer

        # Build an Asset and pull daily bars
        asset = Asset(symbol, asset_type="stock")
        bars = ds.get_historical_prices(
            asset=asset,
            length=length,
            timestep="day",            # YahooData.MIN_TIMESTEP = 'day'
            include_after_hours=True,  # safe default for daily
        )

        if bars is None:
            raise ValueError(f"No data returned for {symbol} using Lumibot YahooData.")

        df = bars.df.copy()

        if df is None or df.empty:
            raise ValueError(f"No data found for {symbol} using Lumibot YahooData.")

        # Normalize columns: open/high/low/close/volume -> Title Case
        rename_map = {}
        for c in df.columns:
            lc = c.lower().replace(" ", "").replace("_", "")
            if lc == "open": rename_map[c] = "Open"
            elif lc == "high": rename_map[c] = "High"
            elif lc == "low": rename_map[c] = "Low"
            elif lc == "close": rename_map[c] = "Close"
            elif lc in ("adjclose", "adjustedclose", "adjustclose"): rename_map[c] = "Adj Close"
            elif lc == "volume": rename_map[c] = "Volume"
        df = df.rename(columns=rename_map)

        if "Close" not in df.columns:
            raise ValueError("Downloaded data does not contain a 'Close' column after normalization.")

        # Index comes tz-aware (America/New_York); convert to tz-naive for your code
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)

        df = df.sort_index()

        # Slice to your exact [start_dt, end_dt] range (inclusive)
        df = df[(df.index >= start_dt) & (df.index <= end_dt)]
        if df.empty:
            raise ValueError(f"No rows for {symbol} in range {start_dt.date()} to {end_dt.date()}.")

        logger.info(f"Downloaded {len(df)} rows via Lumibot (post-slice)")
        logger.debug(f"Columns after normalization: {list(df.columns)}")
        return df

    def _execute_backtest(self, params):
        """Execute the moving average crossover backtest with debug logging"""
        logger.info(f"Starting backtest for {params['stock_symbol']}")

        try:
            # ✅ REPLACED: fetch data via Lumibot (YahooData)
            stock_data = self._download_data_with_lumibot(
                params['stock_symbol'],
                params['start_date'],
                params['end_date'],
            )

            logger.info(f"Downloaded {len(stock_data)} rows of data")
            logger.info(f"Stock data type: {type(stock_data)}")
            logger.info(f"Stock data columns: {stock_data.columns.tolist()}")

            if len(stock_data) == 0:
                raise ValueError(f"No data found for {params['stock_symbol']}")

            # Flatten MultiIndex if any (rare with our normalization, but safe)
            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data.columns = [col[0] for col in stock_data.columns]
                logger.info(f"Flattened MultiIndex columns: {stock_data.columns.tolist()}")

            # Calculate moving averages
            stock_data['SMA_short'] = stock_data['Close'].rolling(params['short_period']).mean()
            stock_data['SMA_long'] = stock_data['Close'].rolling(params['long_period']).mean()

            logger.info("Moving averages calculated")

            # Create backtest result
            backtest = BacktestResult.objects.create(
                stock_tested=params['stock_symbol'],
                trade_test_start_date=timezone.make_aware(datetime.combine(params['start_date'], datetime.min.time())),
                trade_test_end_date=timezone.make_aware(datetime.combine(params['end_date'], datetime.min.time())),
                stop_loss=params['stop_loss_percentage'],
                take_profit=params['take_profit_percentage'],
                starting_amount=params['starting_amount'],
                closing_amount=params['starting_amount'],
                total_profit=Decimal('0.00'),
                number_of_trades=0,
                total_returns=Decimal('0.00'),
                peak_stock_value=params['starting_amount'],
                lowest_stock_value=params['starting_amount'],
                drawdown=Decimal('0.00')
            )

            logger.info(f"Created backtest record with ID: {backtest.id}")

            # Run backtest simulation
            cash = float(params['starting_amount'])
            position = None  # Explicitly set to None
            portfolio_value = cash
            peak_value = cash
            trades_count = 0

            logger.info("Starting simulation loop")

            for i, (date, row) in enumerate(stock_data.iterrows()):
                logger.debug(f"Processing day {i}: {date}")
                logger.debug(f"Position type at start of loop: {type(position)}")
                logger.debug(f"Position value: {position}")

                if pd.isna(row['SMA_short']) or pd.isna(row['SMA_long']):
                    logger.debug("Skipping day due to NaN moving averages")
                    continue

                current_price = float(row['Close'])
                logger.debug(f"Current price: {current_price}, type: {type(current_price)}")

                # Calculate portfolio value
                logger.debug("About to check position for portfolio calculation")
                if position is not None:
                    logger.debug("Position exists, calculating portfolio value")
                    portfolio_value = cash + (position['quantity'] * current_price)
                else:
                    logger.debug("No position, portfolio = cash")
                    portfolio_value = cash

                # Update peak and calculate drawdown
                if portfolio_value > peak_value:
                    peak_value = portfolio_value

                drawdown = ((peak_value - portfolio_value) / peak_value) * 100 if peak_value > 0 else 0

                # Create daily snapshot
                try:
                    daily_return_pct = 0.00
                    if i == 0:
                        daily_return_pct = 0.00
                    else:
                        prev_snapshots = DailyPortfolioSnapshot.objects.filter(backtest=backtest).order_by('-date')
                        if prev_snapshots.exists():
                            prev_value = float(prev_snapshots.first().total_portfolio_value)
                            daily_return_pct = ((portfolio_value - prev_value) / prev_value) * 100
                        else:
                            daily_return_pct = 0.00
                    DailyPortfolioSnapshot.objects.create(
                        backtest=backtest,
                        date=date.date(),
                        total_portfolio_value=Decimal(str(round(portfolio_value, 2))),
                        cash_balance=Decimal(str(round(cash, 2))),
                        daily_return=Decimal(str(daily_return_pct)),
                        peak_portfolio_value=Decimal(str(round(peak_value, 2))),
                        drawdown=Decimal(str(round(drawdown, 2))),
                        open_positions_count=1 if position is not None else 0
                    )
                    logger.debug("Daily snapshot created successfully")
                except Exception as e:
                    logger.error(f"Error creating daily snapshot: {e}")
                    raise

                # Check stop-loss/take-profit
                logger.debug("About to check stop-loss/take-profit")
                if position is not None:
                    logger.debug("Checking stop-loss/take-profit for existing position")
                    entry_price = position['entry_price']
                    stop_price = entry_price * (1 - params['stop_loss_percentage'] / 100)
                    take_profit_price = entry_price * (1 + params['take_profit_percentage'] / 100)

                    if current_price <= stop_price or current_price >= take_profit_price:
                        logger.debug("Stop-loss or take-profit triggered")
                        cash += position['quantity'] * current_price
                        Trade.objects.create(
                            backtest=backtest,
                            stock_symbol=params['stock_symbol'],
                            entry_date=position['entry_date'],
                            entry_price=Decimal(str(position['entry_price'])),
                            quantity=position['quantity'],
                            exit_date=timezone.make_aware(datetime.combine(date.date(), datetime.min.time())),
                            exit_price=Decimal(str(current_price))
                        )
                        trades_count += 1
                        position = None  # Explicitly set to None
                        logger.debug("Position closed due to stop-loss/take-profit")
                        continue

                # Check for crossover signals
                logger.debug("About to check crossover signals")
                if i > 0:
                    prev_row = stock_data.iloc[i-1]
                    logger.debug(f"Previous row type: {type(prev_row)}")
                    logger.debug(f"Current row type: {type(row)}")

                    if pd.isna(prev_row['SMA_short']) or pd.isna(prev_row['SMA_long']):
                        logger.debug("Skipping crossover check due to NaN in previous row")
                        continue

                    # Extract scalar values to avoid Series comparison
                    prev_short = float(prev_row['SMA_short'])
                    prev_long = float(prev_row['SMA_long'])
                    curr_short = float(row['SMA_short'])
                    curr_long = float(row['SMA_long'])

                    logger.debug(f"MA values - Prev: {prev_short:.2f}/{prev_long:.2f}, Curr: {curr_short:.2f}/{curr_long:.2f}")

                    # Golden Cross - Buy
                    if (prev_short <= prev_long and curr_short > curr_long and position is None):
                        logger.debug("Golden Cross detected!")
                        shares_to_buy = int(cash / current_price)
                        if shares_to_buy > 0:
                            position = {
                                'quantity': shares_to_buy,
                                'entry_price': float(current_price),
                                'entry_date': timezone.make_aware(datetime.combine(date.date(), datetime.min.time()))
                            }
                            cash -= shares_to_buy * current_price
                            logger.debug(f"Bought {shares_to_buy} shares at ${current_price}")

                    # Death Cross - Sell
                    elif (prev_short >= prev_long and curr_short < curr_long and position is not None):
                        logger.debug("Death Cross detected!")
                        cash += position['quantity'] * current_price
                        Trade.objects.create(
                            backtest=backtest,
                            stock_symbol=params['stock_symbol'],
                            entry_date=position['entry_date'],
                            entry_price=Decimal(str(position['entry_price'])),
                            quantity=position['quantity'],
                            exit_date=timezone.make_aware(datetime.combine(date.date(), datetime.min.time())),
                            exit_price=Decimal(str(current_price))
                        )
                        trades_count += 1
                        position = None  # Explicitly set to None
                        logger.debug(f"Sold position at ${current_price}")

                logger.debug(f"End of loop iteration {i}")

            logger.info("Simulation loop completed")

            # Close any remaining position
            if position is not None:
                logger.info("Closing remaining position")
                final_price = float(stock_data['Close'].iloc[-1])
                cash += position['quantity'] * final_price
                final_date = timezone.make_aware(datetime.combine(stock_data.index[-1].date(), datetime.min.time()))
                Trade.objects.create(
                    backtest=backtest,
                    stock_symbol=params['stock_symbol'],
                    entry_date=position['entry_date'],
                    entry_price=Decimal(str(position['entry_price'])),
                    quantity=position['quantity'],
                    exit_date=final_date,
                    exit_price=Decimal(str(final_price))
                )
                trades_count += 1

            # Update backtest results
            final_value = cash
            profit = final_value - float(params['starting_amount'])
            returns = (profit / float(params['starting_amount'])) * 100

            backtest.closing_amount = Decimal(str(round(final_value, 2)))
            backtest.total_profit = Decimal(str(round(profit, 2)))
            backtest.number_of_trades = trades_count
            backtest.total_returns = Decimal(str(round(returns, 2)))
            backtest.peak_stock_value = Decimal(str(round(peak_value, 2)))
            backtest.lowest_stock_value = Decimal(str(round(min(portfolio_value, float(params['starting_amount'])), 2)))
            backtest.drawdown = Decimal(str(round(((peak_value - final_value) / peak_value) * 100, 2)))
            backtest.save()

            logger.info(f"Backtest completed successfully for {params['stock_symbol']}")
            logger.info(f"Final results: {trades_count} trades, ${profit:.2f} profit")

            return backtest

        except Exception as e:
            logger.error(f"Error in backtest execution: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer

class DailyPortfolioSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DailyPortfolioSnapshot.objects.all()
    serializer_class = DailyPortfolioSnapshotSerializer
