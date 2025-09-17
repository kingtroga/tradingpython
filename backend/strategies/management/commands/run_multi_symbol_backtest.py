from django.core.management.base import BaseCommand
from strategies.models import BacktestResult
from strategies.views import BacktestResultViewSet
from datetime import datetime

class Command(BaseCommand):
    help = 'Run backtests on multiple symbols for comparison'

    def handle(self, *args, **options):
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        
        viewset = BacktestResultViewSet()
        
        for symbol in symbols:
            self.stdout.write(f'Running backtest for {symbol}...')
            
            params = {
                'stock_symbol': symbol,
                'start_date': datetime(2023, 1, 1).date(),
                'end_date': datetime(2023, 12, 31).date(),
                'short_period': 20,
                'long_period': 50,
                'stop_loss_percentage': 1.00,
                'take_profit_percentage': 50.00,
                'starting_amount': 10000.00
            }
            
            try:
                result = viewset._execute_backtest(params)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{symbol}: ${result.total_profit:.2f} profit, {result.total_returns:.2f}% return'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed for {symbol}: {str(e)}')
                )
        
        self.stdout.write('Multi-symbol backtest complete!')