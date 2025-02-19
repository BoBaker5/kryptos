import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { 
  AlertCircle, 
  TrendingUp, 
  DollarSign, 
  Activity, 
  RefreshCcw,
  Clock,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

const Alert = ({ children, variant = 'default', className = '' }) => {
  const variantStyles = {
    default: 'bg-gray-100 text-gray-800',
    destructive: 'bg-red-100 text-red-800',
    success: 'bg-green-100 text-green-800',
  };

  return (
    <div className={`p-4 rounded-lg ${variantStyles[variant]} ${className}`}>
      {children}
    </div>
  );
};

const AlertTitle = ({ children }) => (
  <h5 className="font-medium mb-1">{children}</h5>
);

const AlertDescription = ({ children }) => (
  <div className="text-sm">{children}</div>
);

const BotDashboard = ({ mode = 'demo', apiBaseUrl = '' }) => {
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
  const [retryCount, setRetryCount] = useState(0);
  const [lastUpdateTime, setLastUpdateTime] = useState(new Date());

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const timestamp = new Date().getTime();
      const response = await fetch(`${apiBaseUrl}/api/${mode}-status?t=${timestamp}`, {
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.status === 'success' && data.data) {
        setBotData(data.data);
        setError(null);
        setRetryCount(0);
        setLastUpdateTime(new Date());
      } else {
        throw new Error('Invalid data format received');
      }
    } catch (err) {
      console.error('Fetch error:', err);
      setError('Unable to connect to trading bot. Server might be down or restarting.');
      if (retryCount < 3) {
        setRetryCount(prev => prev + 1);
      }
    } finally {
      setLoading(false);
    }
  }, [mode, apiBaseUrl, retryCount]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRetry = () => {
    setError(null);
    setRetryCount(0);
    fetchData();
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value / 100);
  };

  const formatQuantity = (value) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 8,
      maximumFractionDigits: 8
    }).format(value);
  };

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle>Connection Error</AlertTitle>
          <AlertDescription className="space-y-4">
            <p>{error}</p>
            <button
              onClick={handleRetry}
              className="flex items-center px-4 py-2 bg-red-100 text-red-800 rounded-md hover:bg-red-200 transition-colors"
            >
              <RefreshCcw className="h-4 w-4 mr-2" />
              Retry Connection
            </button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-slate-50 min-h-screen">
      {/* Status Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">
          {mode === 'live' ? 'Live Trading Dashboard' : 'Demo Trading Dashboard'}
        </h1>
        <div className="flex items-center space-x-4">
          <div className="flex items-center text-sm text-slate-600">
            <Clock className="h-4 w-4 mr-1" />
            Last update: {lastUpdateTime.toLocaleTimeString()}
          </div>
          <div className="flex items-center">
            <div className={`h-3 w-3 rounded-full ${botData.running ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="ml-2 text-sm font-medium text-slate-600">
              {botData.running ? 'Bot Active' : 'Bot Inactive'}
            </span>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Portfolio Value */}
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <DollarSign className="h-5 w-5 text-blue-500" />
            <h2 className="text-sm font-medium text-slate-600">Portfolio Value</h2>
          </div>
          <div className="mt-4">
            <p className="text-2xl font-bold text-slate-800">
              {formatCurrency(botData.portfolio_value)}
            </p>
            <p className="text-sm text-slate-500">
              Initial: {formatCurrency(100000)}
            </p>
          </div>
        </div>

        {/* Total P&L */}
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-green-500" />
            <h2 className="text-sm font-medium text-slate-600">Total P&L</h2>
          </div>
          <div className="mt-4">
            <div className="flex items-center">
              <p className="text-2xl font-bold text-slate-800">
                {formatCurrency(botData.pnl)}
              </p>
              <div className={`ml-2 flex items-center ${botData.pnl_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {botData.pnl_percentage >= 0 ? 
                  <ArrowUpRight className="h-4 w-4" /> : 
                  <ArrowDownRight className="h-4 w-4" />
                }
                <span className="text-sm font-medium">
                  {formatPercent(botData.pnl_percentage)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Active Positions */}
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-purple-500" />
            <h2 className="text-sm font-medium text-slate-600">Active Positions</h2>
          </div>
          <div className="mt-4">
            <p className="text-2xl font-bold text-slate-800">
              {botData.positions.length}
            </p>
            <p className="text-sm text-slate-500">
              Total value: {formatCurrency(
                botData.positions.reduce((sum, pos) => 
                  sum + (parseFloat(pos.quantity) * parseFloat(pos.current_price)), 0)
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Positions Table */}
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
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">Value</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {botData.positions.map((position) => (
                  <tr key={position.symbol}>
                    <td className="px-4 py-3 text-sm text-slate-800 font-medium">
                      {position.symbol}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">
                      {formatQuantity(parseFloat(position.quantity))}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">
                      {formatCurrency(parseFloat(position.entry_price))}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">
                      {formatCurrency(parseFloat(position.current_price))}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 text-right">
                      {formatCurrency(parseFloat(position.quantity) * parseFloat(position.current_price))}
                    </td>
                    <td className={`px-4 py-3 text-sm text-right font-medium ${parseFloat(position.pnl) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      <div className="flex items-center justify-end">
                        {parseFloat(position.pnl) >= 0 ? 
                          <ArrowUpRight className="h-4 w-4 mr-1" /> : 
                          <ArrowDownRight className="h-4 w-4 mr-1" />
                        }
                        <span>
                          {formatCurrency(parseFloat(position.pnl))}
                          <span className="ml-1 text-xs">
                            ({formatPercent(parseFloat(position.pnl_percentage))})
                          </span>
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm p-6 text-center">
          <p className="text-slate-600">No active positions</p>
        </div>
      )}

      {loading && (
        <div className="fixed bottom-4 right-4">
          <div className="bg-white rounded-full shadow-lg p-2">
            <RefreshCcw className="h-5 w-5 text-blue-500 animate-spin" />
          </div>
        </div>
      )}
    </div>
  );
};

export default BotDashboard;
