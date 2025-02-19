import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp, DollarSign, Activity } from 'lucide-react';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';

const BotDashboard = ({ mode = 'demo', apiBaseUrl = '', wsBaseUrl = '' }) => {
  const [botData, setBotData] = useState({
    status: 'loading',
    metrics: {
      portfolio_value: 0,
      pnl: 0,
      pnl_percentage: 0
    },
    positions: [],
    balance: { ZUSD: 100000 }
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchData = async () => {
      try {
        setLoading(true);
        // Add timestamp to prevent caching
        const timestamp = new Date().getTime();
        const response = await fetch(`${apiBaseUrl}/api/${mode}-status?t=${timestamp}`, {
          signal: controller.signal,
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        });

        if (!response.ok) {
          throw new Error(
            `Server returned ${response.status}: ${response.statusText}`
          );
        }

        const data = await response.json();
        
        if (isMounted) {
          if (data.status === 'success' && data.data) {
            setBotData(data.data);
            setError(null);
          } else {
            setError('Invalid data format received from server');
          }
        }
      } catch (err) {
        if (isMounted) {
          console.error('Fetch error:', err);
          setError(
            'Unable to connect to trading bot. Please check your connection and try again.'
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);

    return () => {
      isMounted = false;
      controller.abort();
      clearInterval(interval);
    };
  }, [mode, apiBaseUrl]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-lg text-slate-600">
          Loading trading data...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle>Connection Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  return (
    <div className="p-6 space-y-6 bg-slate-50 min-h-screen">
      {/* Status Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Trading Bot Status</h1>
        <div className="flex items-center space-x-2">
          <div className={`h-3 w-3 rounded-full ${botData.running ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm font-medium text-slate-600">
            {botData.running ? 'Bot Active' : 'Bot Inactive'}
          </span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <DollarSign className="h-5 w-5 text-blue-500" />
            <h2 className="text-sm font-medium text-slate-600">Portfolio Value</h2>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-800">
            {formatCurrency(botData.portfolio_value)}
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-green-500" />
            <h2 className="text-sm font-medium text-slate-600">Total P&L</h2>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-800">
            {formatCurrency(botData.pnl)}
          </p>
          <p className={`text-sm ${botData.pnl_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {botData.pnl_percentage.toFixed(2)}%
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-purple-500" />
            <h2 className="text-sm font-medium text-slate-600">Active Positions</h2>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-800">
            {botData.positions.length}
          </p>
        </div>
      </div>

      {/* Positions Table */}
      {botData.positions.length > 0 && (
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
                {botData.positions.map((position) => (
                  <tr key={position.symbol}>
                    <td className="px-4 py-3 text-sm text-slate-800 font-medium">{position.symbol}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{parseFloat(position.quantity).toFixed(8)}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{formatCurrency(parseFloat(position.entry_price))}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{formatCurrency(parseFloat(position.current_price))}</td>
                    <td className={`px-4 py-3 text-sm text-right font-medium ${parseFloat(position.pnl) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(parseFloat(position.pnl))}
                      <span className="ml-1 text-xs">
                        ({parseFloat(position.pnl_percentage).toFixed(2)}%)
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default BotDashboard;
