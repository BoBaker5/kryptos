import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, DollarSign, LineChart } from 'lucide-react';
import PerformanceChart from './PerformanceChart';

const BotDashboard = ({ mode = 'live' }) => {
  const API_URL = 'http://localhost:5000';
  
  const [botData, setBotData] = useState({
    status: 'stopped',
    positions: [],
    balance: {},
    metrics: {
      current_equity: mode === 'demo' ? 1000000 : 0,
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

  const fetchBotStatus = async () => {
    try {
      const endpoint = `/bot-status/${mode}`;
      console.log('Fetching from:', `${API_URL}${endpoint}`);
      const response = await axios.get(`${API_URL}${endpoint}`);
      
      if (response.data.status === 'success') {
        setBotData(response.data.data);
        setError(null);
      }
    } catch (err) {
      console.error('Error fetching bot status:', err);
      setError('Unable to connect to trading server. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBotStatus();
    const interval = setInterval(fetchBotStatus, 30000);
    return () => clearInterval(interval);
  }, [mode]);

  const handleApiKeyChange = (field, value) => {
    setApiConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleStartBot = async () => {
    if (mode === 'live' && (!apiConfig.apiKey || !apiConfig.apiSecret)) {
      setError('Please enter both API Key and Secret to start live trading.');
      return;
    }

    try {
      setIsActionLoading(true);
      const endpoint = `/start-bot/${mode}`;
      const response = await axios.post(`${API_URL}${endpoint}`, {
        apiKey: apiConfig.apiKey,
        apiSecret: apiConfig.apiSecret
      });
      
      if (response.data.status === 'success') {
        setBotData(prevData => ({
          ...prevData,
          status: 'running'
        }));
        await fetchBotStatus();
      }
    } catch (err) {
      console.error('Start bot error:', err);
      setError(err.response?.data?.message || 'Failed to start bot. Please check your API keys and try again.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleStopBot = async () => {
    try {
      setIsActionLoading(true);
      const endpoint = `/stop-bot/${mode}`;
      const response = await axios.post(`${API_URL}${endpoint}`, {
        apiKey: apiConfig.apiKey
      });
      if (response.data.status === 'success') {
        setBotData(prevData => ({
          ...prevData,
          status: 'stopped'
        }));
        await fetchBotStatus();
      }
    } catch (err) {
      console.error('Stop bot error:', err);
      setError('Failed to stop bot. Please try again.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const renderApiKeyForm = () => {
    if (mode !== 'live') return null;
    
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">API Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">API Key</label>
            <input 
              type="text" 
              className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2"
              placeholder="Enter your Kraken API Key"
              value={apiConfig.apiKey}
              onChange={(e) => handleApiKeyChange('apiKey', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">API Secret</label>
            <input 
              type="password" 
              className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2"
              placeholder="Enter your Kraken API Secret"
              value={apiConfig.apiSecret}
              onChange={(e) => handleApiKeyChange('apiSecret', e.target.value)}
            />
          </div>
          <p className="text-sm text-gray-500">
            Your API keys are required to enable live trading. Only trading permissions are needed.
          </p>
        </div>
      </div>
    );
  };

  const renderActionButton = () => {
    if (mode === 'demo') {
      return null;
    }

    if (botData.status === 'running') {
      return (
        <button
          onClick={handleStopBot}
          disabled={isActionLoading}
          className={`px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors ${
            isActionLoading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isActionLoading ? 'Stopping...' : 'Stop Bot'}
        </button>
      );
    } else {
      return (
        <button
          onClick={handleStartBot}
          disabled={isActionLoading || (mode === 'live' && (!apiConfig.apiKey || !apiConfig.apiSecret))}
          className={`px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors ${
            isActionLoading || (mode === 'live' && (!apiConfig.apiKey || !apiConfig.apiSecret))
              ? 'opacity-50 cursor-not-allowed' 
              : ''
          }`}
        >
          {isActionLoading ? 'Starting...' : 'Start Bot'}
        </button>
      );
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#87CEEB]"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-[#001F3F]">
          {mode === 'demo' ? 'Demo Trading Dashboard' : 'Live Trading Dashboard'}
        </h1>
        
        <div className="flex items-center gap-4">
          <div className={`px-3 py-1 rounded-full ${
            mode === 'demo' || botData.status === 'running' 
              ? 'bg-green-100 text-green-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            {mode === 'demo' || botData.status === 'running' ? 'Active' : 'Stopped'}
          </div>
          {renderActionButton()}
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-6 rounded">
          {error}
        </div>
      )}

      {renderApiKeyForm()}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500">Portfolio Value</p>
              <h3 className="text-2xl font-bold">
                ${botData.metrics?.current_equity?.toFixed(2) || '0.00'}
              </h3>
            </div>
            <DollarSign className="h-8 w-8 text-[#87CEEB]" />
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
            <Activity className="h-8 w-8 text-[#87CEEB]" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500">Active Positions</p>
              <h3 className="text-2xl font-bold text-[#001F3F]">
                {botData.positions?.length || 0}
              </h3>
            </div>
            <LineChart className="h-8 w-8 text-[#87CEEB]" />
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <PerformanceChart 
        mode={mode} 
        data={botData.performanceHistory || []} 
      />

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
                    <td className="px-6 py-4 text-right">
                      {parseFloat(position.quantity).toFixed(4)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      ${parseFloat(position.entry_price).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      ${parseFloat(position.current_price).toFixed(2)}
                    </td>
                    <td className={`px-6 py-4 text-right ${
                      position.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {position.pnl >= 0 ? '+' : ''}
                      {parseFloat(position.pnl).toFixed(2)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trade History */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Trades</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Price</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Quantity</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {!botData.trades?.length ? (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-gray-500">
                    No trades yet
                  </td>
                </tr>
              ) : (
                botData.trades.map((trade, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4">
                      {new Date(trade.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">{trade.symbol}</td>
                    <td className={`px-6 py-4 ${
                      trade.type === 'buy' ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {trade.type.toUpperCase()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {parseFloat(trade.quantity).toFixed(4)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      ${parseFloat(trade.value).toFixed(2)}
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