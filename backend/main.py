from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import sys
import os
import asyncio
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TradingAPI")

# Add bot directory to Python path
BACKEND_DIR = Path(__file__).resolve().parent
BOT_DIR = BACKEND_DIR / "bot"
sys.path.append(str(BOT_DIR))

print(f"Python path: {sys.path}")
print(f"Looking for bot in: {BOT_DIR}")

try:
    from bot.kraken_crypto_bot_ai import EnhancedKrakenCryptoBot
    from bot.demo_bot import DemoKrakenBot
    from bot.bot_manager import BotManager
    print("Successfully imported trading bots")
    BOT_AVAILABLE = True
except ImportError as e:
    print(f"Error importing trading bot: {str(e)}")
    print(f"Current directory: {os.getcwd()}")
    BOT_AVAILABLE = False
    EnhancedKrakenCryptoBot = None
    DemoKrakenBot = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://6798705--kryptobot.netlify.app", "http://localhost:3000"],  # Add your Netlify domain
    allow_credentials=True,  # Changed to True to support credentials if needed
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

class KrakenCredentials(BaseModel):
    api_key: str
    secret_key: str

class APIResponse(BaseModel):
    status: str
    message: str
    data: Dict = None

# Initialize global bot instances
active_bots = {}
demo_bot = None
bot_manager = BotManager()

@app.on_event("startup")
async def startup_event():
    global demo_bot
    try:
        logger.info("Starting demo bot...")
        demo_bot = DemoKrakenBot()  # Remove api_key and secret_key
        demo_bot.running = True
        
        # Start bot manager
        await bot_manager.start_bots()
        
        # Start demo bot in background task
        asyncio.create_task(demo_bot.run())
        logger.info("Demo bot started successfully")
    except Exception as e:
        logger.error(f"Error starting demo bot: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop all bots when the application shuts down"""
    try:
        if hasattr(bot_manager, 'stop_bots'):
            await bot_manager.stop_bots()
        if demo_bot:
            demo_bot.running = False
        logger.info("All bots stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping bots: {str(e)}")

@app.get("/api/demo-status")
async def get_demo_status():
    """Get status of the demo bot"""
    try:
        if demo_bot and demo_bot.running:
            metrics = demo_bot.get_portfolio_metrics() if hasattr(demo_bot, 'get_portfolio_metrics') else {
                'current_equity': 100000.0,
                'pnl': 0,
                'pnl_percentage': 0
            }
            
            positions = demo_bot.get_demo_positions() if hasattr(demo_bot, 'get_demo_positions') else []
            
            return {
                "status": "success",
                "message": "Demo bot status retrieved successfully",
                "data": {
                    "status": "running",
                    "positions": positions,
                    "balance": getattr(demo_bot, 'demo_balance', {"ZUSD": 100000.0}),
                    "metrics": metrics,
                    "trades": getattr(demo_bot, 'trade_history', [])[-10:],
                    "performanceHistory": getattr(demo_bot, 'portfolio_history', [])[-100:]
                }
            }
        else:
            return {
                "status": "success",
                "message": "Demo bot is not running",
                "data": {
                    "status": "stopped",
                    "positions": [],
                    "balance": {"ZUSD": 100000.0},
                    "metrics": {
                        "current_equity": 100000.0,
                        "pnl": 0,
                        "pnl_percentage": 0
                    },
                    "trades": [],
                    "performanceHistory": []
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting demo status: {str(e)}")
        return {
            "status": "error",
            "message": f"Error getting demo status: {str(e)}",
            "data": {
                "status": "error",
                "positions": [],
                "balance": {"ZUSD": 100000.0},
                "metrics": {
                    "current_equity": 100000.0,
                    "pnl": 0,
                    "pnl_percentage": 0
                },
                "trades": [],
                "performanceHistory": []
            }
        }

@app.get("/api/live-status")
async def get_live_status():
    """Get live bot status"""
    try:
        return {
            "status": "success",
            "message": "Live bot status retrieved successfully",
            "data": {
                "status": "stopped",
                "positions": [],
                "balance": {},
                "metrics": {
                    "current_equity": 0,
                    "pnl": 0,
                    "pnl_percentage": 0
                },
                "lastUpdate": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error getting live status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start-bot/{user_id}")
async def start_bot(user_id: int, credentials: KrakenCredentials):
    if not BOT_AVAILABLE:
        raise HTTPException(status_code=500, detail="Trading bot not available")
        
    if user_id in active_bots:
        raise HTTPException(status_code=400, detail="Bot already running")
    
    try:
        logger.info("Creating new bot instance...")
        bot = EnhancedKrakenCryptoBot(
            api_key=credentials.api_key,
            secret_key=credentials.secret_key
        )
        logger.info("Bot instance created successfully")
        
        active_bots[user_id] = {
            "bot": bot,
            "credentials": credentials.dict()
        }
        
        # Start bot in background
        asyncio.create_task(bot.run())
        return {"status": "Bot started successfully"}
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/stop-bot/{user_id}")
async def stop_bot(user_id: int):
    if not BOT_AVAILABLE:
        raise HTTPException(status_code=500, detail="Trading bot not available")
        
    if user_id not in active_bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    try:
        bot = active_bots[user_id]["bot"]
        if hasattr(bot, 'running'):
            bot.running = False
        del active_bots[user_id]
        return {"status": "Bot stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "demo_bot": "running" if demo_bot and demo_bot.running else "stopped",
        "live_bot": "running" if bot_manager.live_running else "stopped"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
