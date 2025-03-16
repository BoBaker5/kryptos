import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { DollarSign, TrendingUp, Activity, ArrowUp, ArrowDown, RefreshCw, TrendingDown } from 'lucide-react';

const BotDashboard = ({ mode = 'demo', apiBaseUrl = '', onError = () => {}, isRunning = false, connectionStatus = 'disconnected' }) => {
  const [botData, setBotData] = useState({
    portfolio_value: 1000000.00,  // Default initial value
    pnl: 0,
    pnl_percentage: 0,
    positions: [],
    running: false
  });
  const [tradeHistory, setTradeHistory] = useState([]);
  const [loadingTrades, setLoadingTrades] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    const fetchData = async () => {
      if (connectionStatus !== 'connected') {
        return; // Don't fetch if we're not connected
      }
      
      try {
        const response = await fetch(`${apiBaseUrl}/api/${mode}-status`);
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data && data.status === 'success' && data.data) {
          // Safely parse numeric values with fallbacks
          const portfolioValue = parseFloat(data.data.portfolio_value);
          const pnl = parseFloat(data.data.pnl);
          const pnlPercentage = parseFloat(data.data.pnl_percentage);
          
          // Get positions with safe numeric parsing
          const safePositions = Array.isArray(data.data.positions) 
            ? data.data.positions.map(pos => ({
                ...pos,
                quantity: parseFloat(pos.quantity) || 0,
                entry_price: parseFloat(pos.entry_price) || 0,
                current_price: parseFloat(pos.current_price) || 0,
                pnl: parseFloat(pos.pnl) || 0,
                pnl_percentage: parseFloat(pos.pnl_percentage) || 0
              }))
            : [];
          
          setBotData({
            portfolio_value: isNaN(portfolioValue) ? 1000000.00 : portfolioValue,
            pnl: isNaN(pnl) ? 0 : pnl,
            pnl_percentage: isNaN(pnlPercentage) ? 0 : pnlPercentage,
            positions: safePositions,
            running: Boolean(data.data.running) || false
          });
          
          setLastUpdate(new Date());
        }
      } catch (error) {
        console.error('Error fetching bot data:', error);
        if (onError) {
          onError(error.message);
        }
      }
    };

    // Fetch trade history
    const fetchTradeHistory = async () => {
      if (connectionStatus !== 'connected') {
        return;
      }
      
      try {
        setLoadingTrades(true);
        const response = await fetch(`${apiBaseUrl}/api/trade-history`);
        
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result && result.status === 'success' && Array.isArray(result.data)) {
          // Format trade data
          const formattedTrades = result.data.map(trade => ({
            ...trade,
            timestamp: new Date(trade.timestamp),
            price: parseFloat(trade.price) || 0,
            quantity: parseFloat(trade.quantity) || 0,
            value: parseFloat(trade.value) || 0,
            pnl: parseFloat(trade.pnl) || 0,
            pnl_percentage: parseFloat(trade.pnl_percentage) || 0
          }));
          
          // Sort by timestamp (newest first)
          formattedTrades.sort((a, b) => b.timestamp - a.timestamp);
          
          setTradeHistory(formattedTrades);
        }
      } catch (error) {
        console.error('Error fetching trade history:', error);
        if (onError) {
          onError('Failed to load trade history: ' + error.message);
        }
      } finally {
        setLoadingTrades(false);
      }
    };

    fetchData();
    fetchTradeHistory();
    
    const dataInterval = setInterval(fetchData, 5000);
    const historyInterval = setInterval(fetchTradeHistory, 30000); // Refresh history less frequently
    
    return () => {
      clearInterval(dataInterval);
      clearInterval(historyInterval);
    };
  }, [mode, apiBaseUrl, connectionStatus, onError]);

  // Safe number formatting functions that handle non-numeric inputs
  const formatCurrency = (value) => {
    // Make sure value is a valid number before formatting
    const numValue = parseFloat(value);
    const safeValue = isNaN(numValue) ? 0 : numValue;
    
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(safeValue);
  };

  const formatPercent = (value) => {
    // Convert to number and provide fallback for invalid values
    const numValue = parseFloat(value);
    const safeValue = isNaN(numValue) ? 0 : numValue;
    
    return safeValue.toFixed(2) + '%';
  };

  // Calculate total value from positions safely
  const calculateTotalPositionsValue = () => {
    if (!Array.isArray(botData.positions) || botData.positions.length === 0) {
      return 0;
    }
    
    return botData.positions.reduce((sum, pos) => {
      const quantity = parseFloat(pos.quantity) || 0;
      const price = parseFloat(pos.current_price) || 0;
      return sum + (quantity * price);
    }, 0);
  };

  // Format trade timestamp
  const formatDate = (date) => {
    if (!(date instanceof Date) || isNaN(date.getTime())) {
      return 'Invalid date';
    }
    return date.toLocaleString();
  };

  // Calculate trade performance metrics
  const calculateTradeMetrics = () => {
    if (!Array.isArray(tradeHistory) || tradeHistory.length === 0) {
      return { totalTrades: 0, winningTrades: 0, losingTrades: 0, winRate: 0 };
    }
    
    const sellTrades = tradeHistory.filter(trade => trade.type === 'sell');
    const winningTrades = sellTrades.filter(trade => trade.pnl > 0).length;
    const losingTrades = sellTrades.filter(trade => trade.pnl < 0).length;
    const totalTrades = sellTrades.length;
    const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;
    
    return {
      totalTrades,
      winningTrades,
      losingTrades,
      winRate: winRate.toFixed(2)
    };
  };

  const tradeMetrics = calculateTradeMetrics();

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">
          {mode === 'demo' ? 'Demo' : 'Live'} Trading Dashboard
        </h1>
        <div className="flex items-center space-x-2 text-sm text-slate-600">
          <span>Last update: {lastUpdate.toLocaleTimeString()}</span>
          <div className={`h-2 w-2 rounded-full ${botData.running || isRunning ? 'bg-green-500' : 'bg-red-500'}`} />
          <span>{botData.running || isRunning ? 'Bot active' : 'Bot inactive'}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Portfolio Value */}
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <DollarSign className="h-5 w-5 text-blue-500" />
            <h2 className="text-sm font-medium text-slate-600">Portfolio Value</h2>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-800">
            {formatCurrency(botData.portfolio_value)}
          </p>
          <p className="text-sm text-slate-500">
            Initial: {formatCurrency(100000.00)}
          </p>
        </div>

        {/* Total P&L */}
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-green-500" />
            <h2 className="text-sm font-medium text-slate-600">Total P&L</h2>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-800">
            {formatCurrency(botData.pnl)}
          </p>
          <p className={`text-sm ${parseFloat(botData.pnl_percentage) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatPercent(botData.pnl_percentage)}
          </p>
        </div>

        {/* Active Positions */}
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-purple-500" />
            <h2 className="text-sm font-medium text-slate-600">Active Positions</h2>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-800">
            {Array.isArray(botData.positions) ? botData.positions.length : 0}
          </p>
          <p className="text-sm text-slate-500">
            Total value: {formatCurrency(calculateTotalPositionsValue())}
          </p>
        </div>
      </div>

      {Array.isArray(botData.positions) && botData.positions.length > 0 ? (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200">
            <h2 className="text-lg font-medium text-slate-800">Active Positions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Symbol</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Quantity</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Entry Price</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Current Price</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {botData.positions.map((position, index) => (
                  <tr key={position.symbol || `position-${index}`}>
                    <td className="px-4 py-3 text-sm text-slate-800 font-medium">{position.symbol}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{position.quantity}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{formatCurrency(position.entry_price)}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{formatCurrency(position.current_price)}</td>
                    <td className={`px-4 py-3 text-sm text-right font-medium ${parseFloat(position.pnl) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(position.pnl)}
                      <span className="ml-1 text-xs">
                        ({formatPercent(position.pnl_percentage)})
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm p-6 text-center text-slate-600">
          No active positions
        </div>
      )}

      {/* Trade History Section */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center">
          <h2 className="text-lg font-medium text-slate-800">Trade History</h2>
          <div className="flex items-center space-x-4">
            <div className="text-sm text-slate-600 flex items-center space-x-2">
              <span>Win Rate:</span>
              <span className={`font-medium ${parseFloat(tradeMetrics.winRate) >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                {tradeMetrics.winRate}% ({tradeMetrics.winningTrades}/{tradeMetrics.totalTrades})
              </span>
            </div>
            <button 
              onClick={() => {
                setLoadingTrades(true);
                fetch(`${apiBaseUrl}/api/trade-history`)
                  .then(response => response.json())
                  .then(data => {
                    if (data.status === 'success') {
                      const formattedTrades = data.data.map(trade => ({
                        ...trade,
                        timestamp: new Date(trade.timestamp),
                        price: parseFloat(trade.price) || 0,
                        quantity: parseFloat(trade.quantity) || 0,
                        value: parseFloat(trade.value) || 0,
                        pnl: parseFloat(trade.pnl) || 0,
                        pnl_percentage: parseFloat(trade.pnl_percentage) || 0
                      }));
                      formattedTrades.sort((a, b) => b.timestamp - a.timestamp);
                      setTradeHistory(formattedTrades);
                    }
                    setLoadingTrades(false);
                  })
                  .catch(error => {
                    console.error('Error refreshing trade history:', error);
                    setLoadingTrades(false);
                  });
              }}
              className="flex items-center text-sm text-slate-600 hover:text-blue-600"
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${loadingTrades ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
        
        {loadingTrades && tradeHistory.length === 0 ? (
          <div className="p-10 flex justify-center items-center">
            <RefreshCw className="animate-spin h-5 w-5 text-blue-500 mr-2" />
            <span className="text-slate-600">Loading trade history...</span>
          </div>
        ) : tradeHistory.length === 0 ? (
          <div className="p-10 text-center text-slate-600">
            No trade history available
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Date/Time</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Symbol</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-slate-600">Type</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Price</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Quantity</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Value</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Profit/Loss</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {tradeHistory.map((trade, index) => (
                  <tr key={`trade-${index}`} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm text-slate-800">
                      {formatDate(trade.timestamp)}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">
                      {trade.symbol}
                    </td>
                    <td className="px-4 py-3 text-sm text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        trade.type === 'buy' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {trade.type === 'buy' ? <ArrowDown className="h-3 w-3 mr-1" /> : <ArrowUp className="h-3 w-3 mr-1" />}
                        {trade.type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">
                      {formatCurrency(trade.price)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">
                      {trade.quantity.toFixed(8)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">
                      {formatCurrency(trade.value)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right">
                      {trade.type === 'sell' && (
                        <div className={`flex items-center justify-end ${
                          trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {trade.pnl >= 0 ? 
                            <TrendingUp className="h-4 w-4 mr-1" /> : 
                            <TrendingDown className="h-4 w-4 mr-1" />
                          }
                          <span>{formatCurrency(trade.pnl)}</span>
                          <span className="ml-1 text-xs">({formatPercent(trade.pnl_percentage)})</span>
                        </div>
                      )}
                      {trade.type === 'buy' && (
                        <span className="text-slate-500">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default BotDashboard;
