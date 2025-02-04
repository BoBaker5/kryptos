import React, { useState, useEffect, useCallback } from 'react';
import { Activity, DollarSign, LineChart } from 'lucide-react';
import { ResponsiveContainer, Line, XAxis, YAxis, CartesianGrid, Tooltip, LineChart as RechartsLineChart } from 'recharts';

const BotDashboard = ({ mode = 'live' }) => {
  const [botData, setBotData] = useState({
    status: mode === 'demo' ? 'running' : 'stopped',
    positions: [],
    balance: {},
    metrics: {
      current_equity: mode === 'demo' ? 100000 : 0,
      pnl: 0,
      pnl_percentage: 0
    },
    trades: [],
    performanceHistory: []
  });

  const [apiConfig, setApiConfig] = useState({
    apiKey: '',
    apiSecret: ''
  });

  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);

  const fetchBotStatus = useCallback(async () => {
    try {
      const endpoint = mode === 'demo' ? '/api/demo-status' : '/api/live-status';
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error('Failed to fetch status');
      }
      
      const data = await response.json();
      if (data.status === 'success') {
        setBotData(data.data);
        setError(null);
      }
    } catch (err) {
      console.error('Error fetching bot status:', err);
      setError('Unable to connect to trading server. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    fetchBotStatus();
    const interval = setInterval(fetchBotStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchBotStatus]);

  const handleApiKeyChange = (field, value) => {
    setApiConfig(prev => ({
      ...prev,
      [field]: value
    }));
    setError(null);
  };

  const handleStartBot = async () => {
    if (!apiConfig.apiKey || !apiConfig.apiSecret) {
      setError('Please enter both API Key and Secret to start live trading.');
      return;
    }

    try {
      setIsActionLoading(true);
      const response = await fetch('/api/start-bot/1', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apiConfig)
      });
      
      if (!response.ok) {
        throw new Error('Failed to start bot');
      }
      
      const data = await response.json();
      if (data.status === 'success') {
        await fetchBotStatus();
        setError(null);
      }
    } catch (err) {
      console.error('Start bot error:', err);
      setError('Failed to start bot. Please check your API keys and try again.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleStopBot = async () => {
    try {
      setIsActionLoading(true);
      const response = await fetch('/api/stop-bot/1', {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to stop bot');
      }
      
      const data = await response.json();
      if (data.status === 'success') {
        await fetchBotStatus();
        setError(null);
      }
    } catch (err) {
      setError('Failed to stop bot. Please try again.');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Rest of your component code remains the same, including renderApiKeyForm, 
  // renderActionButton, renderPerformanceChart, and the return statement...
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">
          {mode === 'demo' ? 'Demo Trading Dashboard' : 'Live Trading Dashboard'}
        </h1>
        
        <div className="flex items-center gap-4">
          <div className={`px-3 py-1 rounded-full ${
            botData.status === 'running' 
              ? 'bg-green-100 text-green-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            {botData.status === 'running' ? 'Active' : 'Stopped'}
          </div>
          {mode === 'live' && (
            <button
              onClick={botData.status === 'running' ? handleStopBot : handleStartBot}
              disabled={isActionLoading}
              className={`px-4 py-2 rounded text-white ${
                botData.status === 'running' 
                  ? 'bg-red-500 hover:bg-red-600' 
                  : 'bg-green-500 hover:bg-green-600'
              } ${isActionLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isActionLoading 
                ? (botData.status === 'running' ? 'Stopping...' : 'Starting...') 
                : (botData.status === 'running' ? 'Stop Bot' : 'Start Bot')}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-6 rounded">
          {error}
        </div>
      )}

      {mode === 'live' && botData.status !== 'running' && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">API Configuration</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">API Key</label>
              <input 
                type="text"
                className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2"
                value={apiConfig.apiKey}
                onChange={(e) => handleApiKeyChange('apiKey', e.target.value)}
                placeholder="Enter your Kraken API Key"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">API Secret</label>
              <input 
                type="password"
                className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2"
                value={apiConfig.apiSecret}
                onChange={(e) => handleApiKeyChange('apiSecret', e.target.value)}
                placeholder="Enter your Kraken API Secret"
              />
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500">Portfolio Value</p>
              <h3 className="text-2xl font-bold">
                ${botData.metrics?.current_equity?.toFixed(2) || '0.00'}
              </h3>
            </div>
            <DollarSign className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500">P&L</p>
              <h3 className={`text-2xl font-bold ${
                botData.metrics?.pnl >= 0 ? 'text-green-500' : 'text-red-500'
              }`}>
                ${botData.metrics?.pnl?.toFixed(2) || '0.00'}
              </h3>
              <p className={`text-sm ${
                botData.metrics?.pnl_percentage >= 0 ? 'text-green-500' : 'text-red-500'
              }`}>
                {botData.metrics?.pnl_percentage >= 0 ? '+' : ''}
                {botData.metrics?.pnl_percentage?.toFixed(2) || '0.00'}%
              </p>
            </div>
            <Activity className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500">Active Positions</p>
              <h3 className="text-2xl font-bold">
                {botData.positions?.length || 0}
              </h3>
            </div>
            <LineChart className="h-8 w-8 text-blue-500" />
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Performance History</h2>
        <div className="h-64">
          {!botData.performanceHistory?.length ? (
            <div className="h-full flex items-center justify-center text-gray-500">
              No performance data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <RechartsLineChart data={botData.performanceHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(time) => new Date(time).toLocaleTimeString()} 
                />
                <YAxis />
                <Tooltip 
                  formatter={(value) => [`$${value.toLocaleString()}`, 'Portfolio Value']}
                  labelFormatter={(label) => new Date(label).toLocaleString()}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={false}
                />
              </RechartsLineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Current Positions</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Quantity</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Entry Price</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Current Price</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">P/L %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {!botData.positions?.length ? (
                <tr>
                  <td colSpan="5" className="px-6 py-4 text-center text-gray-500">
                    No active positions
                  </td>
                </tr>
              ) : (
                botData.positions.map((position, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4">{position.symbol}</td>
                    <td className="px-6 py-4 text-right">{position.quantity}</td>
                    <td className="px-6 py-4 text-right">${position.entry_price}</td>
                    <td className="px-6 py-4 text-right">${position.current_price}</td>
                    <td className={`px-6 py-4 text-right ${
                      position.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {position.pnl >= 0 ? '+' : ''}{position.pnl}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default BotDashboard;
