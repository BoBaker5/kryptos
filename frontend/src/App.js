import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  LineChart, 
  Activity, 
  Settings 
} from 'lucide-react';
import BotDashboard from './components/BotDashboard';

// API configuration
const API_BASE_URL = 'https://150.136.163.34:8000'; // Update with your domain
const API_TIMEOUT = 10000; // 10 seconds

function App() {
  const [currentView, setCurrentView] = useState('demo');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

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
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('error');
      }
    } catch (error) {
      console.error('Connection error:', error);
      setConnectionStatus('error');
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
        return <BotDashboard mode="live" apiBaseUrl={API_BASE_URL} />;
      case 'demo':
        return <BotDashboard mode="demo" apiBaseUrl={API_BASE_URL} />;
      case 'analytics':
        return (
          <div className="flex items-center justify-center h-screen">
            <div className="text-lg text-gray-600">Analytics Dashboard Coming Soon</div>
          </div>
        );
      case 'settings':
        return (
          <div className="flex items-center justify-center h-screen">
            <div className="text-lg text-gray-600">Settings Dashboard Coming Soon</div>
          </div>
        );
      default:
        return <BotDashboard mode="demo" apiBaseUrl={API_BASE_URL} />;
    }
  };

  const getConnectionStatusStyles = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
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
      case 'error':
        return 'Connection Error';
      default:
        return 'Connecting...';
    }
  };

  return (
    <div className="flex min-h-screen">
      <div className="w-64 bg-[#001F3F] fixed h-full">
        <div className="flex items-center px-6 py-4">
          <img src="/logo.svg" alt="Kryptos" className="h-10" />
          <span className="ml-2 text-[#87CEEB] font-bold text-xl">KRYPTOS</span>
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

        <div className="absolute bottom-0 w-full p-4">
          <div className="flex items-center justify-center px-4 py-2 bg-[#002b4d] rounded">
            <div className="flex items-center">
              <div className={`h-2 w-2 rounded-full ${getConnectionStatusStyles()} mr-2`}></div>
              <span className="text-sm text-gray-400">{getConnectionText()}</span>
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
