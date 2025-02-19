import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp, DollarSign, Activity } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const BotDashboard = () => {
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

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/demo-status');
        if (!response.ok) {
          throw new Error('Failed to fetch bot data');
        }
        const data = await response.json();
        setBotData(data.data);
        setError(null);
      } catch (err) {
        setError(err.message);
      }
    };

    // Initial fetch
    fetchData();

    // Poll every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
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
        <h1 className="text-2xl font-bold text-slate-800">Crypto Trading Bot</h1>
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

      {/* Performance Chart */}
      <div className="bg-white p-4 rounded-lg shadow-sm">
        <h2 className="text-lg font-medium text-slate-800 mb-4">Portfolio Performance</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={[
                { timestamp: 'Start', value: 100000 },
                { timestamp: 'Current', value: botData.portfolio_value }
              ]}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip 
                formatter={(value) => formatCurrency(value)}
                labelFormatter={(label) => `Time: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#2563eb" 
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default BotDashboard;
