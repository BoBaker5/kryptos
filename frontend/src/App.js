import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  LineChart, 
  Activity, 
  Settings,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import { ErrorBoundary } from 'react-error-boundary';
import BotDashboard from './components/BotDashboard';

// API configuration
const API_TIMEOUT = 10000;

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="p-6 max-w-sm mx-auto bg-white rounded-xl shadow-md flex flex-col items-center space-y-4">
      <AlertCircle className="h-6 w-6 text-red-500" />
      <div className="text-center">
        <div className="text-xl font-medium text-black">Connection Error</div>
        <div className="text-red-500 mt-2">{error.message}</div>
      </div>
      <button
        onClick={resetErrorBoundary}
        className="flex items-center px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
      >
        <RefreshCw className="h-4 w-4 mr-2" />
        Retry Connection
      </button>
    </div>
  );
}

function App() {
  const [currentView, setCurrentView] = useState('demo');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastError, setLastError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [botStatus, setBotStatus] = useState({
    demo: false,
    live: false
  });

  const navItems = [
    { id: 'live', label: 'Live Trading', icon: LayoutDashboard },
    { id: 'demo', label: 'Demo Account', icon: LineChart },
    { id: 'analytics', label: 'Analytics', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  const checkConnection = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

      const response = await fetch('/api/health', {
        signal: controller.signal,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server Error (${response.status}): ${errorText || 'No additional info'}`);
      }

      const data = await response.json();
      
      if (data.status === 'healthy') {
        setConnectionStatus('connected');
        setBotStatus({
          demo: data.bots?.demo?.running || false,
          live: data.bots?.live?.running || false
        });
        setLastError(null);
        setRetryCount(0);
      } else {
        throw new Error(data.error || 'Service degraded');
      }
    } catch (error) {
      console.error('Connection error:', error);
      setConnectionStatus('error');
      setLastError(error.message);
      
      if (retryCount < 3) {
        const backoffDelay = Math.pow(2, retryCount) * 1000;
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          checkConnection();
        }, backoffDelay);
      }
    }
  };

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRetry = () => {
    setRetryCount(0);
    setLastError(null);
    checkConnection();
  };

  const renderContent = () => {
    switch (currentView) {
      case 'live':
      case 'demo':
        return (
          <ErrorBoundary 
            FallbackComponent={ErrorFallback}
            onReset={handleRetry}
            resetKeys={[currentView]}
          >
            <BotDashboard 
              mode={currentView} 
              onError={setLastError}
              isRunning={botStatus[currentView]}
            />
          </ErrorBoundary>
        );
      case 'analytics':
      case 'settings':
        return (
          <div className="flex items-center justify-center h-[calc(100vh-2rem)] bg-white rounded-lg shadow-sm m-4">
            <div className="text-lg text-slate-600">
              {currentView === 'analytics' ? 'Analytics' : 'Settings'} Dashboard Coming Soon
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex min-h-screen">
      <div className="w-64 bg-[#001F3F] fixed h-full">
        <div className="flex items-center px-6 py-4">
          <span className="text-[#87CEEB] font-bold text-xl">KRYPTOS</span>
        </div>
        
        <nav className="mt-8">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              className={`w-full flex items-center px-6 py-3 text-sm font-medium transition-colors
                ${currentView === item.id 
                  ? 'text-[#87CEEB] bg-[#87CEEB]/10' 
                  : 'text-gray-400 hover:text-[#87CEEB] hover:bg-[#87CEEB]/5'}`}
            >
              <item.icon className="h-5 w-5 mr-3" />
              {item.label}
              {(item.id === 'demo' || item.id === 'live') && (
                <div className={`ml-auto h-2 w-2 rounded-full ${
                  botStatus[item.id] ? 'bg-green-500' : 'bg-red-500'
                }`} />
              )}
            </button>
          ))}
        </nav>

        <div className="absolute bottom-0 w-full p-4">
          <div className="flex items-center justify-center px-4 py-2 bg-[#002b4d] rounded">
            <div className="flex items-center">
              <div className={`h-2 w-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-500' :
                connectionStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500'
              } mr-2`} />
              <span className="text-sm text-gray-400">
                {connectionStatus === 'error' ? (
                  <button 
                    onClick={handleRetry}
                    className="flex items-center hover:text-[#87CEEB]"
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Retry Connection
                  </button>
                ) : (
                  connectionStatus.charAt(0).toUpperCase() + connectionStatus.slice(1)
                )}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="ml-64 flex-1 bg-gray-50">
        <main className="h-full">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
