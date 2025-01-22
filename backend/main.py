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
    allow_origins=["http://localhost:3000", "http://129.158.53.116:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        logger.info("Starting official demo bot...")
        demo_bot = DemoKrakenBot(api_key="demo", secret_key="demo")
        demo_bot.running = True
        
        # Start bot manager
        await bot_manager.start_bots()
        
        # Start demo bot in background task
        asyncio.create_task(demo_bot.run())
        logger.info("Official demo bot started successfully")
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

@app.get("/api/bot-status/{user_id}")
async def get_bot_status(user_id: int):
    """Get status for both demo and live bots"""
    try:
        demo_status = bot_manager.get_demo_bot_status()
        live_status = bot_manager.get_live_bot_status()
        return APIResponse(
            status="success",
            message="Bot status retrieved successfully",
            data={
                "demo": demo_status,
                "live": live_status,
                "running": bot_manager.running
            }
        )
    except Exception as e:
        logger.error(f"Error getting bot status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/demo-status")
async def get_demo_status():
    """Get status of the official demo bot"""
    if not demo_bot:
        return {
            "status": "stopped",
            "positions": [],
            "portfolio_value": 1000000,
            "daily_pnl": 0,
            "performance_metrics": []
        }
    
    try:
        positions = []
        if hasattr(demo_bot, 'position_tracker') and 'positions' in demo_bot.position_tracker:
            for symbol, pos in demo_bot.position_tracker['positions'].items():
                positions.append({
                    "symbol": symbol,
                    "quantity": pos['quantity'],
                    "entry_price": pos['entry_price'],
                    "current_price": pos['current_price'],
                    "pnl": ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
                })

        return {
            "status": "running",
            "positions": positions,
            "portfolio_value": getattr(demo_bot, 'portfolio_value', 1000000),
            "daily_pnl": getattr(demo_bot, 'daily_pnl', 0),
            "performance_metrics": getattr(demo_bot, 'performance_metrics', [])[-100:]
        }
    except Exception as e:
        logger.error(f"Error getting demo status: {e}")
        return {
            "status": "error",
            "positions": [],
            "portfolio_value": 1000000,
            "daily_pnl": 0,
            "performance_metrics": []
        }

@app.get("/api/live-status")
async def get_live_bot_status():
    """Get live bot status"""
    try:
        status_data = bot_manager.get_live_bot_status()
        return APIResponse(
            status="success",
            message="Live bot status retrieved successfully",
            data=status_data
        )
    except Exception as e:
        logger.error(f"Error getting live status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

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

@app.get("/api/metrics")
async def get_combined_metrics():
    """Get combined metrics from both bots"""
    try:
        metrics = bot_manager.get_combined_metrics()
        return APIResponse(
            status="success",
            message="Metrics retrieved successfully",
            data=metrics
        )
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# Health check endpoint
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
