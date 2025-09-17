from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

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

    def _execute_backtest(self, params):
        """Execute the moving average crossover backtest"""
        # Download stock data
        stock_data = yf.download(
            params['stock_symbol'], 
            start=params['start_date'], 
            end=params['end_date'],
            progress=False
        )
        
        if stock_data.empty:
            raise ValueError(f"No data found for {params['stock_symbol']}")

        # Calculate moving averages
        stock_data['SMA_short'] = stock_data['Close'].rolling(params['short_period']).mean()
        stock_data['SMA_long'] = stock_data['Close'].rolling(params['long_period']).mean()
        
        # Create backtest result
        backtest = BacktestResult.objects.create(
            stock_tested=params['stock_symbol'],
            trade_test_start_date=params['start_date'],
            trade_test_end_date=params['end_date'],
            stop_loss=params['stop_loss_percentage'],
            take_profit=params['take_profit_percentage'],
            starting_amount=params['starting_amount'],
            closing_amount=params['starting_amount'],  # Will update
            total_profit=Decimal('0.00'),
            number_of_trades=0,
            total_returns=Decimal('0.00'),
            peak_stock_value=params['starting_amount'],
            lowest_stock_value=params['starting_amount'],
            drawdown=Decimal('0.00')
        )
        
        # Run backtest simulation
        cash = float(params['starting_amount'])
        position = None
        portfolio_value = cash
        peak_value = cash
        trades_count = 0
        
        for i, (date, row) in enumerate(stock_data.iterrows()):
            if pd.isna(row['SMA_short']) or pd.isna(row['SMA_long']):
                continue
                
            current_price = row['Close']
            
            # Calculate portfolio value
            if position:
                portfolio_value = cash + (position['quantity'] * current_price)
            else:
                portfolio_value = cash
            
            # Update peak and calculate drawdown
            if portfolio_value > peak_value:
                peak_value = portfolio_value
            
            drawdown = ((peak_value - portfolio_value) / peak_value) * 100 if peak_value > 0 else 0
            
            # Create daily snapshot
            DailyPortfolioSnapshot.objects.create(
                backtest=backtest,
                date=date.date(),
                total_portfolio_value=Decimal(str(round(portfolio_value, 2))),
                cash_balance=Decimal(str(round(cash, 2))),
                daily_return=Decimal('0.00'),  # Calculate properly if needed
                peak_portfolio_value=Decimal(str(round(peak_value, 2))),
                drawdown=Decimal(str(round(drawdown, 2))),
                open_positions_count=1 if position else 0
            )
            
            # Check stop-loss/take-profit
            if position:
                entry_price = position['entry_price']
                stop_price = entry_price * (1 - params['stop_loss_percentage'] / 100)
                take_profit_price = entry_price * (1 + params['take_profit_percentage'] / 100)
                
                if current_price <= stop_price or current_price >= take_profit_price:
                    # Close position
                    cash += position['quantity'] * current_price
                    Trade.objects.create(
                        backtest=backtest,
                        stock_symbol=params['stock_symbol'],
                        entry_date=position['entry_date'],
                        entry_price=Decimal(str(position['entry_price'])),
                        quantity=position['quantity'],
                        exit_date=date,
                        exit_price=Decimal(str(current_price))
                    )
                    trades_count += 1
                    position = None
                    continue
            
            # Check for crossover signals
            if i > 0:
                prev_row = stock_data.iloc[i-1]
                if pd.isna(prev_row['SMA_short']) or pd.isna(prev_row['SMA_long']):
                    continue
                
                # Golden Cross - Buy
                if (prev_row['SMA_short'] <= prev_row['SMA_long'] and 
                    row['SMA_short'] > row['SMA_long'] and 
                    not position):
                    
                    shares_to_buy = int(cash / current_price)
                    if shares_to_buy > 0:
                        position = {
                            'quantity': shares_to_buy,
                            'entry_price': current_price,
                            'entry_date': date
                        }
                        cash -= shares_to_buy * current_price
                
                # Death Cross - Sell
                elif (prev_row['SMA_short'] >= prev_row['SMA_long'] and 
                      row['SMA_short'] < row['SMA_long'] and 
                      position):
                    
                    cash += position['quantity'] * current_price
                    Trade.objects.create(
                        backtest=backtest,
                        stock_symbol=params['stock_symbol'],
                        entry_date=position['entry_date'],
                        entry_price=Decimal(str(position['entry_price'])),
                        quantity=position['quantity'],
                        exit_date=date,
                        exit_price=Decimal(str(current_price))
                    )
                    trades_count += 1
                    position = None
        
        # Close any remaining position
        if position:
            final_price = stock_data['Close'].iloc[-1]
            cash += position['quantity'] * final_price
            Trade.objects.create(
                backtest=backtest,
                stock_symbol=params['stock_symbol'],
                entry_date=position['entry_date'],
                entry_price=Decimal(str(position['entry_price'])),
                quantity=position['quantity'],
                exit_date=stock_data.index[-1],
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
        
        return backtest

class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer

class DailyPortfolioSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DailyPortfolioSnapshot.objects.all()
    serializer_class = DailyPortfolioSnapshotSerializer