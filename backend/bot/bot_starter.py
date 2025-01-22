# backend/bot/bot_starter.py
import asyncio
import logging
from typing import Optional
from datetime import datetime
from .bot_manager import BotManager
from .demo_service import DemoBotService

class BotStarter:
    def __init__(self):
        self.logger = self._setup_logging()
        self.bot_manager = BotManager()
        self.demo_service = DemoBotService()
        self.is_running = False

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration"""
        logger = logging.getLogger("BotStarter")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    async def start_all(self):
        """Start both demo and live services"""
        try:
            self.is_running = True
            self.logger.info("Starting all bot services...")
            
            # Start bot manager
            await self.bot_manager.start_bots()
            
            # Start demo service
            demo_task = asyncio.create_task(self.demo_service.start_bot())
            
            # Keep track of startup time
            startup_time = datetime.now()
            self.logger.info(f"All services started at {startup_time}")
            
            return {
                "status": "success",
                "message": "All bot services started",
                "startup_time": startup_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error starting services: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to start services: {str(e)}"
            }

    async def stop_all(self):
        """Stop all bot services"""
        try:
            self.is_running = False
            
            # Stop bot manager
            await self.bot_manager.stop_bots()
            
            # Stop demo service
            self.demo_service.stop()
            
            self.logger.info("All services stopped successfully")
            return {
                "status": "success",
                "message": "All services stopped"
            }
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to stop services: {str(e)}"
            }

    def get_status(self):
        """Get status of all services"""
        try:
            bot_manager_status = self.bot_manager.get_combined_metrics()
            demo_status = self.demo_service.get_bot_status()
            
            return {
                "status": "running" if self.is_running else "stopped",
                "bot_manager": bot_manager_status,
                "demo_service": demo_status,
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get status: {str(e)}"
            }

# Standalone runner
async def run_starter():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot_starter.log')
        ]
    )
    
    starter = BotStarter()
    await starter.start_all()
    
    try:
        while True:
            await asyncio.sleep(60)  # Keep running
    except KeyboardInterrupt:
        await starter.stop_all()

if __name__ == "__main__":
    asyncio.run(run_starter())
