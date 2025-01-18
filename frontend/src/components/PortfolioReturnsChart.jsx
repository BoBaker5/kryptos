import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

const PortfolioReturnsChart = ({ data }) => {
  return (
    <div className="w-full h-96 bg-navy-800 rounded-lg p-4">
      <h2 className="text-lg text-blue-100 mb-4">Portfolio Returns</h2>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a8a" />
          <XAxis 
            dataKey="timestamp" 
            stroke="#94a3b8"
            tickFormatter={(time) => new Date(time).toLocaleTimeString()} 
          />
          <YAxis 
            stroke="#94a3b8"
            tickFormatter={(value) => `${value.toFixed(2)}%`}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e3a8a' }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value) => [`${value.toFixed(2)}%`, 'Return']}
          />
          <ReferenceLine y={0} stroke="#475569" />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="return" 
            stroke="#22c55e" 
            dot={false}
            name="Return %"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PortfolioReturnsChart;