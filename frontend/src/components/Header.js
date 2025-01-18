// components/Header.js
import React from 'react';

const Header = ({ title }) => {
  return (
    <div className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200">
      <div className="flex items-center gap-3">
        <div className="flex items-center">
          <img src="/logo.svg" alt="Kryptos" className="h-10 w-10" />
          <span className="ml-2 text-xl font-bold text-[#001F3F]">KRYPTOS</span>
        </div>
        <div className="h-6 w-px bg-gray-300"></div>
        <h1 className="text-xl font-semibold text-gray-700">{title}</h1>
      </div>
    </div>
  );
};

export default Header;