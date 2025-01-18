# backend/bot/demo_service.py
import asyncio
import logging
from typing import Optional
from datetime import datetime
import signal
import sys

from .demo_bot import DemoTradingBot

class DemoBotService:
    def __init__(self):
        self.logger = logging.getLogger("DemoBotService")
        self.demo_bot: Optional[DemoTradingBot] = None
        self.should_restart = True
        
    async def start_bot(self):
        """Start the demo bot with automatic restart on failure"""
        while self.should_restart:
            try:
                self.logger.info("Starting demo bot service...")
                self.demo_bot = DemoTradingBot(initial_balance=10000.0)
                await self.demo_bot.run()
            except Exception as e:
                self.logger.error(f"Demo bot crashed: {str(e)}")
                self.logger.info("Restarting demo bot in 10 seconds...")
                await asyncio.sleep(10)
            finally:
                if self.demo_bot:
                    self.demo_bot.stop()
                    self.demo_bot = None
    
    def stop(self):
        """Stop the demo bot service"""
        self.should_restart = False
        if self.demo_bot:
            self.demo_bot.stop()
            
    def get_bot_status(self):
        """Get current bot status"""
        if self.demo_bot:
            return self.demo_bot.get_status()
        return {
            'status': 'stopped',
            'error': 'Demo bot not running'
        }

# Standalone service runner
async def run_service():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('demo_bot.log')
        ]
    )
    
    service = DemoBotService()
    
    def handle_shutdown(signum, frame):
        print("\nShutting down demo bot service...")
        service.stop()
        
    # Register shutdown handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    await service.start_bot()

if __name__ == "__main__":
    asyncio.run(run_service())