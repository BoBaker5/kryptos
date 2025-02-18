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
        self.demo_initial_balance = 100000.00  # Set initial demo balance

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
        if self.demo_running:
            self.logger.warning("Demo bot already running")
            return True

        try:
            # Initialize with basic configuration
            self.demo_bot = {
                'status': 'running',
                'balance': {'ZUSD': self.demo_initial_balance},
                'positions': {},
                'last_update': datetime.now()
            }
            self.demo_running = True
            
            self.logger.info(f"Demo bot started successfully with balance: ${self.demo_initial_balance}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error starting demo bot: {e}")
            self.demo_running = False
            self.demo_bot = None
            raise e

    async def get_demo_metrics(self) -> Dict:
        """Get demo bot metrics with proper P&L calculation"""
        if not self.demo_bot or not self.demo_running:
            return {
                "current_equity": self.demo_initial_balance,
                "pnl": 0,
                "pnl_percentage": 0
            }
        
        try:
            # Calculate total value including positions
            total_value = self.demo_bot['balance'].get('ZUSD', self.demo_initial_balance)
            positions = self.demo_bot.get('positions', {})
            
            # Calculate P&L
            pnl = total_value - self.demo_initial_balance
            pnl_percentage = (pnl / self.demo_initial_balance) * 100

            return {
                "current_equity": total_value,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage
            }
        except Exception as e:
            self.logger.error(f"Error getting demo metrics: {e}")
            return {
                "current_equity": self.demo_initial_balance,
                "pnl": 0,
                "pnl_percentage": 0
            }

    async def get_demo_positions(self) -> List:
        """Get demo bot positions"""
        if not self.demo_bot or not self.demo_running:
            return []
        
        try:
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
        if not self.demo_bot or not self.demo_running:
            return {"ZUSD": self.demo_initial_balance}
        
        try:
            return self.demo_bot.get('balance', {"ZUSD": self.demo_initial_balance})
        except Exception as e:
            self.logger.error(f"Error getting demo balance: {e}")
            return {"ZUSD": self.demo_initial_balance}

    async def start_live_bot(self, api_key: str, secret_key: str) -> bool:
        """Start the live trading bot"""
        if self.live_running:
            self.logger.warning("Live bot already running")
            return True

        try:
            self.live_bot = {
                'status': 'running',
                'api_key': api_key,
                'secret_key': secret_key,
                'balance': {},
                'positions': [],
                'last_update': datetime.now()
            }
            self.live_running = True
            
            self.logger.info("Live bot started successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Error starting live bot: {e}")
            self.live_running = False
            self.live_bot = None
            raise e

    async def stop_live_bot(self) -> bool:
        """Stop the live trading bot"""
        try:
            if self.live_bot:
                self.live_running = False
                self.live_bot = None
                self.logger.info("Live bot stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping live bot: {e}")
            raise e

    async def get_live_metrics(self) -> Dict:
        """Get live bot metrics"""
        if not self.live_bot or not self.live_running:
            return {
                "current_equity": 0,
                "pnl": 0,
                "pnl_percentage": 0
            }
        
        try:
            metrics = {
                "current_equity": 0,
                "pnl": 0,
                "pnl_percentage": 0
            }
            return metrics
        except Exception as e:
            self.logger.error(f"Error getting live metrics: {e}")
            return {
                "current_equity": 0,
                "pnl": 0,
                "pnl_percentage": 0
            }

    async def get_live_positions(self) -> List:
        """Get live bot positions"""
        if not self.live_bot or not self.live_running:
            return []
        
        try:
            return self.live_bot.get('positions', [])
        except Exception as e:
            self.logger.error(f"Error getting live positions: {e}")
            return []

    async def get_live_balance(self) -> Dict:
        """Get live bot balance"""
        if not self.live_bot or not self.live_running:
            return {}
        
        try:
            return self.live_bot.get('balance', {})
        except Exception as e:
            self.logger.error(f"Error getting live balance: {e}")
            return {}

    def get_bot_status(self, mode: str = 'demo') -> Dict:
        """Get comprehensive bot status"""
        try:
            if mode == 'demo':
                return {
                    'running': self.demo_running,
                    'status': 'running' if self.demo_running else 'stopped',
                    'last_update': datetime.now().isoformat(),
                    'bot_data': self.demo_bot
                }
            else:
                return {
                    'running': self.live_running,
                    'status': 'running' if self.live_running else 'stopped',
                    'last_update': datetime.now().isoformat(),
                    'bot_data': self.live_bot
                }
        except Exception as e:
            self.logger.error(f"Error getting bot status: {e}")
            return {
                'running': False,
                'status': 'error',
                'error': str(e),
                'last_update': datetime.now().isoformat()
            }

    def get_combined_metrics(self) -> Dict:
        """Get combined metrics from both bots"""
        try:
            return {
                'time': datetime.now().isoformat(),
                'demo_bot': self.get_bot_status('demo'),
                'live_bot': self.get_bot_status('live'),
                'system_status': {
                    'running': self.demo_running or self.live_running,
                    'last_update': datetime.now().isoformat()
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting combined metrics: {e}")
            return {
                'time': datetime.now().isoformat(),
                'demo_bot': {'status': 'error'},
                'live_bot': {'status': 'error'},
                'system_status': {
                    'running': False,
                    'error': str(e),
                    'last_update': datetime.now().isoformat()
                }
            }
