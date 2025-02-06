import React, { useState, useEffect, useCallback } from 'react';
import { Activity, DollarSign, LineChart } from 'lucide-react';

const BotDashboard = ({ mode = 'live' }) => {
  const [demoBotData, setDemoBotData] = useState({
    status: 'running',
    positions: [],
    metrics: { current_equity: 100000, pnl: 0, pnl_percentage: 0 }
  });
  
  const [liveBotData, setLiveBotData] = useState({
    status: 'stopped',
    positions: [],
    metrics: { current_equity: 0, pnl: 0, pnl_percentage: 0 }
  });
  
  const [apiConfig, setApiConfig] = useState({ apiKey: '', apiSecret: '' });
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const currentBotData = mode === 'demo' ? demoBotData : liveBotData;

  const fetchBotStatus = useCallback(async () => {
    let controller = new AbortController();
    try {
      const endpoint = mode === 'demo' ? '/api/demo-status' : '/api/live-status';
      const timeout = setTimeout(() => controller.abort(), 15000);

      const response = await fetch(endpoint, {
        signal: controller.signal,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      
      clearTimeout(timeout);
      
      if (!response.ok) {
        throw new Error(response.status === 504 ? 'Server gateway timeout' : 
          response.status === 502 ? 'Server unavailable' : 
          `Server error ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'success') {
        const newData = {
          ...data.data,
          status: mode === 'demo' ? 'running' : (data.data.status || 'stopped'),
          metrics: {
            current_equity: mode === 'demo' ? 100000 : data.data.metrics?.current_equity || 0,
            pnl: data.data.metrics?.pnl || 0,
            pnl_percentage: data.data.metrics?.pnl_percentage || 0
          }
        };

        if (mode === 'demo') {
          setDemoBotData(prev => ({ ...prev, ...newData }));
        } else {
          setLiveBotData(prev => ({ ...prev, ...newData }));
        }
        setError(null);
        setRetryCount(0);
      }
    } catch (err) {
      const isAbortError = err.name === 'AbortError';
      setError(isAbortError ? 
        'Connection timed out. Retrying...' : 
        `Unable to connect to ${mode} trading server: ${err.message}`
      );
      
      if (retryCount < 3) {
        const timeout = Math.pow(2, retryCount) * 2000;
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchBotStatus();
        }, timeout);
      }
      
      if (mode === 'demo') {
        setDemoBotData(prev => ({
          ...prev,
          status: 'running',
          metrics: { current_equity: 100000, pnl: 0, pnl_percentage: 0 }
        }));
      }
    } finally {
      setIsLoading(false);
      controller = null;
    }
  }, [mode, retryCount]);

  useEffect(() => {
    setIsLoading(true);
    fetchBotStatus();
    const interval = setInterval(fetchBotStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchBotStatus, mode]);

  const handleApiKeyChange = (field, value) => {
    setApiConfig(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleStartBot = async () => {
    if (!apiConfig.apiKey || !apiConfig.apiSecret) {
      setError('Please enter both API Key and Secret');
      return;
    }

    try {
      setIsActionLoading(true);
      const response = await fetch('/api/start-bot/1', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiConfig)
      });
      
      if (!response.ok) throw new Error('Failed to start bot');
      
      await fetchBotStatus();
      setError(null);
    } catch (err) {
      console.error('Error starting bot:', err);
      setError('Failed to start bot. Check API keys and try again.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleStopBot = async () => {
    try {
      setIsActionLoading(true);
      const response = await fetch('/api/stop-bot/1', { method: 'POST' });
      
      if (!response.ok) throw new Error('Failed to stop bot');
      
      await fetchBotStatus();
      setError(null);
    } catch (err) {
      console.error('Error stopping bot:', err);
      setError('Failed to stop bot. Please try again.');
    } finally {
      setIsActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
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
            currentBotData.status === 'running' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {currentBotData.status === 'running' ? 'Active' : 'Stopped'}
          </div>
          {mode === 'live' && (
            <button
              onClick={currentBotData.status === 'running' ? handleStopBot : handleStartBot}
              disabled={isActionLoading}
              className={`px-4 py-2 rounded text-white ${
                currentBotData.status === 'running' ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'
              } ${isActionLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isActionLoading 
                ? (currentBotData.status === 'running' ? 'Stopping...' : 'Starting...') 
                : (currentBotData.status === 'running' ? 'Stop Bot' : 'Start Bot')}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-6 rounded">
          {error}
        </div>
      )}

      {mode === 'live' && currentBotData.status !== 'running' && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">API Configuration</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">API Key</label>
              <input 
                type="text"
                className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2 focus:ring-blue-500 focus:border-blue-500"
                value={apiConfig.apiKey}
                onChange={(e) => handleApiKeyChange('apiKey', e.target.value)}
                placeholder="Enter your Kraken API Key"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">API Secret</label>
              <input 
                type="password"
                className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm p-2 focus:ring-blue-500 focus:border-blue-500"
                value={apiConfig.apiSecret}
                onChange={(e) => handleApiKeyChange('apiSecret', e.target.value)}
                placeholder="Enter your Kraken API Secret"
              />
            </div>
            <p className="text-sm text-gray-500">
              Enter your Kraken API credentials to start live trading. Make sure your API key has trading permissions enabled.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {[
          {
            title: 'Portfolio Value',
            value: currentBotData.metrics?.current_equity?.toFixed(2) || '0.00',
            icon: DollarSign,
            prefix: '$'
          },
          {
            title: 'P&L',
            value: currentBotData.metrics?.pnl?.toFixed(2) || '0.00',
            percentage: currentBotData.metrics?.pnl_percentage?.toFixed(2) || '0.00',
            icon: Activity,
            prefix: '$',
            color: currentBotData.metrics?.pnl >= 0 ? 'text-green-500' : 'text-red-500'
          },
          {
            title: 'Active Positions',
            value: currentBotData.positions?.length || 0,
            icon: LineChart
          }
        ].map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500">{stat.title}</p>
                <h3 className={`text-2xl font-bold ${stat.color || ''}`}>
                  {stat.prefix || ''}{stat.value}
                </h3>
                {stat.percentage !== undefined && (
                  <p className={stat.color}>
                    {Number(stat.percentage) >= 0 ? '+' : ''}{stat.percentage}%
                  </p>
                )}
              </div>
              <stat.icon className="h-8 w-8 text-blue-500" />
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Current Positions</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Quantity</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Entry Price</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Current Price</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">P/L %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {!currentBotData.positions?.length ? (
                <tr>
                  <td colSpan="5" className="px-6 py-4 text-center text-gray-500">
                    No active positions
                  </td>
                </tr>
              ) : (
                currentBotData.positions.map((position, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap">{position.symbol}</td>
                    <td className="px-6 py-4 text-right">{parseFloat(position.quantity).toFixed(8)}</td>
                    <td className="px-6 py-4 text-right">${parseFloat(position.entry_price).toFixed(2)}</td>
                    <td className="px-6 py-4 text-right">${parseFloat(position.current_price).toFixed(2)}</td>
                    <td className={`px-6 py-4 text-right ${parseFloat(position.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {parseFloat(position.pnl) >= 0 ? '+' : ''}{parseFloat(position.pnl).toFixed(2)}%
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
