// styles/dashboardStyles.js
export const dashboardStyles = {
    mainContainer: "min-h-screen bg-gray-50",
    contentContainer: "max-w-7xl mx-auto px-6 py-6",
    
    // Cards
    cardGrid: "grid grid-cols-1 md:grid-cols-3 gap-6 mb-8",
    card: "bg-white rounded-lg shadow-sm p-6 border border-gray-200",
    cardTitle: "text-sm font-medium text-gray-600",
    cardValue: "text-2xl font-bold text-gray-900 mt-2",
    
    // Stats
    statContainer: "flex justify-between items-start",
    iconContainer: "h-10 w-10 rounded-lg border border-[#87CEEB]/30 flex items-center justify-center",
    icon: "h-6 w-6 text-[#87CEEB]",
    
    // Chart
    chartCard: "bg-white rounded-lg shadow-sm p-6 border border-gray-200 mb-8",
    chartTitle: "text-lg font-semibold text-gray-900 mb-6",
    
    // Table
    tableContainer: "bg-white rounded-lg shadow-sm border border-gray-200",
    tableHeader: "p-6 border-b border-gray-200",
    tableTitle: "text-lg font-semibold text-gray-900",
    
    // Status badge
    statusBadge: (isActive) => `
      px-3 py-1 rounded-full border 
      ${isActive 
        ? 'bg-green-100 text-green-800 border-green-200' 
        : 'bg-gray-100 text-gray-800 border-gray-200'}
    `,
  
    // Buttons
    button: "px-4 py-2 rounded-lg transition-colors duration-200",
    primaryButton: "bg-[#87CEEB] hover:bg-[#87CEEB]/90 text-white",
    stopButton: "bg-red-500 hover:bg-red-600 text-white"
  };