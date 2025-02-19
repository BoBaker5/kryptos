import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp, DollarSign, Activity } from 'lucide-react';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';

const BotDashboard = ({ mode = 'demo', apiBaseUrl, wsBaseUrl }) => {
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
        const response = await fetch(`${apiBaseUrl}/api/${mode}-status`);
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
  }, [mode, apiBaseUrl]);

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
      {/* Rest of your component remains the same */}
    </div>
  );
};

export default BotDashboard;
