import React, { useState, useEffect } from 'react';
import { 
  ArrowUp, 
  ArrowDown,
  RefreshCw,
  TrendingUp,
  TrendingDown
} from 'lucide-react';

const TradeHistoryTable = () => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchTradeHistory = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/trade-history');
      
      if (!response.ok) {
        throw new Error(`Failed to fetch trade history: ${response.statusText}`);
      }
      
      const data = await response.json();
      setTrades(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching trade history:', err);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchTradeHistory();
    
    // Set up refresh interval
    const intervalId = setInterval(fetchTradeHistory, 60000); // Refresh every minute
    
    return () => clearInterval(intervalId);
  }, []);
  
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  const formatCurrency = (value) => {
    return `$${parseFloat(value).toFixed(2)}`;
  };
  
  const formatPercentage = (value) => {
    return `${parseFloat(value).toFixed(2)}%`;
  };
  
  if (loading && trades.length === 0) {
    return (
      <div className="flex items-center justify-center h-40">
        <RefreshCw className="animate-spin h-6 w-6 text-blue-500 mr-2" />
        <span>Loading trade history...</span>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        <p>Error loading trade history: {error}</p>
        <button 
          onClick={fetchTradeHistory}
          className="mt-2 bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded flex items-center"
        >
          <RefreshCw className="h-4 w-4 mr-1" /> Retry
        </button>
      </div>
    );
  }
  
  if (trades.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 text-gray-700 px-4 py-6 rounded text-center">
        <p>No trades have been executed yet.</p>
      </div>
    );
  }
  
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <h3 className="text-lg font-medium">Trade History</h3>
        <button 
          onClick={fetchTradeHistory} 
          className="flex items-center text-sm text-gray-600 hover:text-blue-600"
        >
          <RefreshCw className="h-4 w-4 mr-1" /> Refresh
        </button>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date/Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Symbol
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quantity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Value
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Profit/Loss
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {trades.map((trade, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatDate(trade.timestamp)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {trade.symbol}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    trade.type === 'buy' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {trade.type === 'buy' ? <ArrowDown className="h-3 w-3 mr-1" /> : <ArrowUp className="h-3 w-3 mr-1" />}
                    {trade.type.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatCurrency(trade.price)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {parseFloat(trade.quantity).toFixed(8)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatCurrency(trade.value)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {trade.pnl !== 0 && (
                    <div className={`flex items-center ${
                      trade.pnl > 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {trade.pnl > 0 ? 
                        <TrendingUp className="h-4 w-4 mr-1" /> : 
                        <TrendingDown className="h-4 w-4 mr-1" />
                      }
                      <span>{formatCurrency(trade.pnl)}</span>
                      <span className="ml-1 text-xs">({formatPercentage(trade.pnl_percentage)})</span>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TradeHistoryTable;
