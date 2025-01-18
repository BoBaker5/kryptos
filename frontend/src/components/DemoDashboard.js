import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Cpu, TrendingUp } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const Dashboard = () => {
  const [botData, setBotData] = useState({
    status: 'loading',
    positions: [],
    portfolio_value: 1000000,
    daily_pnl: 0,
    performance_metrics: []
  });

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${API_URL}/demo-status`);
        setBotData(response.data);
      } catch (err) {
        console.error('Error:', err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#000B18]">
      <header className="bg-[#001F3F] border-b border-[#87CEEB]/30">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <img src="/logo.svg" alt="Kryptos" className="h-12" />
              <div className={`px-3 py-1 rounded border border-[#87CEEB]/50 ${
                botData.status === 'running' 
                  ? 'bg-[#87CEEB]/10 text-[#87CEEB]' 
                  : 'bg-[#001F3F] text-[#87CEEB]/50'
              }`}>
                {botData.status === 'running' ? 'AI ACTIVE' : 'AI STANDBY'}
              </div>
            </div>
            <Cpu className="h-6 w-6 text-[#87CEEB]" />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-[#001F3F] rounded-lg border border-[#87CEEB]/30 p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[#87CEEB]/70 text-sm">Portfolio Value</p>
                <p className="text-[#87CEEB] text-2xl font-bold mt-2">
                  ${botData.portfolio_value.toLocaleString()}
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg border border-[#87CEEB]/30 flex items-center justify-center">
                <Activity className="h-6 w-6 text-[#87CEEB]" />
              </div>
            </div>
          </div>

          <div className="bg-[#001F3F] rounded-lg border border-[#87CEEB]/30 p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[#87CEEB]/70 text-sm">24h Profit/Loss</p>
                <p className={`text-2xl font-bold mt-2 ${
                  botData.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {botData.daily_pnl >= 0 ? '+' : ''}{botData.daily_pnl.toFixed(2)}%
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg border border-[#87CEEB]/30 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-[#87CEEB]" />
              </div>
            </div>
          </div>

          <div className="bg-[#001F3F] rounded-lg border border-[#87CEEB]/30 p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[#87CEEB]/70 text-sm">Active Positions</p>
                <p className="text-[#87CEEB] text-2xl font-bold mt-2">
                  {botData.positions.length}
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg border border-[#87CEEB]/30 flex items-center justify-center">
                <Activity className="h-6 w-6 text-[#87CEEB]" />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-[#001F3F] rounded-lg border border-[#87CEEB]/30 p-6 mb-8">
          <h2 className="text-[#87CEEB] text-lg font-bold mb-6">Performance History</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={botData.performance_metrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#87CEEB30" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(time) => new Date(time).toLocaleTimeString()} 
                  stroke="#87CEEB80"
                />
                <YAxis stroke="#87CEEB80" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#001F3F', 
                    border: '1px solid #87CEEB50',
                    color: '#87CEEB' 
                  }}
                  formatter={(value) => ['$' + value.toLocaleString(), 'Portfolio Value']}
                  labelFormatter={(label) => new Date(label).toLocaleString()}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#87CEEB" 
                  strokeWidth={2}
                  dot={false}
                  name="Portfolio Value"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#001F3F] rounded-lg border border-[#87CEEB]/30">
          <div className="p-6 border-b border-[#87CEEB]/30">
            <h2 className="text-[#87CEEB] text-lg font-bold">Active Positions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#87CEEB]/30">
                  <th className="text-left text-[#87CEEB]/70 text-sm font-medium p-4">Symbol</th>
                  <th className="text-right text-[#87CEEB]/70 text-sm font-medium p-4">Quantity</th>
                  <th className="text-right text-[#87CEEB]/70 text-sm font-medium p-4">Entry Price</th>
                  <th className="text-right text-[#87CEEB]/70 text-sm font-medium p-4">Current Price</th>
                  <th className="text-right text-[#87CEEB]/70 text-sm font-medium p-4">P/L %</th>
                </tr>
              </thead>
              <tbody>
                {botData.positions.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center text-[#87CEEB]/50 p-4">
                      No active positions
                    </td>
                  </tr>
                ) : (
                  botData.positions.map((position, index) => (
                    <tr key={index} className="border-b border-[#87CEEB]/10">
                      <td className="text-[#87CEEB] p-4">{position.symbol}</td>
                      <td className="text-right text-[#87CEEB] p-4">
                        {position.quantity.toFixed(4)}
                      </td>
                      <td className="text-right text-[#87CEEB] p-4">
                        ${position.entry_price.toFixed(4)}
                      </td>
                      <td className="text-right text-[#87CEEB] p-4">
                        ${position.current_price.toFixed(4)}
                      </td>
                      <td className={`text-right p-4 ${
                        position.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {position.pnl >= 0 ? '+' : ''}{position.pnl.toFixed(2)}%
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;