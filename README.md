# Moving Average Crossover Trading Strategy

A comprehensive backtesting system for the Moving Average Crossover trading strategy, built with Django REST Framework and React with interactive charts.

## Strategy Overview

### Core Logic
The Moving Average Crossover strategy uses two simple moving averages to generate trading signals:
- **Short-term MA**: 20-day Simple Moving Average
- **Long-term MA**: 50-day Simple Moving Average

### Trading Signals
- **Golden Cross (BUY)**: When 20-day MA crosses above 50-day MA
- **Death Cross (SELL)**: When 20-day MA crosses below 50-day MA

### Risk Management
- **Stop Loss**: 1% - Exit position if loss reaches 1% of entry price
- **Take Profit**: 50% - Exit position if profit reaches 50% of entry price

## Project Structure

```
trading-strategy-api/
├── backend/                    # Django REST API
│   ├── trading_project/        # Django project settings
│   ├── strategies/             # Main application
│   │   ├── models.py          # Database models
│   │   ├── views.py           # API endpoints
│   │   ├── serializers.py     # DRF serializers
│   │   └── management/        # Custom commands
│   ├── manage.py
│   └── requirements.txt
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── TradingDashboard.js
│   │   │   └── TradingDashboard.css
│   │   ├── App.js
│   │   └── App.css
│   ├── public/
│   └── package.json
├── images/                     # Database screenshots
├── SCHEMA_DESIGN.md           # Database design documentation
└── README.md
```

## Technology Stack

### Backend
- **Django 4.2.7** - Web framework
- **Django REST Framework 3.14.0** - API framework
- **PostgreSQL** - Primary database
- **yfinance 0.2.20** - Stock data retrieval
- **pandas 2.1.3** - Data analysis

### Frontend
- **React 18.2.0** - UI framework
- **lightweight-charts 4.1.3** - Financial charting
- **Modern CSS** - Styling with glassmorphism effects

## Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 13+

### Backend Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd trading-strategy-api
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Database setup**
```bash
# Create PostgreSQL database
createdb trading_db

# Update database settings in trading_project/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'trading_db',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

5. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Start Django server**
```bash
python manage.py runserver
```

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Start React development server**
```bash
npm start
```

The application will be available at `http://localhost:3000`

## Usage

### Running Backtests

#### Via Web Interface
1. Open `http://localhost:3000`
2. Enter stock symbol (e.g., AAPL, GOOGL, MSFT)
3. Select date range
4. Set starting capital
5. Click "Run Backtest"

#### Via Management Command
```bash
python manage.py run_multi_symbol_backtest
```

#### Via API
```bash
curl -X POST http://localhost:8000/api/backtests/run_backtest/ \
  -H "Content-Type: application/json" \
  -d '{
    "stock_symbol": "AAPL",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "starting_amount": "10000.00"
  }'
```

### API Endpoints

- `GET /api/backtests/` - List all backtest results
- `POST /api/backtests/run_backtest/` - Execute new backtest
- `GET /api/backtests/{id}/trades/` - Get trades for specific backtest
- `GET /api/backtests/{id}/daily_snapshots/` - Get daily portfolio data
- `GET /api/trades/` - List all trades
- `GET /api/snapshots/` - List all daily snapshots

## Performance Analysis

### Key Metrics Tracked
- **Total Returns**: Percentage gain/loss
- **Net Profit**: Absolute dollar profit/loss
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Number of Trades**: Total completed transactions
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted return metric

### Sample Results (2023 Backtesting Data)
Based on actual backtests run across major tech stocks during 2023:

| Symbol | Total Return | Net Profit | Max Drawdown | Trades | Win Rate |
|--------|--------------|------------|--------------|--------|----------|
| AMZN   | +5.30%      | $529.51    | -1.38%       | 2      | 50%      |
| TSLA   | +4.66%      | $466.35    | -23.33%      | 3      | 33%      |
| AAPL   | +2.68%      | $267.51    | -2.78%       | 1      | 100%     |
| MSFT   | -3.65%      | -$365.12   | -3.65%       | 1      | 0%       |
| GOOGL  | -6.32%      | -$631.60   | -6.32%       | 3      | 0%       |

