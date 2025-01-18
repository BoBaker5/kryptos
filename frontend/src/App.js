// App.js
import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  LineChart, 
  Activity, 
  Settings 
} from 'lucide-react';
import Header from './components/Header';
import BotDashboard from './components/BotDashboard';

function App() {
  const [currentView, setCurrentView] = useState('live');
  
  const navItems = [
    { id: 'live', label: 'Live Trading', icon: LayoutDashboard },
    { id: 'demo', label: 'Demo Account', icon: LineChart },
    { id: 'analytics', label: 'Analytics', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  const renderContent = () => {
    switch (currentView) {
      case 'live':
        return <BotDashboard mode="live" />;
      case 'demo':
        return <BotDashboard mode="demo" />;
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
        return <BotDashboard mode="live" />;
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
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
        {/* Connection Status */}
        <div className="absolute bottom-0 w-full p-4">
          <div className="flex items-center justify-center px-4 py-2 bg-[#002b4d] rounded">
            <div className="flex items-center">
              <div className="h-2 w-2 rounded-full bg-green-500 mr-2"></div>
              <span className="text-sm text-gray-400">Connected</span>
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