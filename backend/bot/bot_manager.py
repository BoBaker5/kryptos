# bot/bot_manager.py
import os
import logging
import asyncio
from typing import Dict, Optional, List, Any
import traceback
from datetime import datetime

class BotManager:
    def __init__(self):
        # Set up logging
        self.logger = self._setup_logging()
        self.running = True
        
        # Initialize bot states
        self.demo_running = True
        self.live_running = False
        self.live_api = None

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

    async def start_bots(self):
        """Start all trading bots"""
        try:
            self.running = True
            self.demo_running = True
            self.logger.info("Bots started successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start bots: {str(e)}")
            return False

    async def stop_bots(self):
        """Stop all trading bots"""
        try:
            self.running = False
            self.demo_running = False
            self.live_running = False
            self.logger.info("Bots stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop bots: {str(e)}")
            return False

    def get_demo_bot_status(self) -> Dict:
        """Get demo bot status"""
        try:
            return {
                'status': 'running' if self.demo_running else 'stopped',
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_live_bot_status(self) -> Dict:
        """Get live bot status"""
        try:
            return {
                'status': 'running' if self.live_running else 'stopped',
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_combined_metrics(self) -> Dict:
        """Get combined metrics from both bots"""
        try:
            return {
                'time': datetime.now().isoformat(),
                'demo_bot': self.get_demo_bot_status(),
                'live_bot': self.get_live_bot_status(),
                'system_status': {
                    'running': self.running,
                    'last_update': datetime.now().isoformat()
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting combined metrics: {str(e)}")
            return {
                'time': datetime.now().isoformat(),
                'demo_bot': {'status': 'error'},
                'live_bot': {'status': 'error'},
                'system_status': {
                    'running': self.running,
                    'last_update': datetime.now().isoformat()
                }
            }
