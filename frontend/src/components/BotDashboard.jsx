import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { DollarSign, TrendingUp, Activity } from 'lucide-react';

const BotDashboard = ({ mode = 'demo', apiBaseUrl = '' }) => {
  const [botData, setBotData] = useState({
    portfolio_value: 100000.00,  // Default initial value
    pnl: 0,
    pnl_percentage: 0,
    positions: [],
    running: false
  });
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/${mode}-status`);
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        const data = await response.json();
        
        if (data.status === 'success' && data.data) {
          setBotData({
            portfolio_value: Number(data.data.portfolio_value) || 100000.00,
            pnl: Number(data.data.pnl) || 0,
            pnl_percentage: Number(data.data.pnl_percentage) || 0,
            positions: data.data.positions || [],
            running: data.data.running || false
          });
          setLastUpdate(new Date());
        }
      } catch (error) {
        console.error('Error fetching bot data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [mode, apiBaseUrl]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0);
  };

  const formatPercent = (value) => {
    return (value || 0).toFixed(2) + '%';
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Demo Trading Dashboard</h1>
        <div className="flex items-center space-x-2 text-sm text-slate-600">
          <span>Last update: {lastUpdate.toLocaleTimeString()}</span>
          <div className={`h-2 w-2 rounded-full ${botData.running ? 'bg-green-500' : 'bg-red-500'}`} />
          <span>{botData.running ? 'Bot active' : 'Bot inactive'}</span>
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
          <p className={`text-sm ${botData.pnl_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
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
            {botData.positions.length}
          </p>
          <p className="text-sm text-slate-500">
            Total value: {formatCurrency(
              botData.positions.reduce((sum, pos) => 
                sum + (Number(pos.quantity) * Number(pos.current_price)), 0)
            )}
          </p>
        </div>
      </div>

      {botData.positions.length > 0 ? (
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
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{position.quantity}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{formatCurrency(position.entry_price)}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">{formatCurrency(position.current_price)}</td>
                    <td className={`px-4 py-3 text-sm text-right font-medium ${Number(position.pnl) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
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
    </div>
  );
};

export default BotDashboard;
