from django.db import models

class BacktestResult(models.Model):
    """
    Stores overall results of a complete backtest run.
    Each record represents one strategy test on one stock symbol.
    
    Fields:
        stock_tested (CharField): Stock symbol being tested (e.g., 'AAPL', 'GOOGL')
        trade_test_start_date (DateTimeField): Start date/time of the backtest period
        trade_test_end_date (DateTimeField): End date/time of the backtest period
        stop_loss (DecimalField): Stop-loss percentage used in strategy (e.g., 1.00 = 1%)
        take_profit (DecimalField): Take-profit percentage used in strategy (e.g., 50.00 = 50%)
        created_at (DateTimeField): Timestamp when this record was created
        updated_at (DateTimeField): Timestamp when this record was last modified
        starting_amount (DecimalField): Initial capital at start of backtest ($)
        closing_amount (DecimalField): Final capital at end of backtest ($)
        total_profit (DecimalField): Net profit/loss from all trades ($)
        number_of_trades (IntegerField): Total number of completed trade cycles
        total_returns (DecimalField): Overall return percentage (e.g., 25.50 = 25.5%)
        peak_stock_value (DecimalField): Highest portfolio value reached during backtest ($)
        lowest_stock_value (DecimalField): Lowest portfolio value reached during backtest ($)
        drawdown (DecimalField): Maximum drawdown percentage from peak (e.g., -15.25 = -15.25%)
    
    Usage:
        This model stores summary statistics for each complete backtest run.
        Used for comparing strategy performance across different stocks, parameters, and time periods.
    """
    stock_tested = models.CharField(max_length=200)
    trade_test_start_date = models.DateTimeField()
    trade_test_end_date = models.DateTimeField()
    stop_loss = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Stop-loss percentage, e.g. 5.00 means 5%"
    )
    take_profit = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Take-profit percentage, e.g. 15.00 means 15%"
    )
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    starting_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Starting amount in $"
    )
    closing_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="closing amount in $"
    )
    total_profit = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Total Profit in $"
    )
    number_of_trades = models.IntegerField()
    total_returns = models.DecimalField(
        max_digits=7, decimal_places=2,
        help_text="Total returns in % , e.g. 15.00 means 15%"
    )
    peak_stock_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="peak_stock_value in $"
    )
    lowest_stock_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="lowest_stock_value in $"
    )
    drawdown = models.DecimalField(
        max_digits=7, decimal_places=2,
        help_text="Drawdown in % , e.g. 15.00 means 15%"
    )

    def __str__(self):
        return f"{self.stock_tested} backtest ({self.trade_test_start_date.date()} to {self.trade_test_end_date.date()})"


class Trade(models.Model):
    """
    Stores individual trade cycles (buy -> sell).
    Each record represents one complete trade or open position.
    
    Fields:
        backtest (ForeignKey): Reference to the BacktestResult this trade belongs to
        stock_symbol (CharField): Stock symbol for this trade (e.g., 'AAPL')
        entry_date (DateTimeField): Date/time when position was opened (BUY)
        entry_price (DecimalField): Price per share when position was opened ($)
        quantity (IntegerField): Number of shares purchased
        exit_date (DateTimeField): Date/time when position was closed (SELL), null if still open
        exit_price (DecimalField): Price per share when position was closed ($), null if still open
        final_market_price (DecimalField): Last known market price for open positions ($)
        created_at (DateTimeField): Timestamp when this record was created
        updated_at (DateTimeField): Timestamp when this record was last modified
    
    Methods:
        get_profit(): Calculates profit/loss for this trade ($)
        is_open(): Returns True if position is still open, False if closed
    
    Usage:
        Each record represents either:
        1. Complete trade cycle: entry_date, entry_price, exit_date, exit_price all filled
        2. Open position: exit_date and exit_price are null, final_market_price used for valuation
    """
    backtest = models.ForeignKey(BacktestResult, on_delete=models.CASCADE)
    stock_symbol = models.CharField(max_length=10)
    
    # Entry (BUY)
    entry_date = models.DateTimeField()
    entry_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    
    # Exit (SELL) 
    exit_date = models.DateTimeField(null=True, blank=True)
    exit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # For open positions - store final market price
    final_market_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_profit(self):
        """Calculate profit/loss for this trade"""
        if self.exit_price:  # Closed trade
            return (self.exit_price - self.entry_price) * self.quantity
        else:  # Open position
            return (self.final_market_price - self.entry_price) * self.quantity
    
    def is_open(self):
        """Check if this trade is still open"""
        return self.exit_date is None
    
    def __str__(self):
        status = "Open" if self.is_open() else "Closed"
        return f"{self.stock_symbol} {status} Trade - {self.quantity} shares at ${self.entry_price}"


class DailyPortfolioSnapshot(models.Model):
    """
    Daily snapshot of portfolio performance during backtest.
    Used for calculating Sharpe ratio and detailed performance metrics.
    
    Fields:
        backtest (ForeignKey): Reference to the BacktestResult this snapshot belongs to
        date (DateField): Date of this portfolio snapshot
        total_portfolio_value (DecimalField): Total value of cash + all stock positions ($)
        cash_balance (DecimalField): Available uninvested cash ($)
        daily_return (DecimalField): Daily return percentage (e.g., 2.50 = 2.5% gain)
        peak_portfolio_value (DecimalField): Highest portfolio value reached up to this date ($)
        drawdown (DecimalField): Current drawdown from peak (e.g., -5.25 = -5.25% down from peak)
        open_positions_count (IntegerField): Number of different stocks held on this date
        created_at (DateTimeField): Timestamp when this record was created
        updated_at (DateTimeField): Timestamp when this record was last modified
    
    Meta:
        unique_together: Ensures only one snapshot per backtest per date
        ordering: Records ordered chronologically by date
    
    Usage:
        One record created for each trading day during backtest period.
        Essential for calculating risk metrics like Sharpe ratio, maximum drawdown, volatility.
        Allows reconstruction of portfolio performance over time.
    """
    backtest = models.ForeignKey(BacktestResult, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Core portfolio metrics
    total_portfolio_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Total value of cash + all positions"
    )
    cash_balance = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Available cash"
    )
    
    # Daily performance
    daily_return = models.DecimalField(
        max_digits=7, decimal_places=2,
        help_text="Daily return percentage"
    )
    
    # Advanced metrics for detailed analysis
    peak_portfolio_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Highest portfolio value reached so far"
    )
    drawdown = models.DecimalField(
        max_digits=7, decimal_places=2,
        help_text="Current drawdown from peak in %"
    )
    
    open_positions_count = models.IntegerField(
        help_text="Number of different stocks currently held"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['backtest', 'date']  # One snapshot per day per backtest
        ordering = ['date']
    
    def __str__(self):
        return f"{self.backtest.stock_tested} - {self.date}: ${self.total_portfolio_value}"