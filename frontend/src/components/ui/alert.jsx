import React from 'react';

export const Alert = ({ children, variant = 'default', className = '' }) => {
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

export const AlertTitle = ({ children, className = '' }) => (
  <h5 className={`font-medium mb-1 ${className}`}>{children}</h5>
);

export const AlertDescription = ({ children, className = '' }) => (
  <div className={`text-sm ${className}`}>{children}</div>
);

Alert.displayName = 'Alert';
AlertTitle.displayName = 'AlertTitle';
AlertDescription.displayName = 'AlertDescription';
