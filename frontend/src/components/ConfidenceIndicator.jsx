import React from 'react';
import { AlertCircle, InfoIcon } from 'lucide-react';

const ConfidenceIndicator = ({ signals }) => {
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return 'text-green-500';
    if (confidence >= 0.5) return 'text-yellow-500';
    return 'text-red-500';
  };

  const formatConfidence = (confidence) => {
    return `${(confidence * 100).toFixed(1)}%`;
  };

  return (
    <div className="bg-navy-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg text-blue-100">Trading Signals</h2>
        <button className="text-gray-400 hover:text-blue-100">
          <InfoIcon className="h-5 w-5" />
        </button>
      </div>
      <div className="space-y-3">
        {signals.map((signal, index) => (
          <div key={index} className="flex items-center justify-between bg-navy-900 p-3 rounded-lg">
            <div className="flex items-center space-x-3">
              <AlertCircle className={getConfidenceColor(signal.confidence)} />
              <div>
                <p className="text-sm text-blue-100">{signal.symbol}</p>
                <p className="text-xs text-gray-400">
                  {signal.signal === 'buy' ? 'Buy Signal' : 'Sell Signal'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className={`text-sm font-medium ${getConfidenceColor(signal.confidence)}`}>
                {formatConfidence(signal.confidence)}
              </p>
              <p className="text-xs text-gray-400">Confidence</p>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 p-3 bg-navy-900 rounded-lg">
        <p className="text-xs text-gray-400 text-center">
          Signals are generated using ML/AI analysis of multiple market indicators. 
          Higher confidence suggests stronger market conditions for the signal.
        </p>
      </div>
    </div>
  );
};

export default ConfidenceIndicator;