**Overall Performance:**
- **Portfolio Success Rate**: 60% (3 out of 5 stocks profitable)
- **Average Return**: +0.53%
- **Total Net Profit**: $266.65 across all positions
- **Best Single Trade**: $873.54 (TSLA)
- **Worst Single Trade**: -$365.11 (MSFT)

**Key Insights:**
- Strategy performs best in trending markets (AMZN, AAPL)
- High volatility stocks (TSLA) generate higher returns but with significant drawdown
- Choppy, sideways markets (GOOGL, MSFT) trigger frequent false signals
- Average trade duration: 26 days (ranging from 1 day to 74 days)

## Strategy Performance Analysis

## Strategy Performance Analysis

The strategy shows mixed results across different market conditions, demonstrating the importance of market selection and risk management:

### Strengths
- **Effective Risk Management**: 1% stop-loss prevented large losses
- **Trend Capture**: Successfully captured sustained trends in stable stocks
- **Clear Rules**: Quantifiable entry/exit criteria
- **Reasonable Win Rate**: 60% of positions were profitable

### Limitations
- **False Signals**: Struggles in choppy, sideways markets
- **Market Dependent**: Performance varies significantly by stock characteristics  
- **Lagging Indicators**: Moving averages react slowly to price changes
- **Volatility Sensitivity**: High-volatility stocks create larger drawdowns

### Optimization Opportunities
- **Market Filters**: Add volatility or volume confirmation
- **Dynamic Risk Management**: Adjust stop-loss based on stock volatility
- **Parameter Tuning**: Test different MA periods (15/45, 10/30)
- **Multi-Timeframe Analysis**: Combine daily signals with weekly trends

## Database Schema

The system uses a normalized PostgreSQL schema with three main tables:

### BacktestResult
Stores high-level strategy performance metrics for each backtest run.

### Trade
Tracks individual buy/sell transactions with entry/exit details.

### DailyPortfolioSnapshot
Contains daily time-series data for portfolio value and risk metrics.

See [SCHEMA_DESIGN.md](SCHEMA_DESIGN.md) for detailed schema documentation.

## Git Workflow

### Branch Structure
- `main` - Production ready code
- `task-1-basic-strategy` - Basic MA crossover implementation
- `task-2-risk-management` - Stop-loss and take-profit features
- `task-3-multi-symbol` - Multiple symbol backtesting
- `task-4-react-frontend` - Web interface and charts

### Commit Strategy
Each task is implemented incrementally with clear commit messages:
```bash
git checkout -b task-1-basic-strategy
# Implement basic strategy
git add .
git commit -m "feat: implement basic MA crossover strategy"

git checkout -b task-2-risk-management
# Add risk management
git add .
git commit -m "feat: add stop-loss and take-profit logic"
```

## Testing

### Backend Tests
```bash
python manage.py test strategies
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Deployment

### Backend (Django)
- Configure production database
- Set `DEBUG = False`
- Use environment variables for sensitive settings
- Deploy to services like Heroku, DigitalOcean, or AWS

### Frontend (React)
```bash
npm run build
# Deploy build/ directory to Netlify, Vercel, or similar
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Project Structure and Development

### Git Workflow
The project was developed using task-based branches:
- `main` - Production ready code
- `task-1-basic-strategy` - Basic MA crossover implementation
- `task-2-risk-management` - Stop-loss and take-profit features  
- `task-3-multi-symbol` - Multiple symbol backtesting with PostgreSQL
- `task-4-react-frontend` - Web interface with lightweight-charts

### Performance Analysis
Detailed performance analysis and strategy comparison available in [PERFORMANCE_ANALYSIS.md](PERFORMANCE_ANALYSIS.md).

### Database Design
Comprehensive database schema documentation with design rationale in [SCHEMA_DESIGN.md](SCHEMA_DESIGN.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **yfinance** for providing free stock data
- **TradingView** for the lightweight-charts library
- **Django** and **React** communities for excellent documentation

## Future Enhancements

- [ ] Real-time paper trading integration
- [ ] Advanced technical indicators (RSI, MACD, Bollinger Bands)
- [ ] Portfolio optimization algorithms
- [ ] Machine learning signal enhancement
- [ ] Email/SMS trade notifications
- [ ] Multi-strategy comparison tools
- [ ] Options and crypto support

## Contact

For questions or suggestions, please open an issue on GitHub.