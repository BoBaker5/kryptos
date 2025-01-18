// App.js
import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  LineChart, 
  Activity, 
  Settings 
} from 'lucide-react';
import Header from './components/Header';
import TradingDashboard from './components/TradingDashboard';
import DemoDashboard from './components/DemoDashboard';

function App() {
  const [currentView, setCurrentView] = useState('live');

  // Navigation items configuration
  const navItems = [
    { id: 'live', label: 'Live Trading', icon: LayoutDashboard },
    { id: 'demo', label: 'Demo Account', icon: LineChart },
    { id: 'analytics', label: 'Analytics', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

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
      </div>

      {/* Main Content */}
      <div className="ml-64 flex-1 bg-gray-50">
        <Header 
          title={
            currentView === 'live' 
              ? 'Live Trading Dashboard' 
              : currentView === 'demo' 
                ? 'Demo Trading Dashboard'
                : `${navItems.find(item => item.id === currentView)?.label || ''}`
          } 
        />
        
        <main className="p-8">
          {currentView === 'live' && <TradingDashboard />}
          {currentView === 'demo' && <DemoDashboard />}
          {currentView === 'analytics' && (
            <div className="flex items-center justify-center h-64 bg-white rounded-lg shadow">
              <span className="text-lg text-gray-500">Analytics Coming Soon</span>
            </div>
          )}
          {currentView === 'settings' && (
            <div className="flex items-center justify-center h-64 bg-white rounded-lg shadow">
              <span className="text-lg text-gray-500">Settings Coming Soon</span>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;