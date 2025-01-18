import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const PerformanceChart = ({ data = [], mode }) => {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Performance History</h2>
      <div className="h-96">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis 
              dataKey="date" 
              tick={{ fill: '#666' }} 
              tickLine={{ stroke: '#666' }}
              tickFormatter={formatDate}
            />
            <YAxis 
              tick={{ fill: '#666' }} 
              tickLine={{ stroke: '#666' }}
              tickFormatter={value => `$${(value / 1000).toFixed(1)}k`}
            />
            <Tooltip 
              contentStyle={{ background: '#fff', border: '1px solid #ddd' }}
              formatter={(value, name) => {
                if (name === 'Portfolio Value') {
                  return [`$${value.toFixed(2)}`, name];
                }
                return [`${value.toFixed(2)}%`, name];
              }}
              labelFormatter={formatDate}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              name="Portfolio Value"
              stroke="#87CEEB"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="pnlPercentage"
              name="P&L %"
              stroke="#82ca9d"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PerformanceChart;