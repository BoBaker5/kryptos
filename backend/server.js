const express = require('express');
const cors = require('cors');
const KrakenClient = require('kraken-api');

const app = express();
const port = 5000;

// Store bot states and performance history
const botState = {
  live: false,
  demo: true
};

const botPerformanceHistory = {
  live: [],
  demo: []
};

const activeBots = new Map();

app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true
}));

app.use(express.json());

function updatePerformanceHistory(mode, metrics) {
  const entry = {
    date: new Date().toISOString(),
    value: metrics.current_equity,
    pnl: metrics.pnl,
    pnlPercentage: metrics.pnl_percentage
  };

  botPerformanceHistory[mode].push(entry);
  
  // Keep last 30 days of data
  if (botPerformanceHistory[mode].length > 30) {
    botPerformanceHistory[mode].shift();
  }
}

async function getKrakenBalance(kraken) {
  try {
    const balance = await kraken.api('Balance');
    let totalUSD = 0;
    // Calculate total balance in USD
    for (const [asset, amount] of Object.entries(balance)) {
      const ticker = await kraken.api('Ticker', { pair: `${asset}USD` });
      const price = ticker[Object.keys(ticker)[0]].c[0];
      totalUSD += amount * price;
    }
    return totalUSD;
  } catch (error) {
    console.error('Error getting Kraken balance:', error);
    return 0;
  }
}

app.get('/bot-status/:mode', async (req, res) => {
  const { mode } = req.params;
  
  try {
    let metrics = {
      current_equity: 0,
      pnl: 0,
      pnl_percentage: 0
    };

    if (mode === 'live' && activeBots.has('live')) {
      const kraken = activeBots.get('live').kraken;
      const currentBalance = await getKrakenBalance(kraken);
      const initialBalance = activeBots.get('live').initialBalance;
      
      metrics = {
        current_equity: currentBalance,
        pnl: currentBalance - initialBalance,
        pnl_percentage: ((currentBalance - initialBalance) / initialBalance) * 100
      };
    } else if (mode === 'demo') {
      // Demo bot simulated performance
      const lastValue = botPerformanceHistory.demo.length > 0 
        ? botPerformanceHistory.demo[botPerformanceHistory.demo.length - 1].value 
        : 1000000;
      
      metrics = {
        current_equity: lastValue,
        pnl: lastValue - 1000000,
        pnl_percentage: ((lastValue - 1000000) / 1000000) * 100
      };
    }

    updatePerformanceHistory(mode, metrics);

    res.json({
      status: 'success',
      data: {
        status: botState[mode] ? 'running' : 'stopped',
        positions: [],
        metrics,
        trades: [],
        performanceHistory: botPerformanceHistory[mode]
      }
    });
  } catch (error) {
    console.error('Error getting bot status:', error);
    res.status(500).json({ status: 'error', message: error.message });
  }
});

app.post('/start-bot/:mode', async (req, res) => {
  const { mode } = req.params;
  const { apiKey, apiSecret } = req.body;

  try {
    if (mode === 'live') {
      const kraken = new KrakenClient(apiKey, apiSecret);
      const initialBalance = await getKrakenBalance(kraken);
      
      activeBots.set('live', {
        kraken,
        initialBalance,
        startTime: new Date()
      });
    }
    
    botState[mode] = true;
    res.json({ status: 'success' });
  } catch (error) {
    console.error('Error starting bot:', error);
    res.status(400).json({ 
      status: 'error', 
      message: 'Failed to start bot: ' + error.message 
    });
  }
});

app.post('/stop-bot/:mode', (req, res) => {
  const { mode } = req.params;
  
  if (mode === 'live') {
    activeBots.delete('live');
  }
  
  botState[mode] = false;
  res.json({ status: 'success' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
  
  // Initialize demo bot performance history with starting value
  if (botPerformanceHistory.demo.length === 0) {
    updatePerformanceHistory('demo', {
      current_equity: 1000000,
      pnl: 0,
      pnl_percentage: 0
    });
  }
});