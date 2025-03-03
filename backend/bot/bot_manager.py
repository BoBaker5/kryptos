import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel

class BotManager:
    def __init__(self):
        """Initialize the bot manager"""
        self.logger = self._setup_logging()
        self.demo_running = False
        self.live_running = False
        self.live_bot = None
        self.demo_bot = None
        self.polling_task = None
        self.demo_initial_balance = 100000.00
        self._lock = asyncio.Lock()  # Add lock for thread safety

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration"""
        logger = logging.getLogger("bot.manager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    async def start_demo_bot(self) -> bool:
        """Start the demo trading bot"""
        async with self._lock:
            if self.demo_running:
                self.logger.warning("Demo bot already running")
                return True

            try:
                self.demo_bot = {
                    'status': 'running',
                    'balance': {'ZUSD': self.demo_initial_balance},
                    'positions': {},
                    'last_update': datetime.now(),
                    'trade_history': []  # Initialize empty trade history
                }
                self.demo_running = True
                
                self.logger.info(f"Demo bot started with balance: ${self.demo_initial_balance}")
                return True
            
            except Exception as e:
                self.logger.error(f"Error starting demo bot: {e}")
                self.demo_running = False
                self.demo_bot = None
                raise e

    async def get_demo_metrics(self) -> Dict:
        """Get demo bot metrics with proper P&L calculation"""
        async with self._lock:
            try:
                if not self.demo_bot or not self.demo_running:
                    return {
                        "current_equity": float(self.demo_initial_balance),
                        "pnl": 0.0,
                        "pnl_percentage": 0.0
                    }
                
                total_value = float(self.demo_bot['balance'].get('ZUSD', self.demo_initial_balance))
                pnl = float(total_value - self.demo_initial_balance)
                pnl_percentage = float((pnl / self.demo_initial_balance) * 100)
        
                return {
                    "current_equity": total_value,
                    "pnl": pnl,
                    "pnl_percentage": pnl_percentage
                }
            except Exception as e:
                self.logger.error(f"Error getting demo metrics: {e}")
                return {
                    "current_equity": float(self.demo_initial_balance),
                    "pnl": 0.0,
                    "pnl_percentage": 0.0
                }

    async def get_demo_positions(self) -> List:
        """Get demo bot positions"""
        async with self._lock:
            try:
                if not self.demo_bot or not self.demo_running:
                    return []
                
                positions = []
                for symbol, pos in self.demo_bot.get('positions', {}).items():
                    positions.append({
                        "symbol": symbol,
                        "quantity": pos.get('volume', 0),
                        "entry_price": pos.get('entry_price', 0),
                        "current_price": pos.get('current_price', 0),
                        "pnl": pos.get('pnl', 0),
                        "pnl_percentage": pos.get('pnl_percentage', 0)
                    })
                return positions
            except Exception as e:
                self.logger.error(f"Error getting demo positions: {e}")
                return []

    async def get_demo_balance(self) -> Dict:
        """Get demo bot balance"""
        async with self._lock:
            try:
                if not self.demo_bot or not self.demo_running:
                    return {"ZUSD": float(self.demo_initial_balance)}
                
                return {k: float(v) for k, v in self.demo_bot.get('balance', {"ZUSD": self.demo_initial_balance}).items()}
            except Exception as e:
                self.logger.error(f"Error getting demo balance: {e}")
                return {"ZUSD": float(self.demo_initial_balance)}
    
    async def get_demo_trade_history(self) -> List:
        """Get demo bot trade history"""
        async with self._lock:
            try:
                self.logger.info("Fetching demo trade history...")
                if not self.demo_bot or not self.demo_running:
                    return []
                
                # Try to get trade history from the demo bot
                try:
                    # First attempt to get from the demo_bot instance directly
                    if hasattr(self.demo_bot, 'trade_history'):
                        trade_history = self.demo_bot.trade_history
                    # Fallback to dictionary access if it's stored that way
                    else:
                        trade_history = self.demo_bot.get('trade_history', [])
                    
                    # Format trades
                    formatted_trades = []
                    for trade in trade_history:
                        # Skip any system trades if needed
                        if isinstance(trade, dict) and trade.get('symbol') == 'SYSTEM':
                            continue
                            
                        # Format the trade record
                        try:
                            formatted_trade = {
                                'timestamp': trade['timestamp'].isoformat() if isinstance(trade.get('timestamp'), datetime) else trade.get('timestamp', ''),
                                'symbol': trade.get('symbol', 'Unknown'),
                                'type': trade.get('type', 'Unknown'),
                                'price': float(trade.get('price', 0)),
                                'quantity': float(trade.get('quantity', 0)),
                                'value': float(trade.get('value', 0)),
                                'profit_loss': float(trade.get('profit_loss', 0)),
                                'pnl_percentage': float(trade.get('pnl_percentage', 0)),
                                'entry_price': float(trade.get('entry_price', 0)) if 'entry_price' in trade else 0
                            }
                            formatted_trades.append(formatted_trade)
                        except Exception as format_error:
                            self.logger.error(f"Error formatting trade: {format_error}")
                            continue
                            
                    return formatted_trades
                    
                except Exception as access_error:
                    self.logger.error(f"Error accessing trade history: {access_error}")
                    return []
                    
            except Exception as e:
                self.logger.error(f"Error getting demo trade history: {str(e)}")
                return []
