import React, { useState, useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import './TradingDashboard.css';

const TradingDashboard = () => {
  const [backtests, setBacktests] = useState([]);
  const [selectedBacktest, setSelectedBacktest] = useState(null);
  const [trades, setTrades] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newBacktestForm, setNewBacktestForm] = useState({
    stock_symbol: '',
    start_date: '2023-01-01',
    end_date: '2023-12-31',
    starting_amount: '10000.00'
  });
  const chartContainerRef = useRef();
  const chartRef = useRef();

  const API_BASE = '/api';

  useEffect(() => {
    fetchBacktests();
  }, []);

  const fetchBacktests = async () => {
    try {
      const response = await fetch(`${API_BASE}/backtests/`);
      const data = await response.json();
      setBacktests(data.results || data);
    } catch (error) {
      console.error('Error fetching backtests:', error);
      alert('Error connecting to backend. Make sure Django server is running on port 8000.');
    }
  };

  const fetchBacktestDetails = async (backtestId) => {
    setLoading(true);
    try {
      const [tradesRes, snapshotsRes] = await Promise.all([
        fetch(`${API_BASE}/backtests/${backtestId}/trades/`),
        fetch(`${API_BASE}/backtests/${backtestId}/daily_snapshots/`)
      ]);
      
      if (!tradesRes.ok || !snapshotsRes.ok) {
        throw new Error('Failed to fetch backtest details');
      }
      
      const tradesData = await tradesRes.json();
      const snapshotsData = await snapshotsRes.json();
      
      setTrades(tradesData);
      setSnapshots(snapshotsData);
      
      // Create chart with portfolio value
      createPortfolioChart(snapshotsData);
    } catch (error) {
      console.error('Error fetching backtest details:', error);
      alert('Error loading backtest details');
    } finally {
      setLoading(false);
    }
  };

  const createPortfolioChart = (snapshotsData) => {
    if (!chartContainerRef.current || !snapshotsData.length) return;

    // Clear existing chart
    if (chartRef.current) {
      chartRef.current.remove();
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#e1e1e1' },
        horzLines: { color: '#e1e1e1' },
      },
      rightPriceScale: {
        borderColor: '#cccccc',
      },
      timeScale: {
        borderColor: '#cccccc',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add portfolio value line
    const portfolioSeries = chart.addLineSeries({
      color: '#2563eb',
      lineWidth: 2,
      title: 'Portfolio Value ($)',
    });

    // Convert data for chart
    const chartData = snapshotsData.map(snapshot => ({
      time: snapshot.date,
      value: parseFloat(snapshot.total_portfolio_value),
    }));

    portfolioSeries.setData(chartData);

    // Add drawdown series (on separate scale)
    const drawdownSeries = chart.addLineSeries({
      color: '#dc2626',
      lineWidth: 1,
      title: 'Drawdown %',
      priceScaleId: 'right',
    });

    const drawdownData = snapshotsData.map(snapshot => ({
      time: snapshot.date,
      value: -Math.abs(parseFloat(snapshot.drawdown)), // Make negative for visual clarity
    }));

    drawdownSeries.setData(drawdownData);

    // Auto-fit the chart
    chart.timeScale().fitContent();

    // Handle window resize
    const handleResize = () => {
      chart.applyOptions({
        width: chartContainerRef.current.clientWidth,
      });
    };

    window.addEventListener('resize', handleResize);
    
    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  };

  const handleFormChange = (e) => {
    setNewBacktestForm({
      ...newBacktestForm,
      [e.target.name]: e.target.value
    });
  };

  const runNewBacktest = async (e) => {
    e.preventDefault();
    
    if (!newBacktestForm.stock_symbol.trim()) {
      alert('Please enter a stock symbol');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/backtests/run_backtest/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stock_symbol: newBacktestForm.stock_symbol.toUpperCase(),
          start_date: newBacktestForm.start_date,
          end_date: newBacktestForm.end_date,
          starting_amount: newBacktestForm.starting_amount,
        }),
      });

      if (response.ok) {
        const newBacktest = await response.json();
        setBacktests([newBacktest, ...backtests]);
        setNewBacktestForm({ ...newBacktestForm, stock_symbol: '' });
        alert(`Backtest completed for ${newBacktest.stock_tested}!`);
      } else {
        const errorData = await response.json();
        console.error('Backtest error:', errorData);
        alert('Error running backtest. Check console for details.');
      }
    } catch (error) {
      console.error('Error running backtest:', error);
      alert('Error running backtest. Make sure the Django server is running.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercent = (value) => {
    const color = value >= 0 ? '#16a34a' : '#dc2626';
    return (
      <span style={{ color }}>
        {value >= 0 ? '+' : ''}{parseFloat(value).toFixed(2)}%
      </span>
    );
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>Moving Average Crossover Strategy Dashboard</h1>
        <p>Analyze and compare trading strategy performance across different stocks</p>
      </div>

      {/* New Backtest Form */}
      <div className="new-backtest-section">
        <h2>Run New Backtest</h2>
        <form onSubmit={runNewBacktest} className="backtest-form">
          <div className="form-row">
            <input
              type="text"
              name="stock_symbol"
              placeholder="Stock Symbol (e.g., AAPL)"
              value={newBacktestForm.stock_symbol}
              onChange={handleFormChange}
              className="form-input"
              disabled={loading}
            />
            <input
              type="date"
              name="start_date"
              value={newBacktestForm.start_date}
              onChange={handleFormChange}
              className="form-input"
              disabled={loading}
            />
            <input
              type="date"
              name="end_date"
              value={newBacktestForm.end_date}
              onChange={handleFormChange}
              className="form-input"
              disabled={loading}
            />
            <input
              type="number"
              name="starting_amount"
              placeholder="Starting Amount"
              value={newBacktestForm.starting_amount}
              onChange={handleFormChange}
              className="form-input"
              disabled={loading}
              step="100"
              min="1000"
            />
            <button type="submit" disabled={loading} className="run-button">
              {loading ? 'Running...' : 'Run Backtest'}
            </button>
          </div>
        </form>
      </div>

      <div className="dashboard-content">
        {/* Backtest List */}
        <div className="backtest-list">
          <h2>Backtest Results</h2>
          {backtests.length === 0 ? (
            <div className="empty-state">
              <p>No backtests found. Run your first backtest above!</p>
            </div>
          ) : (
            <div className="backtest-grid">
              {backtests.map((backtest) => (
                <div
                  key={backtest.id}
                  className={`backtest-card ${
                    selectedBacktest?.id === backtest.id ? 'selected' : ''
                  }`}
                  onClick={() => {
                    setSelectedBacktest(backtest);
                    fetchBacktestDetails(backtest.id);
                  }}
                >
                  <div className="card-header">
                    <h3>{backtest.stock_tested}</h3>
                    <span className="date-range">
                      {new Date(backtest.trade_test_start_date).toLocaleDateString()} - 
                      {new Date(backtest.trade_test_end_date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="card-metrics">
                    <div className="metric">
                      <span className="metric-label">Return</span>
                      <span className="metric-value">
                        {formatPercent(backtest.total_returns)}
                      </span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Profit</span>
                      <span className="metric-value">
                        {formatCurrency(backtest.total_profit)}
                      </span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Trades</span>
                      <span className="metric-value">{backtest.number_of_trades}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Max Drawdown</span>
                      <span className="metric-value" style={{ color: '#dc2626' }}>
                        -{parseFloat(backtest.drawdown).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Chart and Details */}
        <div className="chart-section">
          {selectedBacktest ? (
            <div>
              <div className="chart-header">
                <h2>{selectedBacktest.stock_tested} Performance Analysis</h2>
                <div className="strategy-params">
                  <span>Stop Loss: {selectedBacktest.stop_loss}%</span>
                  <span>Take Profit: {selectedBacktest.take_profit}%</span>
                  <span>Period: 20/50 day MA crossover</span>
                </div>
              </div>
              
              {/* Portfolio Chart */}
              <div className="chart-container">
                <div ref={chartContainerRef} className="chart" />
                {loading && (
                  <div className="chart-loading">
                    <p>Loading chart data...</p>
                  </div>
                )}
              </div>

              {/* Summary Stats */}
              <div className="summary-stats">
                <div className="stat-card">
                  <h4>Total Return</h4>
                  <div className="stat-value">
                    {formatPercent(selectedBacktest.total_returns)}
                  </div>
                </div>
                <div className="stat-card">
                  <h4>Net Profit</h4>
                  <div className="stat-value">
                    {formatCurrency(selectedBacktest.total_profit)}
                  </div>
                </div>
                <div className="stat-card">
                  <h4>Max Drawdown</h4>
                  <div className="stat-value" style={{ color: '#dc2626' }}>
                    -{parseFloat(selectedBacktest.drawdown).toFixed(2)}%
                  </div>
                </div>
                <div className="stat-card">
                  <h4>Total Trades</h4>
                  <div className="stat-value">
                    {selectedBacktest.number_of_trades}
                  </div>
                </div>
                <div className="stat-card">
                  <h4>Starting Capital</h4>
                  <div className="stat-value">
                    {formatCurrency(selectedBacktest.starting_amount)}
                  </div>
                </div>
                <div className="stat-card">
                  <h4>Final Value</h4>
                  <div className="stat-value">
                    {formatCurrency(selectedBacktest.closing_amount)}
                  </div>
                </div>
              </div>

              {/* Trades Table */}
              <div className="trades-section">
                <h3>Trade History</h3>
                {trades.length === 0 ? (
                  <p>No trades found for this backtest.</p>
                ) : (
                  <div className="trades-table-container">
                    <table className="trades-table">
                      <thead>
                        <tr>
                          <th>Entry Date</th>
                          <th>Exit Date</th>
                          <th>Entry Price</th>
                          <th>Exit Price</th>
                          <th>Quantity</th>
                          <th>P&L</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trades.map((trade) => (
                          <tr key={trade.id}>
                            <td>{new Date(trade.entry_date).toLocaleDateString()}</td>
                            <td>
                              {trade.exit_date 
                                ? new Date(trade.exit_date).toLocaleDateString() 
                                : 'Open'
                              }
                            </td>
                            <td>{formatCurrency(trade.entry_price)}</td>
                            <td>
                              {trade.exit_price 
                                ? formatCurrency(trade.exit_price)
                                : formatCurrency(trade.final_market_price)
                              }
                            </td>
                            <td>{trade.quantity}</td>
                            <td>
                              <span style={{ 
                                color: parseFloat(trade.profit) >= 0 ? '#16a34a' : '#dc2626' 
                              }}>
                                {formatCurrency(trade.profit)}
                              </span>
                            </td>
                            <td>
                              <span className={`status ${trade.is_open ? 'open' : 'closed'}`}>
                                {trade.is_open ? 'Open' : 'Closed'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="no-selection">
              <h2>Select a Backtest</h2>
              <p>Choose a backtest from the list to view detailed performance charts and trade history.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TradingDashboard;