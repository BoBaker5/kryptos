// DashboardLayout.js
import React, { useState } from 'react';
import { LayoutDashboard, PieChart, Settings, LineChart } from 'lucide-react';

const DashboardLayout = ({ children }) => {
  const [currentPage, setCurrentPage] = useState('dashboard');

  const navItems = [
    { id: 'dashboard', label: 'Live Trading', icon: LayoutDashboard },
    { id: 'demo', label: 'Demo Account', icon: LineChart },
    { id: 'analytics', label: 'Analytics', icon: PieChart },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <div className="w-64 bg-[#000B18] fixed h-full">
        {/* Logo Container */}
        <div className="h-20 flex items-center justify-center border-b border-[#87CEEB]/20">
          <img src="/logo.svg" alt="Kryptos AI" className="h-12" />
        </div>

        {/* Navigation */}
        <nav className="mt-8">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`w-full flex items-center px-6 py-3 text-base font-medium transition-colors
                  ${currentPage === item.id 
                    ? 'text-[#87CEEB] bg-[#87CEEB]/10' 
                    : 'text-gray-400 hover:text-[#87CEEB] hover:bg-[#87CEEB]/5'}`}
              >
                <Icon className="h-5 w-5 mr-3" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Main Content */}
      <div className="ml-64 flex-1 bg-slate-50">
        {children}
      </div>
    </div>
  );
};

export default DashboardLayout;