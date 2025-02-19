import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  LineChart, 
  Activity, 
  Settings,
  AlertCircle
} from 'lucide-react';
import { ErrorBoundary } from 'react-error-boundary';
import BotDashboard from './components/BotDashboard';

// API configuration - Direct to backend
const API_BASE_URL = 'http://150.136.163.34:8000';
const WS_BASE_URL = 'ws://150.136.163.34:8000';
const API_TIMEOUT = 10000;

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="p-6 max-w-sm mx-auto bg-white rounded-xl shadow-md flex flex-col items-center space-y-4">
      <AlertCircle className="h-6 w-6 text-red-500" />
      <div className="text-center">
        <div className="text-xl font-medium text-black">Something went wrong</div>
        <div className="text-red-500 mt-2">{error.message}</div>
      </div>
      <button
        onClick={resetErrorBoundary}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}

function App() {
  const [currentView, setCurrentView] = useState('demo');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastError, setLastError] = useState(null);

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

      const response = await fetch(`${API_BASE_URL}/api/health`, {
        signal: controller.signal,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        setConnectionStatus(data.status === 'healthy' ? 'connected' : 'degraded');
        setLastError(null);
      } else {
        throw new Error(`Server returned status ${response.status}`);
      }
    } catch (error) {
      console.error('Connection error:', error);
      setConnectionStatus('error');
      setLastError(error.message);
    }
  };

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const renderContent = () => {
    switch (currentView) {
      case 'live':
      case 'demo':
        return (
          <ErrorBoundary 
            FallbackComponent={ErrorFallback}
            onReset={checkConnection}
          >
            <BotDashboard 
              mode={currentView} 
              apiBaseUrl={API_BASE_URL}
              wsBaseUrl={WS_BASE_URL}
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

  const getConnectionStatusStyles = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-yellow-500';
    }
  };

  const getConnectionText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'degraded':
        return 'Service Degraded';
      case 'error':
        return lastError ? `Error: ${lastError}` : 'Connection Error';
      default:
        return 'Connecting...';
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
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
            </button>
          ))}
        </nav>

        {/* Connection Status */}
        <div className="absolute bottom-0 w-full p-4">
          <div className="flex items-center justify-center px-4 py-2 bg-[#002b4d] rounded">
            <div className="flex items-center">
              <div className={`h-2 w-2 rounded-full ${getConnectionStatusStyles()} mr-2`}></div>
              <span className="text-sm text-gray-400">{getConnectionText()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="ml-64 flex-1 bg-gray-50">
        <main className="h-full">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
