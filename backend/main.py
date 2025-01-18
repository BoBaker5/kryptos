from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import sys
import os
import asyncio
from pathlib import Path
import logging

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
    from kraken_crypto_bot_ai import EnhancedKrakenCryptoBot
    from demo_bot import DemoTradingBot
    print("Successfully imported trading bots")
    BOT_AVAILABLE = True
except ImportError as e:
    print(f"Error importing trading bot: {e}")
    print(f"Current directory: {os.getcwd()}")
    BOT_AVAILABLE = False
    EnhancedKrakenCryptoBot = None
    DemoTradingBot = None

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

# Store active bots and their data
active_bots = {}
demo_bot = None

async def run_demo_bot():
    global demo_bot
    try:
        logger.info("Starting demo bot...")
        while True:
            if demo_bot and demo_bot.running:
                await demo_bot.update_portfolio()
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Error in demo bot loop: {e}")

@app.on_event("startup")
async def startup_event():
    global demo_bot
    try:
        logger.info("Starting official demo bot...")
        demo_bot = DemoTradingBot()
        demo_bot.running = True
        
        # Start demo bot in background task
        asyncio.create_task(demo_bot.run())
        logger.info("Official demo bot started successfully")
    except Exception as e:
        logger.error(f"Error starting demo bot: {e}")

@app.get("/demo-status")
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
        for symbol, pos in demo_bot.position_tracker["positions"].items():
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
            "portfolio_value": demo_bot.portfolio_value,
            "daily_pnl": demo_bot.daily_pnl,
            "performance_metrics": demo_bot.performance_metrics[-100:]
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

@app.get("/bot-status/{user_id}")
async def get_bot_status(user_id: int):
    if not BOT_AVAILABLE:
        logger.warning("Bot not available")
        return {
            "status": "error",
            "message": "Trading bot not available",
            "positions": [],
            "portfolio_value": 0,
            "daily_pnl": 0
        }
        
    if user_id not in active_bots:
        logger.info("No active bot for user")
        return {
            "status": "stopped",
            "positions": [],
            "portfolio_value": 0,
            "daily_pnl": 0
        }
    
    bot = active_bots[user_id]["bot"]
    try:
        logger.info("Getting bot data...")
        # Get actual balance
        balance = bot.get_account_balance()
        logger.info(f"Account balance: {balance}")
        
        # Get positions
        positions = []
        if hasattr(bot, 'position_tracker'):
            logger.info("Getting positions...")
            for symbol, pos in bot.position_tracker.positions.items():
                logger.info(f"Position found for {symbol}: {pos}")
                current_price = bot.get_latest_price(symbol)
                if current_price:
                    pnl = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                    positions.append({
                        "symbol": symbol,
                        "quantity": pos['quantity'],
                        "entry_price": pos['entry_price'],
                        "current_price": current_price,
                        "pnl": pnl
                    })
        
        return {
            "status": "running" if getattr(bot, 'running', False) else "stopped",
            "positions": positions,
            "portfolio_value": float(balance.get('ZUSD', 0)),
            "daily_pnl": getattr(bot, 'daily_pnl', 0)
        }
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return {
            "status": "error",
            "positions": [],
            "portfolio_value": 0,
            "daily_pnl": 0
        }

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