# -*- coding: utf-8 -*-
"""The Final Complex Kraken Trading Bot
"""
import requests
from datetime import datetime, timedelta
import nest_asyncio
import threading
import pickle
import joblib
from sklearn.ensemble import RandomForestClassifier
import sqlite3
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from scipy import stats
import ta
import logging
from typing import Optional, Dict, List
import asyncio
from decimal import Decimal
import warnings
import time
import os
import krakenex
from pykrakenapi import KrakenAPI
from dotenv import load_dotenv
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
import numpy as np
from sklearn.model_selection import train_test_split
import traceback
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, GlobalAveragePooling1D
from sklearn.utils import compute_class_weight
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV

# Constants for rate limiting and cleanup
API_CALLS_PER_SECOND = 0.5  # 2 seconds between calls
CLEANUP_INTERVAL = 3600     # Cleanup every hour
DATA_RETENTION_DAYS = 7     # Keep 7 days of market data
MAX_PORTFOLIO_HISTORY = 1000  # Maximum portfolio history entries
MAX_TRADE_HISTORY = 100      # Maximum trade history entries
API_BASE_DELAY = 1.0         # Base delay between API calls
# Apply nest_asyncio at the start
nest_asyncio.apply()
warnings.filterwarnings('ignore')

class TransformerBlock(tf.keras.layers.Layer):
    def __init__(self, embed_dim=9, num_heads=3, ff_dim=36, dropout=0.1):
        super(TransformerBlock, self).__init__()
        
        self.embed_dim = embed_dim  # Set to match our input features
        self.att = tf.keras.layers.MultiHeadAttention(
            num_heads=num_heads, 
            key_dim=embed_dim,  # Match input dimension
            value_dim=embed_dim  # Match input dimension
        )
        self.ffn = tf.keras.Sequential([
            Dense(ff_dim, activation="relu"),
            Dense(embed_dim),  # Output dimension matches input
        ])
        self.layernorm1 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = tf.keras.layers.Dropout(dropout)
        self.dropout2 = tf.keras.layers.Dropout(dropout)

    def call(self, inputs, training=False):
        # Self-attention
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        
        # Feed-forward network
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)

class AITradingEnhancer:
    def __init__(self):
        self.lstm_model = None
        self.transformer_model = None
        self.feature_scaler = StandardScaler()
        self.sequence_length = 100
        self.n_features = 9 
        
    def build_lstm_model(self):
        """Build LSTM model with updated input dimensions"""
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=(self.sequence_length, 9)),  # 9 features
            Dropout(0.2),
            LSTM(64, return_sequences=False),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', 
                    loss='binary_crossentropy', 
                    metrics=['accuracy'])
        return model
        
    def build_transformer_model(self):
        """Build Transformer model with matching dimensions"""
        input_shape = (self.sequence_length, self.n_features)  # (100, 9)
        inputs = Input(shape=input_shape)
        
        # TransformerBlock with matching dimensions
        x = TransformerBlock(
            embed_dim=self.n_features,  # 9
            num_heads=3,  # Must divide embed_dim evenly
            ff_dim=36,    # 4x embed_dim
            dropout=0.1
        )(inputs)
        
        x = GlobalAveragePooling1D()(x)
        x = Dense(18, activation="relu")(x)  # 2x embed_dim
        x = Dropout(0.1)(x)
        outputs = Dense(1, activation="sigmoid")(x)
        
        model = Model(inputs=inputs, outputs=outputs)
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        return model

    def prepare_sequence_data(self, df: pd.DataFrame, sequence_length: int = 100):
        """Prepare sequential data with minimal output"""
        try:
            features = [
                'returns', 'log_returns', 'rolling_std_20', 'volume_ma_ratio',
                'rsi', 'macd', 'bb_width', 'adx', 'sma_20'
            ]
            
            missing_features = [f for f in features if f not in df.columns]
            if missing_features:
                raise ValueError(f"Missing required features: {missing_features}")
            
            X = []
            y = []
            
            for i in range(len(df) - sequence_length):
                sequence = df[features].iloc[i:i+sequence_length].values
                if np.isnan(sequence).any():
                    continue
                X.append(sequence)
                next_return = df['returns'].iloc[i+sequence_length]
                y.append(1 if next_return > 0 else 0)
            
            if not X:
                raise ValueError("No valid sequences could be created")
            
            X = np.array(X)
            y = np.array(y)
            
            X_reshaped = X.reshape(-1, X.shape[-1])
            X_scaled = self.feature_scaler.fit_transform(X_reshaped)
            X = X_scaled.reshape(X.shape)
            
            return X, y
            
        except Exception as e:
            print(f"Error preparing sequence data: {str(e)}")
            return np.array([]), np.array([])

    def predict_next_movement(self, current_data: pd.DataFrame) -> dict:
        """Combine predictions from multiple models"""
        try:
            # Prepare sequence data
            X, _ = self.prepare_sequence_data(current_data, self.sequence_length)
            if len(X) == 0:
                return {'confidence': 0.5, 'direction': 'hold'}
            
            # Get predictions from both models
            if self.lstm_model is not None and self.transformer_model is not None:
                lstm_pred = self.lstm_model.predict(X[-1:], verbose=0)[0][0]
                transformer_pred = self.transformer_model.predict(X[-1:], verbose=0)[0][0]
                
                # Combine predictions with weights
                combined_pred = (lstm_pred * 0.4 + transformer_pred * 0.6)
                
                # Convert to confidence score centered around 0.5
                confidence = 0.5 + (combined_pred - 0.5) * 0.1
                
                # Ensure confidence stays in reasonable bounds
                confidence = max(0.45, min(0.55, confidence))
                
                return {
                    'confidence': confidence,
                    'direction': 'buy' if combined_pred > 0.5 else 'sell'
                }
            
            return {'confidence': 0.5, 'direction': 'hold'}
            
        except Exception as e:
            print(f"Error in AI prediction: {str(e)}")
            return {'confidence': 0.5, 'direction': 'hold'}
        
class MLModelManager:
    def __init__(self):
        self.logger = logging.getLogger("MLModelManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        self.compute_class_weight = compute_class_weight
        self.scaler = StandardScaler()
        self.model = None
        self.feature_importance = {}
        self.is_trained = False
        self.min_samples = 100
        self._feature_names = [
            'close',
            'returns',
            'log_returns',
            'rolling_std_20',
            'rolling_std_50',
            'volume',
            'volume_ma_ratio',
            'volume_std',
            'rsi',
            'rsi_divergence',
            'mom_14',
            'mom_30',
            'macd',
            'macd_signal',
            'macd_diff',
            'bb_width',
            'bb_position',
            'sma_20',
            'sma_50',
            'sma_20_50_ratio',
            'atr',
            'adx',
            'adx_pos',
            'adx_neg'
        ]

    def get_model_features(self) -> List[str]:
        """Get list of required features in the correct order"""
        return self._feature_names.copy()

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive features ensuring all required columns exist"""
        try:
            # Verify required columns exist
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
                
            # Create copy to avoid modifying original
            df_copy = df.copy()
            
            # Ensure numeric
            for col in required_columns:
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
                
            # Remove any rows with NaN values in required columns
            df_copy = df_copy.dropna(subset=required_columns)
            
            # Now create features
            features = pd.DataFrame(index=df_copy.index)
            
            # Price-based features
            features['close'] = df_copy['close']
            features['returns'] = df_copy['close'].pct_change()
            features['log_returns'] = np.log1p(features['returns'])
            features['rolling_std_20'] = features['returns'].rolling(window=20, min_periods=1).std()
            features['rolling_std_50'] = features['returns'].rolling(window=50, min_periods=1).std()
            
            # Volume features
            features['volume'] = df_copy['volume']
            vol_ma = df_copy['volume'].rolling(window=20, min_periods=1).mean()
            features['volume_ma_ratio'] = df_copy['volume'] / vol_ma
            features['volume_std'] = df_copy['volume'].rolling(window=20, min_periods=1).std()
            
            # Technical indicators
            # RSI
            rsi = ta.momentum.RSIIndicator(close=df_copy['close'], window=14)
            features['rsi'] = rsi.rsi()
            features['rsi_divergence'] = features['rsi'].diff()
            
            # Momentum
            features['mom_14'] = ta.momentum.ROCIndicator(close=df_copy['close'], window=14).roc()
            features['mom_30'] = ta.momentum.ROCIndicator(close=df_copy['close'], window=30).roc()
            
            # MACD
            macd = ta.trend.MACD(close=df_copy['close'])
            features['macd'] = macd.macd()
            features['macd_signal'] = macd.macd_signal()
            features['macd_diff'] = macd.macd_diff()
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(close=df_copy['close'])
            features['bb_width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
            features['bb_position'] = (df_copy['close'] - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband())
            
            # Moving averages
            features['sma_20'] = df_copy['close'].rolling(window=20).mean()
            features['sma_50'] = df_copy['close'].rolling(window=50).mean()
            features['sma_20_50_ratio'] = features['sma_20'] / features['sma_50']
            
            # ATR
            features['atr'] = ta.volatility.AverageTrueRange(
                high=df_copy['high'],
                low=df_copy['low'],
                close=df_copy['close']
            ).average_true_range()
            
            # ADX
            adx = ta.trend.ADXIndicator(high=df_copy['high'], low=df_copy['low'], close=df_copy['close'])
            features['adx'] = adx.adx()
            features['adx_pos'] = adx.adx_pos()
            features['adx_neg'] = adx.adx_neg()
            
            # Clean up
            features = features.replace([np.inf, -np.inf], np.nan)
            features = features.fillna(method='ffill').fillna(method='bfill').fillna(0)
            
            return features
            
        except Exception as e:
            raise ValueError(f"Error preparing features: {str(e)}")

    def create_labels(self, df: pd.DataFrame, forward_window: int = 12) -> np.ndarray:
        """Create labels for training with proper class balance"""
        try:
            # Calculate forward returns
            short_forward = df['close'].shift(-forward_window//2) / df['close'] - 1
            long_forward = df['close'].shift(-forward_window) / df['close'] - 1
            
            # Calculate dynamic thresholds based on volatility
            volatility = df['close'].pct_change().rolling(forward_window).std()
            threshold = volatility * 1.5
            
            # Initialize labels
            labels = pd.Series(0, index=df.index)
            
            # Create binary labels (1 for bullish, 0 for bearish)
            labels[(short_forward > threshold) | (long_forward > threshold)] = 1  # Bullish
            labels[(short_forward < -threshold) | (long_forward < -threshold)] = 0  # Bearish
            
            # Remove future lookahead bias
            labels.iloc[-forward_window:] = np.nan
            
            return labels.values
            
        except Exception as e:
            raise ValueError(f"Error creating labels: {str(e)}")
    
    def get_label_distribution(self, labels: np.ndarray) -> dict:
        """Get distribution of labels with proper handling of negative values"""
        try:
            # Remove NaN values
            valid_labels = labels[~np.isnan(labels)]
            
            # Get unique values and their counts
            label_values, counts = np.unique(valid_labels, return_counts=True)
            
            # Create distribution dictionary
            distribution = {}
            for val, count in zip(label_values, counts):
                label_type = "Buy" if val == 1 else "Sell" if val == -1 else "Hold"
                distribution[label_type] = count
                
            return distribution
            
        except Exception as e:
            print(f"Error calculating label distribution: {str(e)}")
            return {}

    def prepare_training_data(self, features: pd.DataFrame, labels: np.ndarray) -> tuple:
        """Prepare data for training by handling NaN values and converting labels"""
        try:
            # Ensure features and labels have the same length
            if len(features) != len(labels):
                raise ValueError(f"Features length ({len(features)}) does not match labels length ({len(labels)})")
                
            # Remove NaN values from both features and labels
            valid_indices = ~np.isnan(labels)
            features_clean = features.loc[features.index[valid_indices]].copy()
            labels_clean = labels[valid_indices]
            
            # Convert to binary classification (1 for buy, 0 for sell/hold)
            labels_binary = (labels_clean > 0).astype(int)
            
            print(f"Features shape after cleaning: {features_clean.shape}")
            print(f"Labels shape after cleaning: {len(labels_binary)}")
            
            return features_clean, labels_binary
            
        except Exception as e:
            print(f"Error preparing training data: {str(e)}")
            return None, None

    def train_model(self, X: pd.DataFrame, y: np.ndarray):
            """Train the model with improved class balancing and calibration"""
            try:
                # Prepare data
                X_clean, y_binary = self.prepare_training_data(X, y)
                if X_clean is None or y_binary is None:
                    return False
                
                # Split data
                X_train, X_val, y_train, y_val = train_test_split(
                    X_clean, y_binary, test_size=0.2, random_state=42, stratify=y_binary
                )
                
                # Scale features
                self.scaler.fit(X_train)
                X_train_scaled = self.scaler.transform(X_train)
                X_val_scaled = self.scaler.transform(X_val)
                
                # Calculate class weights with smoothing
                class_counts = np.bincount(y_train)
                total = len(y_train)
                # Add smoothing factor to prevent extreme weights
                smoothing = 0.1
                adjusted_weights = total / (class_counts + smoothing * total)
                class_weight_dict = dict(zip(range(len(class_counts)), adjusted_weights))
                
                # Create base model with improved hyperparameters
                base_model = RandomForestClassifier(
                    n_estimators=200,
                    max_depth=12,  # Slightly deeper trees
                    min_samples_leaf=10,  # More conservative to prevent overfitting
                    min_samples_split=20,
                    class_weight=class_weight_dict,
                    random_state=42,
                    n_jobs=-1
                )
                
                # Train base model
                base_model.fit(X_train_scaled, y_train)
                
                # Use sigmoid calibration for better probability estimates
                self.model = CalibratedClassifierCV(
                    base_model, 
                    cv='prefit',
                    method='sigmoid'  # Better for imbalanced datasets
                )
                self.model.fit(X_val_scaled, y_val)
                
                # Validate calibration
                val_probs = self.model.predict_proba(X_val_scaled)
                mean_prob = np.mean(val_probs, axis=0)
                print(f"Mean predicted probabilities: {mean_prob}")
                
                # Check prediction distribution
                test_preds = self.model.predict_proba(X_val_scaled[:100])
                print("Sample prediction distribution:")
                print(pd.DataFrame(test_preds).describe())
                
                self.is_trained = True
                return True
                
            except Exception as e:
                print(f"Error in model training: {str(e)}")
                traceback.print_exc()
                return False

    def predict(self, features: pd.DataFrame) -> dict:
        """Make predictions with scaled confidence matching other indicators"""
        if not self.is_trained or self.model is None:
            return {'action': 'hold', 'confidence': 0.5}
                
        try:
            features_ordered = features[self._feature_names].copy()
            features_scaled = self.scaler.transform(features_ordered)
            
            # Get raw probabilities
            raw_probs = self.model.predict_proba(features_scaled)[-1]
            buy_prob = raw_probs[1]
            
            # Center the buy probability around 0.5
            # Transform from [0, 1] to [0.45, 0.55]
            final_confidence = 0.5 + (buy_prob - 0.5) * 0.1
            
            # Add technical confirmation adjustments
            latest = features.iloc[-1]
            adjustment = 0
            
            # RSI confirmation (small adjustment)
            if 'rsi' in latest:
                rsi = latest['rsi']
                if rsi < 30 and buy_prob > 0.5:  # Oversold + bullish signal
                    adjustment += 0.01
                elif rsi > 70 and buy_prob < 0.5:  # Overbought + bearish signal
                    adjustment -= 0.01
            
            # MACD confirmation (small adjustment)
            if 'macd' in latest and 'macd_signal' in latest:
                macd_diff = latest['macd'] - latest['macd_signal']
                if macd_diff > 0 and buy_prob > 0.5:  # Positive MACD + bullish
                    adjustment += 0.01
                elif macd_diff < 0 and buy_prob < 0.5:  # Negative MACD + bearish
                    adjustment -= 0.01
            
            # Volume confirmation (tiny adjustment)
            if 'volume_ma_ratio' in latest:
                vol_ratio = latest['volume_ma_ratio']
                if vol_ratio > 1.2:  # High volume
                    if buy_prob > 0.5:
                        adjustment += 0.005
                    else:
                        adjustment -= 0.005
            
            # Apply adjustment while maintaining bounds
            final_confidence = max(0.47, min(0.53, final_confidence + adjustment))
            
            # Determine action based on confidence
            if final_confidence > 0.52:
                action = 'buy'
            elif final_confidence < 0.47:
                action = 'sell'
            else:
                action = 'hold'
            
            self.logger.info(f"ML Prediction: raw_prob={buy_prob:.3f}, "
                            f"adj={adjustment:.3f}, "
                            f"final={final_confidence:.3f}")
                
            return {
                'action': action,
                'confidence': final_confidence
            }

        except Exception as e:
            self.logger.error(f"Error in prediction: {str(e)}")
            return {'action': 'hold', 'confidence': 0.5}

class PositionTracker:
    def __init__(self):
        self.positions = {}
        self.logger = logging.getLogger("PositionTracker")

    def update_position(self, symbol: str, quantity: float, entry_price: float):
        self.positions[symbol] = {
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'high_price': entry_price
        }

    def update_price(self, symbol: str, current_price: float):
        if symbol in self.positions:
            position = self.positions[symbol]
            if current_price > position['high_price']:
                position['high_price'] = current_price
            
            # Calculate current P&L
            entry_value = position['quantity'] * position['entry_price']
            current_value = position['quantity'] * current_price
            pnl_pct = (current_value - entry_value) / entry_value * 100
            
            return {
                'symbol': symbol,
                'quantity': position['quantity'],
                'entry_price': position['entry_price'],
                'current_price': current_price,
                'pnl_pct': pnl_pct,
                'high_price': position['high_price']
            }
        return None

class DemoRateLimiter:
    """Specialized rate limiter for demo mode that doesn't use Kraken API"""
    def __init__(self):
        self.last_price_fetch = {}
        self.cache_duration = 5  # Cache prices for 10 seconds
        self.error_count = 0
        self.backoff_time = 1.0
        self.max_backoff = 30.0  # Maximum backoff time in seconds

    def should_fetch_price(self, symbol):
        """Determine if we should fetch a new price or use cached one"""
        now = time.time()
        if symbol not in self.last_price_fetch:
            self.last_price_fetch[symbol] = {"time": now - self.cache_duration - 1, "price": None}
            return True
            
        time_since_last = now - self.last_price_fetch[symbol]["time"]
        return time_since_last > self.cache_duration
        
    def update_price(self, symbol, price):
        """Update the cached price"""
        self.last_price_fetch[symbol] = {"time": time.time(), "price": price}
        
    def get_cached_price(self, symbol):
        """Get cached price if available"""
        if symbol in self.last_price_fetch:
            return self.last_price_fetch[symbol]["price"]
        return None

    async def wait(self):
        """Add a wait method to handle rate limiting between API calls"""
        # Simple implementation - just add a small delay between operations
        await asyncio.sleep(0.5)
            
    async def handle_rate_limit_error(self, seconds_exceeded=0):
        """Handle rate limit exceeded errors with exponential backoff"""
        # Track errors
        self.error_count += 1
        
        # If we know how much we exceeded by, use that information
        if seconds_exceeded > 0:
            # Add a buffer to the exceeded time
            wait_time = seconds_exceeded + 1.0
        else:
            # Exponential backoff with cap
            self.backoff_time = min(self.max_backoff, self.backoff_time * 2)
            wait_time = self.backoff_time
        
        # Log the backoff
        logging.info(f"Rate limit exceeded, backing off for {wait_time:.2f} seconds (error #{self.error_count})")
        
        # Wait the required time
        await asyncio.sleep(wait_time)
        
    def reset_backoff(self):
        """Reset backoff after successful operations"""
        if self.error_count > 0:
            logging.info(f"Resetting rate limiter after {self.error_count} errors")
        self.backoff_time = 1.0
        self.error_count = 0
        
class DemoKrakenBot:
    def __init__(self):
        """Initialize the demo trading bot"""
        # Initialize logging first
        self.logger = self._setup_logging()
        self.db_name = 'crypto_trading.db'
        
        try:
            # Initialize API and rate limiting
            self.timeframe = 5  # 5-minute intervals
            self.last_api_call = time.time()
            self.api_retry_delay = 1.0
            self.max_retry_delay = 60
            # Initialize the demo rate limiter
            self.demo_rate_limiter = DemoRateLimiter()
            
            # Add randomness for jitter in rate limiting
            import random
            self.random = random
            
            # Initialize Kraken API - Direct connection to ensure fresh data
            self.kraken = krakenex.API()
            self.k = KrakenAPI(self.kraken, retry=0.5)
            self.running = True
            
            # Initialize components
            self.position_tracker = PositionTracker()
            self.init_database()
            
            # Initialize ML and AI components
            self.model_manager = MLModelManager()
            self.ai_enhancer = AITradingEnhancer()
            
            # Training state
            self.is_initially_trained = False
            self.training_completed = False
            self.min_training_data = 100
            self.initial_training_hours = 1
            self.start_time = datetime.now()
            
            # Account state
            self.demo_balance = {'ZUSD': 100000.0}
            self.demo_positions = {}
            self.trade_history = []
            self.portfolio_history = [{
                'timestamp': datetime.now(),
                'balance': 100000.0,
                'equity': 100000.0
            }]
        
            # Trading pairs and allocations
            self.symbols = {
                "SOLUSD": 0.20,
                "AVAXUSD": 0.20,
                "XRPUSD": 0.20,
                "XDGUSD": 0.15,
                "SHIBUSD": 0.10,
                "PEPEUSD": 0.15
            }
                
            # Risk parameters
            self.max_drawdown = 0.50
            self.trailing_stop_pct = 0.012
            self.max_trades_per_hour = 2
            self.trade_cooldown = 600
            self.last_trade_time = {}
            self.max_position_size = 0.15
            self.min_position_value = 10.0
            self.max_total_risk = 0.10
            self.stop_loss_pct = 0.008
            self.take_profit_pct = 0.025
            self.min_zusd_balance = 5.0
            
            # Technical parameters
            self.sma_short = 20
            self.sma_long = 50
            self.rsi_period = 14
            self.rsi_oversold = 35
            self.rsi_overbought = 65
            self.macd_fast = 12
            self.macd_slow = 26
            self.macd_signal = 9
            self.volatility_window = 20
            self.volume_ma_window = 20
            self.prediction_threshold = 0.2
            
            # Market conditions
            self.market_conditions = {
                'high_volatility': 0.05,
                'low_liquidity': 1000,
                'excessive_spread': 0.03
            }
            
            # Performance tracking
            self.performance_metrics = {}
            
            # API call tracking and rate limiting
            self.api_calls = {
                'total': 0,
                'rate_limited': 0,
                'errors': 0,
                'last_hour': {
                    'count': 0,
                    'timestamp': datetime.now()
                }
            }
            
            # Reset API call statistics hourly
            self.api_call_reset_task = asyncio.create_task(self._reset_api_call_stats_periodically())
            
            # Load saved state
            self.load_demo_state()
            
            # Initialize with a higher minimum balance to avoid warnings
            if self.demo_balance['ZUSD'] < self.min_zusd_balance:
                self.demo_balance['ZUSD'] = 10000.0
                self.logger.info(f"Initial balance too low, reset to ${self.demo_balance['ZUSD']}")
            
            self.logger.info("Demo bot initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            raise
    
    async def _reset_api_call_stats_periodically(self):
        """Reset API call statistics every hour"""
        try:
            while self.running:
                await asyncio.sleep(3600)  # 1 hour
                current_time = datetime.now()
                
                # Log and reset stats
                hourly_calls = self.api_calls['last_hour']['count']
                self.logger.info(f"API calls in last hour: {hourly_calls}")
                
                # Reset hourly count
                self.api_calls['last_hour'] = {
                    'count': 0,
                    'timestamp': current_time
                }
        except Exception as e:
            self.logger.error(f"Error in API stats reset task: {str(e)}")

    def load_key(self, api_key: str, secret_key: str):
        """Load API credentials for demo bot"""
        try:
            self.kraken.load_key(api_key, secret_key)
            self.logger.info("Demo credentials loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading demo credentials: {str(e)}")
            raise
    
    def get_demo_balance(self):
        """Get current demo account balance"""
        try:
            # Calculate total value of positions
            position_value = 0
            for symbol, position in self.demo_positions.items():
                current_price = self.get_latest_price(symbol)
                if current_price:
                    position_value += position['volume'] * current_price
        
            # Calculate total equity
            total_equity = self.demo_balance['ZUSD'] + position_value
        
            balance_info = pd.Series(self.demo_balance)
            
            # Log balance info
            self.logger.info("\n=== Demo Account Balance ===")
            self.logger.info(f"USD Balance: ${self.demo_balance['ZUSD']:.2f}")
            self.logger.info(f"Position Value: ${position_value:.2f}")
            self.logger.info(f"Total Equity: ${total_equity:.2f}")
            
            for currency, amount in self.demo_balance.items():
                if currency != 'ZUSD' and amount > 0:
                    self.logger.info(f"{currency}: {amount:.8f}")
        
            return balance_info
        
        except Exception as e:
            self.logger.error(f"Error getting demo balance: {str(e)}")
            return pd.Series(self.demo_balance)
    
    def get_demo_positions(self):
        """Get current demo positions"""
        try:
            formatted_positions = []
            for symbol, pos in self.demo_positions.items():
                current_price = self.get_latest_price(symbol)
                if current_price:
                    entry_price = pos['entry_price']
                    volume = pos['volume']
                    pnl = (current_price - entry_price) * volume
                    pnl_percentage = ((current_price - entry_price) / entry_price) * 100
        
                    formatted_pos = {
                        "symbol": symbol,
                        "quantity": str(volume),
                        "entry_price": str(entry_price),
                        "current_price": str(current_price),
                        "pnl": str(pnl),
                        "pnl_percentage": str(pnl_percentage),
                        "entry_time": pos['entry_time'].isoformat()
                    }
                    formatted_positions.append(formatted_pos)
        
            # Log positions
            if formatted_positions:
                self.logger.info("\n=== Demo Positions ===")
                for pos in formatted_positions:
                    self.logger.info(f"{pos['symbol']}: {float(pos['quantity']):.8f} @ ${float(pos['current_price']):.8f}")
                    self.logger.info(f"P&L: ${float(pos['pnl']):.2f} ({float(pos['pnl_percentage']):.2f}%)")
        
            return formatted_positions
        
        except Exception as e:
            self.logger.error(f"Error getting demo positions: {str(e)}")
            return []

    async def get_demo_trade_history(self):
        """Get demo bot trade history"""
        try:
            if self.demo_bot and hasattr(self.demo_bot, 'trade_history'):
                # Format trade history for API response
                formatted_trades = []
                for trade in self.demo_bot.trade_history:
                    # Skip any system trades if needed
                    if trade.get('symbol') == 'SYSTEM':
                        continue
                        
                    # Format the trade record
                    formatted_trade = {
                        'timestamp': trade['timestamp'].isoformat() if isinstance(trade['timestamp'], datetime) else trade['timestamp'],
                        'symbol': trade['symbol'],
                        'type': trade['type'],
                        'price': float(trade['price']),
                        'quantity': float(trade['quantity']),
                        'value': float(trade['value']),
                        'profit_loss': float(trade.get('profit_loss', 0)),
                        'pnl_percentage': float(trade.get('pnl_percentage', 0)),
                        'entry_price': float(trade.get('entry_price', 0)) if 'entry_price' in trade else 0
                    }
                    formatted_trades.append(formatted_trade)
                    
                return formatted_trades
            return []
        except Exception as e:
            self.logger.error(f"Error getting demo trade history: {str(e)}")
            return []
    
    def cleanup_old_data(self):
        """Cleanup old data to manage memory usage"""
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
        
            # Keep only last 7 days of market data
            c.execute('''DELETE FROM market_data 
                        WHERE timestamp < date('now', '-7 days')''')
        
            # Keep only last 1000 portfolio history entries
            if len(self.portfolio_history) > 1000:
                self.portfolio_history = self.portfolio_history[-1000:]
                
            # Keep only last 100 trades
            if len(self.trade_history) > 100:
                self.trade_history = self.trade_history[-100:]
        
            # Update database with cleaned data
            c.execute('DELETE FROM demo_portfolio_history')
            for entry in self.portfolio_history:
                c.execute('INSERT INTO demo_portfolio_history VALUES (?, ?, ?)',
                         (entry['timestamp'].isoformat(), entry['balance'],
                          entry['equity']))
        
            c.execute('DELETE FROM demo_trade_history')
            for trade in self.trade_history:
                c.execute('''INSERT INTO demo_trade_history 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (trade['timestamp'].isoformat(), trade['symbol'],
                          trade['type'], trade['price'], trade['quantity'],
                          trade['value'], trade['balance_after']))
        
            # Commit changes and close connection
            conn.commit()
            conn.close()
        
            # Force garbage collection
            import gc
            gc.collect()
                
            self.logger.info("Memory cleanup completed successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    async def wait_for_api(self, exceeded_by=0):
        """Improved rate limiting with adaptive delays"""
        try:
            current_time = time.time()
            time_since_last_call = current_time - self.last_api_call
            
            # Base delay
            base_delay = 1.0
            
            # Add additional delay if rate limit was exceeded
            if exceeded_by > 0:
                self.api_retry_delay = min(self.api_retry_delay * 1.5, self.max_retry_delay)
                await asyncio.sleep(self.api_retry_delay)
            else:
                # Gradually reduce delay if not exceeded
                self.api_retry_delay = max(1.0, self.api_retry_delay * 0.9)
            
            # Add jitter to prevent synchronized calls
            jitter = random.uniform(0.1, 0.5)
            
            # Ensure minimum spacing between calls
            if time_since_last_call < base_delay:
                await asyncio.sleep(base_delay - time_since_last_call + jitter)  # Add jitter
            
            self.last_api_call = time.time()
            
        except Exception as e:
            self.logger.error(f"Error in API rate limiting: {str(e)}")
            await asyncio.sleep(1.0)  # Safe default delay
    
    def calculate_total_equity(self):
        """Calculate total portfolio value including positions"""
        try:
            equity = self.demo_balance['ZUSD']
            
            for symbol, position in self.demo_positions.items():
                current_price = self.get_latest_price(symbol)
                if current_price:
                    position_value = position['volume'] * current_price
                    equity += position_value
            
            return equity
        
        except Exception as e:
            self.logger.error(f"Error calculating total equity: {str(e)}")
            return self.demo_balance['ZUSD']
    
    def get_portfolio_metrics(self):
        """Get current portfolio performance metrics"""
        try:
            current_equity = self.calculate_total_equity()
            initial_balance = 100000.0
            
            metrics = {
                'current_equity': current_equity,
                'initial_balance': initial_balance,
                'total_pnl': current_equity - initial_balance,
                'pnl_percentage': ((current_equity - initial_balance) / initial_balance) * 100,
                'positions': self.demo_positions,
                'balance': self.demo_balance,
                'trade_history': self.trade_history[-10:],  # Last 10 trades
                'portfolio_history': self.portfolio_history[-100:]  # Last 100 data points
            }
        
            # Log metrics
            self.logger.info("\n=== Portfolio Metrics ===")
            self.logger.info(f"Current Equity: ${metrics['current_equity']:.2f}")
            self.logger.info(f"Total P&L: ${metrics['total_pnl']:.2f} ({metrics['pnl_percentage']:.2f}%)")
            
            return metrics
        
        except Exception as e:
            self.logger.error(f"Error getting portfolio metrics: {str(e)}")
            return {
                'current_equity': self.demo_balance['ZUSD'],
                'initial_balance': 100000.0,
                'total_pnl': 0,
                'pnl_percentage': 0,
                'positions': {},
                'balance': self.demo_balance,
                'trade_history': [],
                'portfolio_history': []
            }
            
    async def wait_for_api(self, exceeded_by=0):
        """Improved rate limiting with adaptive delays"""
        try:
            current_time = time.time()
            time_since_last_call = current_time - self.last_api_call
            
            # Base delay
            base_delay = 1.0
            
            # Add additional delay if rate limit was exceeded
            if exceeded_by > 0:
                self.api_retry_delay = min(self.api_retry_delay * 1.5, self.max_retry_delay)
                await asyncio.sleep(self.api_retry_delay)
            else:
                # Gradually reduce delay if not exceeded
                self.api_retry_delay = max(1.0, self.api_retry_delay * 0.9)
            
            # Ensure minimum spacing between calls
            if time_since_last_call < base_delay:
                await asyncio.sleep(base_delay - time_since_last_call + 0.1)  # Add small buffer
            
            self.last_api_call = time.time()
            
        except Exception as e:
            self.logger.error(f"Error in API rate limiting: {str(e)}")
            await asyncio.sleep(1.0)  # Safe default delay
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration for console output"""
        logger = logging.getLogger("KrakenCryptoBot")
        
        if logger.handlers:
            logger.handlers.clear()
            
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        return logger
    
    def get_formatted_price(self, price: float, symbol: str) -> str:
        try:
            if price == 0 or price is None:
                price = self.get_latest_price(symbol)
                if price == 0 or price is None:
                    return "0.00"
                    
            decimals = {
                'SOLUSD': 4,
                'AVAXUSD': 4,
                'XRPUSD': 4,
                'XDGUSD': 4,
                'SHIBUSD': 10,
                'PEPEUSD': 10
            }
            
            decimal_places = decimals.get(symbol, 10)
            return f"{float(price):.{decimal_places}f}"
            
        except Exception as e:
            self.logger.error(f"Error formatting price for {symbol}: {str(e)}")
            return str(price)
    
    async def get_historical_data(self, symbol: str, lookback_days: int = 7) -> pd.DataFrame:
        """Fetch and preprocess historical data with proper rate limiting"""
        try:
            # Wait for rate limiter before making API call
            await self.wait_for_api()
            
            try:
                since = time.time() - (lookback_days * 24 * 60 * 60)
                ohlc, last = self.k.get_ohlc_data(symbol, interval=self.timeframe, since=since)
                
                # On success, reduce the retry delay gradually
                self.api_retry_delay = max(1.0, self.api_retry_delay * 0.9)
                
                if ohlc is not None and not ohlc.empty:
                    # Convert all numeric columns to float
                    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                    for col in numeric_columns:
                        if col in ohlc.columns:
                            ohlc[col] = pd.to_numeric(ohlc[col], errors='coerce')
                    
                    # Remove any rows with NaN values in critical columns
                    ohlc = ohlc.dropna(subset=['close', 'volume'])
                    
                    # Ensure positive values
                    ohlc = ohlc[ohlc['close'] > 0]
                    ohlc = ohlc[ohlc['volume'] > 0]
                    
                    self.logger.info(f"Successfully fetched {len(ohlc)} rows of data for {symbol}")
                    return ohlc
                    
                self.logger.warning(f"No historical data returned for {symbol}")
                return pd.DataFrame()
                
            except Exception as e:
                error_str = str(e)
                if "public call frequency exceeded" in error_str:
                    # Extract the exceeded time if available
                    import re
                    seconds_match = re.search(r'seconds=(\d+\.\d+)', error_str)
                    seconds_exceeded = float(seconds_match.group(1)) if seconds_match else 0
                    
                    # Apply an exponential backoff
                    self.api_retry_delay = min(self.max_retry_delay, self.api_retry_delay * 2)
                    backoff_time = self.api_retry_delay + seconds_exceeded
                    
                    self.logger.warning(f"Rate limit exceeded, backing off for {backoff_time:.2f} seconds")
                    await asyncio.sleep(backoff_time)
                    
                    # Retry recursively after backoff
                    return await self.get_historical_data(symbol, lookback_days)
                else:
                    # For other exceptions, re-raise to be caught by the outer try/except
                    raise
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def analyze_market_state(self, df: pd.DataFrame) -> dict:
        """Analyze current market state"""
        try:
            if len(df) < self.sma_long:
                return None
        
            # Calculate indicators first
            df = self.calculate_indicators(df)
            
            latest = df.iloc[-1]
        
            # Now we can safely check sma_long since it's calculated
            if 'sma_long' not in df.columns:
                self.logger.warning("SMA long not found in dataframe")
                return None
        
            # Trend analysis
            trend = 1 if latest['close'] > latest['sma_long'] else -1
        
            # Volatility analysis
            current_volatility = latest['volatility'] if 'volatility' in df.columns else df['close'].pct_change().rolling(20).std().iloc[-1]
        
            # Volume analysis
            volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
            volume_trend = 1 if latest['volume'] > volume_sma else -1
        
            return {
                'trend': trend,
                'volatility': current_volatility,
                'volume_trend': volume_trend
            }
        
        except Exception as e:
            self.logger.error(f"Error in market state analysis: {str(e)}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators ensuring all required indicators exist"""
        try:
            df = df.copy()
            
            # Basic price features
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log1p(df['returns'])
            df['rolling_std_20'] = df['returns'].rolling(window=20, min_periods=1).std()
            
            # Moving averages (ensure these are calculated first)
            df['sma_short'] = df['close'].rolling(window=self.sma_short, min_periods=1).mean()
            df['sma_long'] = df['close'].rolling(window=self.sma_long, min_periods=1).mean()
            df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
            df['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
            
            # Volume features
            vol_ma = df['volume'].rolling(window=20, min_periods=1).mean()
            df['volume_ma_ratio'] = df['volume'] / vol_ma
            
            # RSI
            rsi_indicator = ta.momentum.RSIIndicator(close=df['close'], window=14)
            df['rsi'] = rsi_indicator.rsi()
            
            # MACD
            macd_indicator = ta.trend.MACD(close=df['close'])
            df['macd'] = macd_indicator.macd()
            df['macd_signal'] = macd_indicator.macd_signal()
            df['macd_diff'] = macd_indicator.macd_diff()
            
            # Bollinger Bands
            bb_indicator = ta.volatility.BollingerBands(close=df['close'])
            df['bb_width'] = (bb_indicator.bollinger_hband() - bb_indicator.bollinger_lband()) / bb_indicator.bollinger_mavg()
            
            # ADX
            adx_indicator = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'])
            df['adx'] = adx_indicator.adx()
            
            # Additional features for ML model
            df['rolling_std_50'] = df['returns'].rolling(window=50, min_periods=1).std()
            df['volume_std'] = df['volume'].rolling(window=20, min_periods=1).std()
            df['rsi_divergence'] = df['rsi'].diff()
            df['mom_14'] = ta.momentum.ROCIndicator(close=df['close'], window=14).roc()
            df['mom_30'] = ta.momentum.ROCIndicator(close=df['close'], window=30).roc()
            df['adx_pos'] = adx_indicator.adx_pos()
            df['adx_neg'] = adx_indicator.adx_neg()
            
            # Clean up
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error calculating indicators: {str(e)}")
    
    def calculate_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced technical indicators with proper error handling"""
        try:
            # Create a copy to avoid modifying the original
            df = df.copy()
            
            # Ensure we have required columns and they're numeric
            required_columns = ['high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove any rows with NaN values in required columns
            df = df.dropna(subset=required_columns)
            
            # Calculate SMAs first
            df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
            df['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
            df['sma_20_50_ratio'] = df['sma_20'] / df['sma_50']
            
            # Price-based features with error handling
            df['returns'] = df['close'].pct_change().fillna(0)
            df['log_returns'] = np.log1p(df['returns'])
            df['rolling_std_20'] = df['returns'].rolling(window=20, min_periods=1).std()
            df['rolling_std_50'] = df['returns'].rolling(window=50, min_periods=1).std()
            
            # Volume features
            df['volume_sma'] = df['volume'].rolling(window=20, min_periods=1).mean()
            df['volume_ma_ratio'] = df['volume'] / df['volume_sma'].replace(0, np.nan)
            df['volume_std'] = df['volume'].rolling(window=20, min_periods=1).std()
            
            try:
                # RSI with error handling
                rsi_indicator = ta.momentum.RSIIndicator(close=df['close'].replace(0, np.nan), window=14)
                df['rsi'] = rsi_indicator.rsi()
                df['rsi_divergence'] = df['rsi'].diff()
                
                # Momentum
                df['mom_14'] = ta.momentum.ROCIndicator(close=df['close'], window=14).roc()
                df['mom_30'] = ta.momentum.ROCIndicator(close=df['close'], window=30).roc()
                
                # MACD
                macd_indicator = ta.trend.MACD(
                    close=df['close'],
                    window_fast=self.macd_fast,
                    window_slow=self.macd_slow,
                    window_sign=self.macd_signal
                )
                df['macd'] = macd_indicator.macd()
                df['macd_signal'] = macd_indicator.macd_signal()
                df['macd_diff'] = macd_indicator.macd_diff()
                
                # Bollinger Bands with error handling
                bb_indicator = ta.volatility.BollingerBands(close=df['close'])
                bb_high = bb_indicator.bollinger_hband()
                bb_low = bb_indicator.bollinger_lband()
                bb_mid = bb_indicator.bollinger_mavg()
                
                # Safely calculate BB metrics
                df['bb_width'] = (bb_high - bb_low) / bb_mid.replace(0, np.nan)
                df['bb_position'] = (df['close'] - bb_low) / (bb_high - bb_low).replace(0, np.nan)
                
                # ATR and ADX with error handling
                df['atr'] = ta.volatility.AverageTrueRange(
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    window=14
                ).average_true_range()
                
                adx_indicator = ta.trend.ADXIndicator(
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    window=14
                )
                df['adx'] = adx_indicator.adx()
                df['adx_pos'] = adx_indicator.adx_pos()
                df['adx_neg'] = adx_indicator.adx_neg()
                
            except Exception as e:
                self.logger.error(f"Error calculating technical indicators: {str(e)}")
                raise
            
            # Final cleanup
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
            
            # Verify all required features are present and non-null
            for col in df.columns:
                if df[col].isnull().any():
                    self.logger.warning(f"Column {col} contains null values after processing")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating advanced indicators: {str(e)}")
            raise
        
    def analyze_market_state(self, df: pd.DataFrame) -> dict:
        """Analyze current market state with proper error handling"""
        try:
            if len(df) < self.sma_long:
                return {
                    'trend': 0,
                    'volatility': 0,
                    'volume_trend': 0
                }
        
            latest = df.iloc[-1]
            
            # Ensure we have necessary columns
            required_columns = ['sma_short', 'sma_long', 'volume']
            if not all(col in df.columns for col in required_columns):
                self.logger.warning(f"Missing required columns for market analysis: {[col for col in required_columns if col not in df.columns]}")
                return {
                    'trend': 0,
                    'volatility': 0,
                    'volume_trend': 0
                }
        
            # Trend analysis
            trend = 1 if latest['sma_short'] > latest['sma_long'] else -1
        
            # Volatility analysis
            volatility = df['returns'].rolling(window=20).std().iloc[-1]
        
            # Volume analysis
            volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
            volume_trend = 1 if latest['volume'] > volume_sma else -1
        
            return {
                'trend': trend,
                'volatility': volatility,
                'volume_trend': volume_trend
            }
        
        except Exception as e:
            self.logger.error(f"Error in market state analysis: {str(e)}")
            return {
                'trend': 0,
                'volatility': 0,
                'volume_trend': 0
            }
        
    def _check_divergence(self, price: pd.Series, indicator: pd.Series, window: int = 10) -> int:
        """Check for price-indicator divergence"""
        try:
            price_change = price.diff(window).iloc[-1]
            indicator_change = indicator.diff(window).iloc[-1]
        
            if price_change > 0 and indicator_change < 0:
                return -1  # Bearish divergence
            elif price_change < 0 and indicator_change > 0:
                return 1  # Bullish divergence
            return 0
        except:
            return 0

    def detect_market_cycle(self, df):
        """Detect current market cycle with greater sensitivity to avoid risky markets"""
        if len(df) < 50:
            return "unknown"
            
        # Calculate key metrics
        # Price momentum - Look at multiple timeframes
        momentum_short = df['close'].pct_change(5).iloc[-1]  # 5-period momentum
        momentum_medium = df['close'].pct_change(20).iloc[-1]  # 20-period momentum
        
        # Volatility with more accurate measurement
        volatility = df['close'].pct_change().rolling(20).std().iloc[-1]
        
        # Volume trend with multiple timeframes
        volume_trend_short = df['volume'].rolling(5).mean().iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
        volume_trend_medium = df['volume'].rolling(10).mean().iloc[-1] / df['volume'].rolling(30).mean().iloc[-1]
        
        # Moving average relationships
        ma_cross = df['sma_20'].iloc[-1] / df['sma_50'].iloc[-1]
        
        # Check for price breakouts
        recent_high = df['high'].rolling(20).max().iloc[-1]
        recent_low = df['low'].rolling(20).min().iloc[-1]
        price_range = recent_high - recent_low
        breakout_threshold = price_range * 0.03  # 3% of the range
        
        # Determine market cycle with stricter criteria
        if (momentum_short > 0.01 and momentum_medium > 0.03 and 
            ma_cross > 1.01 and volume_trend_short > 1.1 and
            df['close'].iloc[-1] > df['sma_50'].iloc[-1] and
            volatility < 0.025):
            return "bull_trend"  # Strong bullish trend
            
        elif (momentum_short < -0.01 and momentum_medium < -0.03 and
              ma_cross < 0.99 and volume_trend_short > 1.1 and
              df['close'].iloc[-1] < df['sma_50'].iloc[-1]):
            return "bear_trend"  # Strong bearish trend
            
        elif volatility > 0.03:  # Reduced threshold to catch more volatile markets
            return "high_volatility"  # Choppy/volatile market
            
        elif (abs(momentum_medium) < 0.015 and volatility < 0.02 and
              abs(ma_cross - 1.0) < 0.01):
            # Check if price is near support in ranging market
            if df['close'].iloc[-1] < df['sma_20'].iloc[-1] and df['close'].iloc[-1] > df['sma_50'].iloc[-1]:
                return "ranging_support"  # Ranging near support - potential buy
            else:
                return "ranging"  # Regular ranging - less ideal for new entries
                
        elif df['close'].iloc[-1] > recent_high - breakout_threshold and volume_trend_short > 1.2:
            return "breakout"  # Potential breakout with volume confirmation
            
        else:
            return "mixed"  # Mixed or unclear market conditions
    
    def generate_enhanced_signals(self, df: pd.DataFrame, symbol: str) -> dict:
        """Generate highly selective trading signals optimized per coin"""
        try:
            if len(df) < self.sma_long:
                return {'action': 'hold', 'confidence': 0.5}
    
            df = self.calculate_advanced_indicators(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # COIN-SPECIFIC VOLUME THRESHOLDS - FURTHER REDUCED
            volume_thresholds = {
                'SOLUSD': 0.5,    # More liquid coin, higher threshold
                'AVAXUSD': 0.5,   # More liquid coin, higher threshold
                'XRPUSD': 0.3,    # Medium liquidity, medium threshold
                'XDGUSD': 0.1,    # Lower liquidity, lower threshold
                'SHIBUSD': 0.01,  # Ultra-low threshold for SHIB
                'PEPEUSD': 0.01   # Ultra-low threshold for PEPE
            }
            
            # Default threshold if symbol not found
            default_threshold = 0.3
            
            # Get appropriate threshold for this symbol
            volume_threshold = volume_thresholds.get(symbol, default_threshold)
            
            # VOLUME FILTER - Use the coin-specific threshold
            volume_ratio = latest['volume_ma_ratio'] 
            if volume_ratio < volume_threshold:
                self.logger.info(f"Insufficient volume ({volume_ratio:.2f}) for {symbol}, threshold: {volume_threshold}, avoiding trade")
                return {'action': 'hold', 'confidence': 0.5}
            
            # Key indicators
            sma20 = latest['sma_20']
            sma50 = latest['sma_50']
            trend = 1 if sma20 > sma50 else -1
            rsi = latest['rsi']
            macd = latest['macd']
            macd_signal = latest['macd_signal']
            current_price = latest['close']
            bb_position = latest['bb_position'] if 'bb_position' in latest else 0
            if pd.isna(bb_position):
                bb_position = 0
            
            # Market cycle detection - ONLY trade in favorable market conditions
            market_cycle = self.detect_market_cycle(df)
            self.logger.info(f"Detected market cycle for {symbol}: {market_cycle}")
            
            # EXPANDED FAVORABLE MARKETS - Allow more market conditions
            favorable_markets = {
                'SOLUSD': ["bull_trend", "ranging", "breakout", "ranging_support", "low_volatility", "mixed"],
                'AVAXUSD': ["bull_trend", "ranging", "breakout", "ranging_support", "low_volatility", "mixed"],
                'XRPUSD': ["bull_trend", "ranging", "ranging_support", "breakout", "low_volatility"], 
                'XDGUSD': ["bull_trend", "breakout", "ranging_support"],
                'SHIBUSD': ["bull_trend", "breakout"],
                'PEPEUSD': ["bull_trend", "breakout"]
            }
            
            # Get favorable markets for this coin
            allowed_markets = favorable_markets.get(symbol, ["bull_trend"])
            
            # MARKET CONDITION FILTER - Only trade in coin-specific favorable markets
            if market_cycle not in allowed_markets:
                self.logger.info(f"Avoiding trades for {symbol} in {market_cycle} market")
                return {'action': 'hold', 'confidence': 0.5}
            
            # Build confirmation chain system
            confirmations = 0
            max_confirmations = 6
            
            # Price above BOTH key MAs
            if current_price > sma20 and current_price > sma50:
                confirmations += 1
                self.logger.info("✓ Price above key moving averages")
            
            # RSI in ideal range (not overbought) - RELAXED CRITERIA
            if rsi > 40 and rsi < 65:  # Wider range (40-65 instead of 45-60)
                confirmations += 1
                self.logger.info("✓ RSI in ideal range")
            
            # Volume confirmation - RELAXED CRITERIA
            if volume_ratio > volume_threshold:  # Just above threshold is sufficient
                confirmations += 1
                self.logger.info("✓ Sufficient volume confirmation")
            
            # MACD confirmation - RELAXED CRITERIA
            if macd > macd_signal:  # Just need to be above signal line
                confirmations += 1
                self.logger.info("✓ MACD bullish")
            
            # Trend confirmation
            if trend > 0:
                confirmations += 1
                self.logger.info("✓ Bullish trend confirmed")
            
            # BB position not overextended - RELAXED CRITERIA
            if bb_position > -0.4 and bb_position < 0.4:  # Wider range (-0.4/0.4 instead of -0.3/0.3)
                confirmations += 1
                self.logger.info("✓ Price within reasonable Bollinger Band range")
            
            # Initialize confidence at neutral
            confidence = 0.5
            
            # COIN-SPECIFIC REQUIRED CONFIRMATIONS - REDUCED
            required_confirmations = {
                'SOLUSD': 4,      # Lower risk, require 4/6 confirmations
                'AVAXUSD': 4,     # Lower risk, require 4/6 confirmations
                'XRPUSD': 4,      # Medium risk, require 4/6 confirmations
                'XDGUSD': 5,      # Higher risk, require 5/6 confirmations
                'SHIBUSD': 5,     # Very high risk, require 5/6 confirmations
                'PEPEUSD': 5      # Extremely high risk, require 5/6 confirmations
            }
            
            default_required_confirmations = 5  # Default to requiring 5 confirmations
            min_confirmations_needed = required_confirmations.get(symbol, default_required_confirmations)
            
            # EXTREMELY SELECTIVE BUY - Require coin-specific confirmation count
            if (confirmations >= min_confirmations_needed and trend > 0):  # Simplified condition
                # Coin-specific confidence boost
                confidence_boost = {
                    'SOLUSD': 0.17,    # Higher confidence in SOL
                    'AVAXUSD': 0.17,   # Higher confidence in AVAX
                    'XRPUSD': 0.16,    # Medium confidence in XRP
                    'XDGUSD': 0.15,    # Lower confidence in DOGE
                    'SHIBUSD': 0.14,   # Lower confidence in SHIB
                    'PEPEUSD': 0.14    # Lower confidence in PEPE
                }
                
                default_boost = 0.15
                boost = confidence_boost.get(symbol, default_boost)
                
                confidence = 0.5 + boost  # Coin-specific confidence boost
                self.logger.info(f"BUY SIGNAL: {confirmations}/{max_confirmations} confirmations")
                
            # MORE AGGRESSIVE PROFIT TAKING (SELL)
            elif (
                (trend < 0 and macd < macd_signal) or  # Trend and MACD turning negative
                (rsi > 70) or  # RSI getting overbought
                (bb_position > 0.8)  # Price near upper Bollinger Band
            ):
                confidence = 0.35  # Strong sell
                self.logger.info(f"PROFIT TAKING SIGNAL")
            
            # Ensure confidence stays within bounds
            confidence = max(0.3, min(0.7, confidence))
            
            # COIN-SPECIFIC BUY THRESHOLD - LOWERED
            buy_thresholds = {
                'SOLUSD': 0.62,    # Lower risk, lower threshold
                'AVAXUSD': 0.62,   # Lower risk, lower threshold
                'XRPUSD': 0.63,    # Medium risk, medium threshold
                'XDGUSD': 0.64,    # Higher risk, higher threshold
                'SHIBUSD': 0.65,   # Very high risk, very high threshold
                'PEPEUSD': 0.65    # Extremely high risk, very high threshold
            }
            
            default_buy_threshold = 0.64
            buy_threshold = buy_thresholds.get(symbol, default_buy_threshold)
            
            # MUCH MORE SELECTIVE BUY THRESHOLD - Require extremely high confidence
            if confidence > buy_threshold:
                action = 'buy'
            elif confidence < 0.42:  # Eager to take profits (changed from 0.45 to 0.42)
                action = 'sell'
            else:
                action = 'hold'
    
            # FINAL SAFETY CHECKS:
            # 1. Don't buy without enough confirmations
            if action == 'buy' and confirmations < min_confirmations_needed:
                action = 'hold'
                self.logger.info(f"Buy rejected: Only {confirmations}/{min_confirmations_needed} confirmations")
            
            # 2. RSI filter for buys - RELAXED
            if action == 'buy' and rsi > 70:  # Only reject extremely overbought
                action = 'hold'
                self.logger.info(f"Buy rejected: RSI too high at {rsi:.2f}")
            
            # 3. Check if price is trending up in last few candles - REMOVED
            # This check was too strict and was rejecting good entries
    
            # Log final decision
            self.logger.info(f"{symbol} Analysis:")
            self.logger.info(f"Market Cycle: {market_cycle}")
            self.logger.info(f"Confirmations: {confirmations}/{max_confirmations}")
            self.logger.info(f"Required Confirmations: {min_confirmations_needed}")
            self.logger.info(f"Trend: {'Bullish' if trend > 0 else 'Bearish'}")
            self.logger.info(f"RSI: {rsi:.2f}")
            self.logger.info(f"Volume Ratio: {volume_ratio:.2f} (Threshold: {volume_threshold})")
            self.logger.info(f"MACD: {macd:.6f}, Signal: {macd_signal:.6f}")
            self.logger.info(f"Final Signal: {action.upper()} ({confidence:.3f})")
            
            return {'action': action, 'confidence': confidence}
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {str(e)}")
            self.logger.error(f"Exception traceback: {traceback.format_exc()}")
            return {'action': 'hold', 'confidence': 0.50}
    
    def get_minimum_order_requirements(self, symbol: str) -> dict:
        """Get minimum order requirements for a given symbol"""
        try:
            # Define minimum requirements for each symbol
            requirements = {
                'SOLUSD': {
                    'min_vol': 0.1,      # Minimum volume
                    'min_price': 0.01,   # Minimum price
                    'price_decimals': 4,  # Price decimal places
                    'vol_decimals': 8    # Volume decimal places
                },
                'AVAXUSD': {
                    'min_vol': 0.1,
                    'min_price': 0.01,
                    'price_decimals': 4,
                    'vol_decimals': 8
                },
                'XRPUSD': {
                    'min_vol': 10.0,
                    'min_price': 0.00001,
                    'price_decimals': 5,
                    'vol_decimals': 8
                },
                'XDGUSD': {
                    'min_vol': 50.0,
                    'min_price': 0.00001,
                    'price_decimals': 6,
                    'vol_decimals': 8
                },
                'SHIBUSD': {
                    'min_vol': 50000.0,
                    'min_price': 0.000001,
                    'price_decimals': 8,
                    'vol_decimals': 8
                },
                'PEPEUSD': {
                    'min_vol': 50000.0,
                    'min_price': 0.000001,
                    'price_decimals': 8,
                    'vol_decimals': 8
                }
            }
            
            if symbol not in requirements:
                self.logger.error(f"No requirements defined for {symbol}")
                # Return default requirements
                return {
                    'min_vol': 0.1,
                    'min_price': 0.01,
                    'price_decimals': 8,
                    'vol_decimals': 8
                }
                
            return requirements[symbol]
            
        except Exception as e:
            self.logger.error(f"Error getting minimum requirements for {symbol}: {str(e)}")
            # Return safe default values
            return {
                'min_vol': 0.1,
                'min_price': 0.01,
                'price_decimals': 8,
                'vol_decimals': 8
            }
    
    async def train_ai_models(self, historical_data: pd.DataFrame):
        """Train the AI models with historical data"""
        try:
            self.logger.info("Training AI models...")
            
            # Prepare sequence data
            X, y = self.ai_enhancer.prepare_sequence_data(historical_data)
            
            if len(X) < 1000:  # Minimum required samples
                self.logger.warning("Insufficient data for AI training")
                return False
            
            # Split data
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            # Build and train LSTM
            self.ai_enhancer.lstm_model = self.ai_enhancer.build_lstm_model()
            self.ai_enhancer.lstm_model.fit(
                X_train, y_train,
                epochs=10,
                batch_size=32,
                validation_data=(X_test, y_test),
                verbose=1
            )
            
            # Build and train Transformer
            self.ai_enhancer.transformer_model = self.ai_enhancer.build_transformer_model()
            self.ai_enhancer.transformer_model.fit(
                X_train, y_train,
                epochs=10,
                batch_size=32,
                validation_data=(X_test, y_test),
                verbose=1
            )
            
            self.ai_trained = True
            self.logger.info("AI models trained successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error training AI models: {str(e)}")
            return False
    
    def format_order_quantity(self, symbol: str, quantity: float) -> str:
        """Format the order quantity according to symbol requirements"""
        try:
            requirements = self.get_minimum_order_requirements(symbol)
            decimals = requirements['vol_decimals']
            # Format with required decimal places and remove trailing zeros
            return f"{quantity:.{decimals}f}".rstrip('0').rstrip('.')
        except Exception as e:
            self.logger.error(f"Error formatting quantity for {symbol}: {str(e)}")
            return f"{quantity:.8f}".rstrip('0').rstrip('.')  # Safe default
        
    def format_order_price(self, symbol: str, price: float) -> str:
        """Format the order price according to symbol requirements"""
        try:
            requirements = self.get_minimum_order_requirements(symbol)
            decimals = requirements['price_decimals']
            # Format with required decimal places and remove trailing zeros
            return f"{price:.{decimals}f}".rstrip('0').rstrip('.')
        except Exception as e:
            self.logger.error(f"Error formatting price for {symbol}: {str(e)}")
            return f"{price:.8f}".rstrip('0').rstrip('.')  # Safe default
        
    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format for consistent comparison"""
        # Remove common separators and standardize
        return symbol.replace('/', '').replace('-', '').upper()
        
    def format_price_for_log(self, symbol: str, price: float) -> str:
        """Format price with appropriate decimals for logging"""
        if price is None:
            return "N/A"
            
        # Define formatting by symbol
        if symbol in ['SHIBUSD', 'PEPEUSD']:
            return f"${price:.8f}"  # Show 8 decimals for very small value coins
        elif symbol == 'XDGUSD':
            return f"${price:.6f}"  # 6 decimals for DOGE
        elif symbol == 'XRPUSD':
            return f"${price:.5f}"  # 5 decimals for XRP
        else:
            return f"${price:.2f}"
        
    def execute_trade_demo(self, symbol: str, signal: dict, price: float = None):
        """Simplified synchronous version for demo trades with live price data"""
        try:
            # Always get fresh price at execution time
            if price is None or price <= 0:
                price = self.get_latest_price(symbol)
                
            if not price or price <= 0:
                self.logger.error(f"Invalid price for {symbol}: {price}")
                return None
                
            # Calculate position size using demo balance
            position_size = self.calculate_position_size(symbol, signal)
            if position_size <= 0:
                return None
                
            # Get minimum requirements for the symbol
            requirements = self.get_minimum_order_requirements(symbol)
            min_volume = requirements['min_vol']
            
            # SELL LOGIC
            if signal['action'] == 'sell':
                if symbol in self.demo_positions:
                    position = self.demo_positions[symbol]
                    quantity = position['volume']
                    entry_price = position['entry_price']
                    
                    # Ensure minimum volume
                    if quantity < min_volume:
                        self.logger.warning(f"Position size {quantity} below minimum {min_volume}")
                        return None
                    
                    # Calculate sale value
                    sale_value = quantity * price
                    
                    # Calculate profit/loss
                    entry_value = quantity * entry_price
                    profit_loss = sale_value - entry_value
                    pnl_percentage = (profit_loss / entry_value) * 100
                    
                    # Update balances
                    self.demo_balance['ZUSD'] += sale_value
                    self.demo_balance[symbol] = 0
                    del self.demo_positions[symbol]
                    
                    # Record trade with profit/loss information
                    trade = {
                        'timestamp': datetime.now(),
                        'symbol': symbol,
                        'type': 'sell',
                        'price': price,
                        'quantity': quantity,
                        'value': sale_value,
                        'balance_after': self.demo_balance['ZUSD'],
                        'profit_loss': profit_loss,
                        'pnl_percentage': pnl_percentage,
                        'entry_price': entry_price
                    }
                    self.trade_history.append(trade)
                    
                    # Update portfolio history
                    self.portfolio_history.append({
                        'timestamp': datetime.now(),
                        'balance': self.demo_balance['ZUSD'],
                        'equity': self.calculate_total_equity()
                    })
                    
                    self.logger.info(f"Demo SELL executed: {quantity} {symbol} @ ${price}")
                    self.logger.info(f"P&L: ${profit_loss:.2f} ({pnl_percentage:.2f}%)")
                    return {'status': 'success', 'trade': trade}
                        
            # BUY LOGIC  
            elif signal['action'] == 'buy':
                quantity = position_size / price
                
                # Ensure minimum volume
                if quantity < min_volume:
                    quantity = min_volume
                    position_size = quantity * price
                
                # Check if we have enough balance
                if position_size > self.demo_balance['ZUSD']:
                    self.logger.warning(f"Insufficient demo balance. Need ${position_size:.2f}, have ${self.demo_balance['ZUSD']:.2f}")
                    return None
                    
                # Update balances
                self.demo_balance['ZUSD'] -= position_size
                self.demo_balance[symbol] = self.demo_balance.get(symbol, 0) + quantity
                
                # Record position
                self.demo_positions[symbol] = {
                    'volume': quantity,
                    'entry_price': price,
                    'entry_time': datetime.now(),
                    'high_price': price
                }
                
                # Record trade
                trade = {
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'type': 'buy',
                    'price': price,
                    'quantity': quantity,
                    'value': position_size,
                    'balance_after': self.demo_balance['ZUSD'],
                    'profit_loss': 0,
                    'pnl_percentage': 0
                }
                self.trade_history.append(trade)
                
                # Update portfolio history
                self.portfolio_history.append({
                    'timestamp': datetime.now(),
                    'balance': self.demo_balance['ZUSD'],
                    'equity': self.calculate_total_equity()
                })
                
                self.logger.info(f"Demo BUY executed: {quantity} {symbol} @ ${price}")
                return {'status': 'success', 'trade': trade}
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Demo trade execution error: {e}")
            return None
            
    def update_trade_history(self, symbol: str, action: str, quantity: float):
        """Update local tracking of positions based on executed trades"""
        if symbol not in self.trade_history:
            self.trade_history[symbol] = {'quantity': 0}
        
        if action == 'buy':
            self.trade_history[symbol]['quantity'] += quantity
        elif action == 'sell':
            self.trade_history[symbol]['quantity'] -= quantity
            self.trade_history[symbol]['quantity'] = max(0, self.trade_history[symbol]['quantity'])  # Prevent negative quantities
        
    def sync_positions(self):
        """Sync bot's understanding of positions with actual account data from Kraken"""
        try:
            positions = self.k.get_open_orders()  # Check Kraken's API for the correct method to get open orders/positions
            for position in positions:
                symbol = position['descr']['pair']
                quantity = float(position['vol'])
                self.update_trade_history(symbol, 'buy', quantity)  # Assuming all open orders are 'buy' for simplicity
        except Exception as e:
            self.logger.error(f"Failed to sync positions: {str(e)}")

    async def monitor_positions(self):
        """Monitor and manage demo positions with risk management"""
        try:
            current_time = datetime.now()
            
            # For demo mode, we'll just use our local tracking
            # instead of trying to call authenticated API endpoints
            
            # Iterate through all demo positions
            positions_to_close = []  # Track positions that need to be closed
            
            for symbol, position in self.demo_positions.items():
                current_price = self.get_latest_price(symbol)
                if not current_price:
                    self.logger.warning(f"Could not get current price for {symbol}")
                    continue
                    
                entry_price = position['entry_price']
                quantity = position['volume']
                
                # Calculate position metrics
                position_value = quantity * current_price
                unrealized_pnl = (current_price - entry_price) * quantity
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                
                # Update high price if we have a new high
                if current_price > position['high_price']:
                    position['high_price'] = current_price
                
                # Log position status
                self.logger.info(f"\nPosition Update - {symbol}:")
                self.logger.info(f"Quantity: {quantity:.8f}")
                self.logger.info(f"Entry: ${entry_price:.8f}")
                self.logger.info(f"Current: ${current_price:.8f}")
                self.logger.info(f"P&L: ${unrealized_pnl:.2f} ({pnl_percentage:.2f}%)")
                
                # Check take profit
                if pnl_percentage >= self.take_profit_pct * 100:
                    self.logger.info(f"Take profit triggered for {symbol} at {pnl_percentage:.2f}%")
                    positions_to_close.append({
                        'symbol': symbol,
                        'reason': 'take_profit',
                        'price': current_price
                    })
                    continue
                
                # Check stop loss
                if pnl_percentage <= -self.stop_loss_pct * 100:
                    self.logger.info(f"Stop loss triggered for {symbol} at {pnl_percentage:.2f}%")
                    positions_to_close.append({
                        'symbol': symbol,
                        'reason': 'stop_loss',
                        'price': current_price
                    })
                    continue
                
                # Check trailing stop
                if pnl_percentage > 0:  # Only check trailing stop if we're in profit
                    highest_price = position['high_price']
                    trailing_stop_price = highest_price * (1 - self.trailing_stop_pct)
                    
                    if current_price < trailing_stop_price:
                        self.logger.info(f"Trailing stop triggered for {symbol} at ${current_price:.8f}")
                        positions_to_close.append({
                            'symbol': symbol,
                            'reason': 'trailing_stop',
                            'price': current_price
                        })
                        continue
                
                # Check maximum drawdown
                if pnl_percentage <= -self.max_drawdown * 100:
                    self.logger.info(f"Maximum drawdown triggered for {symbol} at {pnl_percentage:.2f}%")
                    positions_to_close.append({
                        'symbol': symbol,
                        'reason': 'max_drawdown',
                        'price': current_price
                    })
                    continue
                    
            # Close positions that triggered risk management rules
            for close_order in positions_to_close:
                symbol = close_order['symbol']
                await self.execute_trade_with_risk_management(
                    symbol=symbol,
                    signal={'action': 'sell', 'confidence': 1.0},
                    price=close_order['price']
                )
                
            # Update portfolio history
            total_equity = self.calculate_total_equity()
            self.portfolio_history.append({
                'timestamp': current_time,
                'balance': self.demo_balance['ZUSD'],
                'equity': total_equity
            })
            
        except Exception as e:
            # Don't include authentication errors in the error message
            error_msg = str(e)
            if "Either key or secret is not set" in error_msg:
                self.logger.info("Monitoring positions in demo mode without authentication")
            else:
                self.logger.error(f"Error monitoring positions: {error_msg}")

    def check_and_reset_balance(self):
        """Check if balance is too low and reset if needed"""
        if self.demo_balance['ZUSD'] < self.min_zusd_balance:
            self.logger.warning(f"Balance ${self.demo_balance['ZUSD']:.2f} below minimum ${self.min_zusd_balance}")
            # Reset to a reasonable amount
            self.demo_balance['ZUSD'] = 10000.0  # Smaller reset amount
            self.save_demo_state()
            self.logger.info(f"Demo balance reset to ${self.demo_balance['ZUSD']:.2f}")
            return True
        return False
        
    async def initialize_position_tracking(self):
        """Initialize demo position tracking"""
        try:
            # For demo bot, we start with no positions
            self.demo_positions = {}
            self.portfolio_history = [{
                'timestamp': datetime.now(),
                'balance': self.demo_balance['ZUSD'],
                'equity': self.demo_balance['ZUSD']
            }]
            self.logger.info("Demo position tracking initialized")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing demo position tracking: {str(e)}")
            return False
        
    def setup_database(self):
        """Set up SQLite database for storing trading data"""
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
        
            # Create market data table
            c.execute('''CREATE TABLE IF NOT EXISTS market_data
                        (timestamp TEXT, symbol TEXT, price REAL,
                        volume REAL, rsi REAL, macd REAL, trend INTEGER,
                        volatility REAL, close REAL)''')
        
            conn.commit()
            conn.close()
        
        except Exception as e:
            self.logger.error(f"Database setup error: {str(e)}")
        
    def store_trade_data(self, trade_data: dict):
        """Store trade information in database"""
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
        
            # Store trade data
            c.execute('''INSERT INTO trades VALUES
                        (?,?,?,?,?,?,?)''', (
                datetime.now().isoformat(),
                trade_data['symbol'],
                trade_data['action'],
                trade_data['price'],
                trade_data['quantity'],
                trade_data.get('profit_loss', 0),
                str(trade_data.get('market_conditions', {}))
            ))
        
            conn.commit()
            conn.close()
        
        except Exception as e:
            self.logger.error(f"Error storing trade data: {str(e)}")
        
    def store_market_data(self, symbol: str, df: pd.DataFrame):
        """Store market data with support for both single symbol and batch operations"""
        try:
            conn = sqlite3.connect(self.db_name)
        
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
        
            # Handle both single symbol and batch data
            if 'symbol' not in df.columns:
                df['symbol'] = symbol
        
            # Convert timestamp to string if needed
            if 'timestamp' not in df.columns and 'timestamp' in df.index.names:
                df['timestamp'] = df.index.get_level_values('timestamp').astype(str)
            elif 'timestamp' not in df.columns:
                df['timestamp'] = pd.Timestamp.now().isoformat()
        
            # Prepare the required columns
            market_data = pd.DataFrame({
                'timestamp': df['timestamp'],
                'symbol': df['symbol'] if 'symbol' in df.columns else symbol,
                'close': df['close'],
                'volume': df['volume'],
                'rsi': df['rsi'],
                'macd': df['macd'],
                'trend': (df['sma_short'] > df['sma_long']).astype(int) if 'sma_short' in df.columns else 0,
                'volatility': df['volatility'] if 'volatility' in df.columns else df['close'].pct_change().rolling(20).std()
            })
        
            # Store data in chunks to prevent memory issues
            chunk_size = 1000
            for i in range(0, len(market_data), chunk_size):
                chunk = market_data.iloc[i:i + chunk_size]
                chunk.to_sql('market_data', conn, if_exists='append', index=False)
        
            self.logger.info(f"Stored {len(market_data)} rows of market data")
            conn.close()
        
        except Exception as e:
            self.logger.error(f"Error storing market data: {str(e)}")
    
    async def perform_initial_training(self):
        """Perform initial model training including AI models"""
        try:
            self.logger.info("Starting initial model training...")
            
            # Get historical data for all symbols
            all_data = []
            for symbol in self.symbols:
                try:
                    df = await self.get_historical_data(symbol)
                    if df is not None and not df.empty:
                        df = self.calculate_indicators(df)
                        all_data.append(df)
                        self.logger.info(f"Collected {len(df)} samples for {symbol}")
                except Exception as e:
                    self.logger.error(f"Error collecting data for {symbol}: {str(e)}")
        
            if not all_data:
                self.logger.warning("No historical data available for training")
                return False
        
            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Train ML Model
            try:
                features_df = self.model_manager.prepare_features(combined_df)
                labels = self.model_manager.create_labels(combined_df)
                
                training_success = self.model_manager.train_model(features_df, labels)
                if training_success:
                    self.is_initially_trained = True
                    self.logger.info("ML model trained successfully")
                else:
                    self.logger.error("ML model training failed")
                    return False
            except Exception as e:
                self.logger.error(f"Error in ML training: {str(e)}")
                return False
        
            # Train AI Models
            try:
                self.logger.info("Starting AI model training...")
                # Prepare sequence data
                X, y = self.ai_enhancer.prepare_sequence_data(combined_df)
                
                if len(X) < 1000:  # Minimum required samples
                    self.logger.warning("Insufficient data for AI training")
                    return False
                
                # Split data
                train_size = int(len(X) * 0.8)
                X_train, X_test = X[:train_size], X[train_size:]
                y_train, y_test = y[:train_size], y[train_size:]
                
                # Build and train LSTM
                self.logger.info("Training LSTM model...")
                self.ai_enhancer.lstm_model = self.ai_enhancer.build_lstm_model()
                self.ai_enhancer.lstm_model.fit(
                    X_train, y_train,
                    epochs=10,
                    batch_size=32,
                    validation_data=(X_test, y_test),
                    verbose=1
                )
                
                # Build and train Transformer
                self.logger.info("Training Transformer model...")
                self.ai_enhancer.transformer_model = self.ai_enhancer.build_transformer_model()
                self.ai_enhancer.transformer_model.fit(
                    X_train, y_train,
                    epochs=10,
                    batch_size=32,
                    validation_data=(X_test, y_test),
                    verbose=1
                )
                
                self.ai_trained = True
                self.logger.info("AI models trained successfully")
                
            except Exception as e:
                self.logger.error(f"Error in AI training: {str(e)}")
                self.logger.error(traceback.format_exc())
                return False
        
            return self.is_initially_trained and self.ai_trained
            
        except Exception as e:
            self.logger.error(f"Error in initial training: {str(e)}")
            return False
    
    def calculate_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced technical indicators"""
        try:
            # Create a copy to avoid modifying the original
            df = df.copy()
            
            # Ensure we have required columns
            required_columns = ['high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            # Basic price and volume features
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log1p(df['returns'].fillna(0))
            df['rolling_std_20'] = df['returns'].rolling(window=20, min_periods=1).std()
            df['rolling_std_50'] = df['returns'].rolling(window=50, min_periods=1).std()
            
            # Volume features
            df['volume_sma'] = df['volume'].rolling(window=20, min_periods=1).mean()
            df['volume_ma_ratio'] = df['volume'] / df['volume_sma']
            df['volume_std'] = df['volume'].rolling(window=20, min_periods=1).std()
            
            # Technical indicators
            try:
                # RSI
                rsi_indicator = ta.momentum.RSIIndicator(close=df['close'], window=14)
                df['rsi'] = rsi_indicator.rsi()
                df['rsi_divergence'] = df['rsi'].diff()
                
                # Momentum
                df['mom_14'] = ta.momentum.ROCIndicator(close=df['close'], window=14).roc()
                df['mom_30'] = ta.momentum.ROCIndicator(close=df['close'], window=30).roc()
                
                # MACD
                macd_indicator = ta.trend.MACD(close=df['close'])
                df['macd'] = macd_indicator.macd()
                df['macd_signal'] = macd_indicator.macd_signal()
                df['macd_diff'] = macd_indicator.macd_diff()
                
                # Bollinger Bands
                bb_indicator = ta.volatility.BollingerBands(close=df['close'])
                df['bb_width'] = (bb_indicator.bollinger_hband() - bb_indicator.bollinger_lband()) / bb_indicator.bollinger_mavg()
                df['bb_position'] = (df['close'] - bb_indicator.bollinger_lband()) / (bb_indicator.bollinger_hband() - bb_indicator.bollinger_lband())
                
                # ATR and ADX
                df['atr'] = ta.volatility.AverageTrueRange(
                    high=df['high'],
                    low=df['low'],
                    close=df['close']
                ).average_true_range()
                
                adx_indicator = ta.trend.ADXIndicator(
                    high=df['high'],
                    low=df['low'],
                    close=df['close']
                )
                df['adx'] = adx_indicator.adx()
                df['adx_pos'] = adx_indicator.adx_pos()
                df['adx_neg'] = adx_indicator.adx_neg()
                
            except Exception as e:
                self.logger.error(f"Error calculating technical indicators: {str(e)}")
                raise
            
            # Clean up any NaN or infinite values
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating advanced indicators: {str(e)}")
            raise
    
    async def update_dashboard(self):
        """Update dashboard without IPython clear_output"""
        try:
            print("\n============= TRADING DASHBOARD =============")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
            # Account Status
            try:
                account = self.trading_client.get_account()
                print("\nAccount Status:")
                print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
                print(f"Cash Balance: ${float(account.cash):,.2f}")
                print(f"Total P/L: ${float(account.portfolio_value) - 60.00:,.2f} ({((float(account.portfolio_value) - 60.00) / 60.00) * 100:.2f}%)")
            except Exception as e:
                print("Account information temporarily unavailable")
    
            # Positions
            print("\nPositions:")
            try:
                positions = self.trading_client.get_all_positions()
                if positions:
                    for position in positions:
                        print(f"\n{position.symbol}:")
                        if hasattr(position, 'qty'):
                            print(f"  Quantity: {position.qty}")
                        if hasattr(position, 'current_price'):
                            print(f"  Current Price: ${float(position.current_price):.4f}")
                        if hasattr(position, 'unrealized_pl') and hasattr(position, 'unrealized_plpc'):
                            print(f"  P/L: ${float(position.unrealized_pl):.2f} ({float(position.unrealized_plpc) * 100:.2f}%)")
                else:
                    print("No active positions")
            except Exception as e:
                print("Position information temporarily unavailable")
    
            # Market Analysis
            print("\nMarket Analysis:")
            try:
                conn = sqlite3.connect(self.db_name)
                cursor = conn.cursor()
    
                for symbol in self.symbols:
                    print(f"\n{symbol}:")
                    try:
                        # Get data point count for this symbol
                        cursor.execute("SELECT COUNT(*) FROM market_data WHERE symbol=?", (symbol,))
                        data_count = cursor.fetchone()[0]
                        print(f"  Data Points Collected: {data_count}")
                        print(f"  Minimum Required: {max(self.sma_long, self.min_training_data)}")
    
                        # Get latest data for this symbol
                        cursor.execute("""
                            SELECT close, volume, rsi, macd, volatility
                            FROM market_data
                            WHERE symbol=?
                            ORDER BY timestamp DESC
                            LIMIT 1""", (symbol,))
                        latest = cursor.fetchone()
    
                        if latest:
                            close, volume, rsi, macd, volatility = latest
                            print(f"  Latest Price: ${float(close):.4f}")
                            if rsi is not None:
                                print(f"  RSI: {float(rsi):.2f}")
                            if volatility is not None:
                                print(f"  Volatility: {float(volatility):.4f}")
    
                        print(f"  Allocation: {self.symbols[symbol]*100:.1f}%")
    
                        # Display data collection status
                        if data_count >= self.min_training_data:
                            print("  Status: ✅ Sufficient data collected")
                        else:
                            print(f"  Status: 📊 Collecting data ({data_count}/{self.min_training_data})")
    
                    except Exception as e:
                        print(f"  Error getting data: {str(e)}")
    
                conn.close()
            except Exception as e:
                print(f"Database access error: {str(e)}")
    
            # Model Status
            print("\nModel Status:")
            if not self.is_initially_trained:
                time_elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
                remaining = max(0, self.initial_training_hours - time_elapsed)
                print(f"Initial Training - {remaining:.1f} hours remaining")
            else:
                print("Model: Trained and Active")
    
            print("\n==========================================")
    
        except Exception as e:
            self.logger.error(f"Error updating dashboard: {str(e)}")
            print("\nStatus: Bot Running - Limited Information Available")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def get_account_balance(self):
        """Get detailed account balance information"""
        try:
            balance = self.k.get_account_balance()
            if isinstance(balance, pd.DataFrame):
                balance_dict = balance.to_dict()['vol']
            else:
                balance_dict = balance
        
            # Log all balances
            self.logger.info("\n=== Account Balances ===")
            for currency, amount in balance_dict.items():
                self.logger.info(f"{currency}: {float(amount):.8f}")
            
            # Get USD balance specifically
            usd_balance = float(balance_dict.get('ZUSD', 0))
            self.logger.info(f"\nTrading Balance (USD): ${usd_balance:.2f}")
            
            return balance_dict
            
        except Exception as e:
            self.logger.error(f"Error getting account balance: {str(e)}")
            return {}
    
    async def collect_data_for_symbol(self, symbol: str):
        """Collect data for a single symbol with proper error handling"""
        try:
            df = self.get_historical_data(symbol)
            if df is not None:
                df = self.calculate_advanced_indicators(df)
                self.store_market_data(symbol, df)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error collecting data for {symbol}: {str(e)}")
            return False
        
    async def collect_all_data(self):
        """Collect data for all symbols"""
        results = {}
        for symbol in self.symbols:
            success = await self.collect_data_for_symbol(symbol)
            results[symbol] = success
        return results
        
    def check_market_conditions(self, symbol: str, df: pd.DataFrame) -> bool:
        """Enhanced market condition checks"""
        try:
            latest = df.iloc[-1]
            
            # Check volatility
            volatility = df['close'].pct_change().rolling(20).std().iloc[-1]
            if volatility > self.market_conditions['high_volatility']:
                self.logger.warning(f"High volatility detected for {symbol}: {volatility:.2%}")
                return False
                
            # Check volume/liquidity
            if latest['volume'] < self.market_conditions['low_liquidity']:
                self.logger.warning(f"Low liquidity for {symbol}")
                return False
                
            # Calculate and check spread if available
            if 'high' in df.columns and 'low' in df.columns:
                spread = (latest['high'] - latest['low']) / latest['low']
                if spread > self.market_conditions['excessive_spread']:
                    self.logger.warning(f"Excessive spread for {symbol}: {spread:.2%}")
                    return False
                    
            return True
        except Exception as e:
            self.logger.error(f"Error checking market conditions: {str(e)}")
            return False
    
    async def implement_trailing_stop(self, symbol: str, entry_price: float):
        """Implement trailing stop loss"""
        try:
            highest_price = entry_price
            while True:
                current_price = float(self.trading_client.get_latest_trade(symbol).price)
                
                if current_price > highest_price:
                    highest_price = current_price
                    trailing_stop = highest_price * (1 - self.trailing_stop_pct)
                
                if current_price < trailing_stop:
                    self.logger.info(f"Trailing stop triggered for {symbol} at {current_price}")
                    await self.close_position(symbol)
                    break
                    
                await asyncio.sleep(1)
        except Exception as e:
            self.logger.error(f"Error in trailing stop: {str(e)}")
        
    def calculate_position_size(self, symbol: str, signal: dict) -> float:
        try:
            # Get current price from price feed
            price = self.get_latest_price(symbol)
            if price is None or price <= 0:
                self.logger.error("Invalid price")
                return 0
                
            # For demo bot, use demo balance instead of Kraken API
            total_usd_balance = self.demo_balance['ZUSD']
            
            if total_usd_balance < self.min_zusd_balance:
                self.logger.warning(f"Balance ${total_usd_balance} below minimum ${self.min_zusd_balance}")
                return 0
            
            # IMPROVED RISK MANAGEMENT - Fixed percentage risk per trade
            # Never risk more than 1% of account on any single trade
            max_risk_amount = total_usd_balance * 0.01
            
            # PORTFOLIO PROTECTION - Reduce position size when equity drops
            equity_ratio = self.calculate_total_equity() / 100000.0  # Initial capital ratio
            
            # Implement smart position sizing based on account drawdown
            if equity_ratio < 0.85:  # Lost 15% or more
                size_multiplier = 0.3  # Drastic reduction - trade at 30% of normal size
                self.logger.warning(f"SIGNIFICANT DRAWDOWN: Scaling position to 30% of normal size")
            elif equity_ratio < 0.95:  # Lost 5-15%
                size_multiplier = 0.6  # Moderate reduction - trade at 60% of normal size
                self.logger.warning(f"MODERATE DRAWDOWN: Scaling position to 60% of normal size")
            else:
                size_multiplier = 1.0  # No adjustment needed
            
            # Calculate size conservatively - reduce default allocation by 50%
            allocation = self.symbols[symbol] * 0.5  # Cut standard allocation in half
            base_position_size = min(
                total_usd_balance * allocation,
                total_usd_balance * (self.max_position_size * 0.5)  # Cut max position size in half too
            ) * size_multiplier
            
            # ONLY increase size for extremely high confidence signals
            confidence_factor = 1.0
            if 'confidence' in signal and signal['action'] == 'buy':
                # Only increase size for very high confidence signals (above 0.65)
                normalized_confidence = (signal['confidence'] - 0.65) * 10  # Scale 0.65-0.75 to 0-1
                if normalized_confidence > 0:
                    confidence_factor = 1.0 + (normalized_confidence * 0.3)  # Maximum increase of 30%
                    self.logger.info(f"High conviction signal: Increasing size by {((confidence_factor-1)*100):.1f}%")
            
            position_size = base_position_size * confidence_factor
            
            # Verify against max risk amount (hard cap at 1% account risk)
            if position_size > max_risk_amount:
                position_size = max_risk_amount
                self.logger.info(f"Position size capped at max risk amount: ${position_size:.2f}")
            
            # Ensure minimum position size
            if position_size < self.min_position_value:
                self.logger.warning(f"Position size ${position_size:.2f} below minimum ${self.min_position_value}")
                return 0
                
            return position_size
            
        except Exception as e:
            self.logger.error(f"Demo position size calculation error: {e}")
            return 0
    
    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """More aggressive market regime detection for profitable trading"""
        try:
            # Price momentum
            price_momentum = df['close'].pct_change(10).iloc[-1]
            
            # Volatility
            volatility = df['returns'].rolling(20).std().iloc[-1]
            
            # Trend strength
            adx = df['adx'].iloc[-1] if 'adx' in df.columns else 25
            
            # Moving average relationship
            ma_relationship = df['sma_20'].iloc[-1] / df['sma_50'].iloc[-1] - 1
            
            # Volume trend
            volume_trend = df['volume_ma_ratio'].iloc[-1] if 'volume_ma_ratio' in df.columns else 1.0
            
            # Classify regime - more sensitive thresholds
            if adx > 25 and ma_relationship > 0.01 and volume_trend > 1.0:  # Reduced thresholds
                return "strong_uptrend"  # More likely to identify uptrends
            elif adx > 25 and ma_relationship < -0.01 and volume_trend > 1.0:  # Reduced thresholds
                return "strong_downtrend"  # More likely to identify downtrends
            elif adx < 15 and abs(ma_relationship) < 0.008:  # Tightened band
                return "consolidation"  # Sideways market
            elif volatility > 0.025:  # Lower threshold, catches more volatile markets
                return "high_volatility"  # High volatility regime
            elif volatility < 0.008:  # Adjusted for more low volatility identification
                return "low_volatility"  # Low volatility regime
            else:
                return "mixed"  # Mixed or unclear market conditions
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {str(e)}")
            return "mixed"

    def check_excessive_correlation(self) -> bool:
        buy_count = 0
        sell_count = 0
        
        for symbol in self.symbols:
            if symbol in self.demo_positions:
                buy_count += 1
        
        # Limit overexposure in one direction
        if buy_count > len(self.symbols) * 0.7:  # More than 70% of assets
            return True
        
        return False
    
    async def retrain_models(self):
        try:
            # Collect new data
            new_data = await self.collect_all_data()
            
            # Prepare features and labels
            features_df = self.model_manager.prepare_features(new_data)
            labels = self.model_manager.create_labels(new_data)
            
            # Retrain ML model
            self.model_manager.train_model(features_df, labels)
            
            # Retrain AI models
            await self.train_ai_models(new_data)
            
            return True
        except Exception as e:
            self.logger.error(f"Error in retraining: {str(e)}")
            return False
    
    def update_performance_metrics(self):
        """Track and analyze performance metrics"""
        try:
            current_time = datetime.now()
            
            # Calculate daily P&L
            daily_pnl = 0
            positions = self.trading_client.get_all_positions()
            for position in positions:
                daily_pnl += float(position.unrealized_pl)
            
            # Update metrics
            self.performance_metrics[current_time] = {
                'pnl': daily_pnl,
                'positions': len(positions),
                'portfolio_value': float(self.trading_client.get_account().portfolio_value)
            }
            
            # Calculate drawdown
            if len(self.performance_metrics) > 1:
                peak = max(m['portfolio_value'] for m in self.performance_metrics.values())
                current = self.performance_metrics[current_time]['portfolio_value']
                drawdown = (peak - current) / peak
                
                if drawdown > self.max_drawdown:
                    self.logger.warning(f"Maximum drawdown exceeded: {drawdown:.2%}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {str(e)}")
            return True
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price with real-time data and proper error handling"""
        # Add timestamp logging
        current_time = datetime.now()
        self.logger.info(f"Fetching real-time price for {symbol} at {current_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # Check if we should use cached price
        if hasattr(self, 'demo_rate_limiter') and not self.demo_rate_limiter.should_fetch_price(symbol):
            cached_price = self.demo_rate_limiter.get_cached_price(symbol)
            if cached_price:
                self.logger.info(f"Using cached price for {symbol}: ${cached_price}")
                return cached_price
        
        # Proceed with normal price fetching
        max_retries = 3
        precision = {
            'SHIBUSD': 8,
            'PEPEUSD': 8,
            'XDGUSD': 6,
            'XRPUSD': 5,
            'SOLUSD': 2,
            'AVAXUSD': 2
        }.get(symbol, 8)
        
        for attempt in range(max_retries):
            try:
                # Try using Ticker API (correct method for your version of pykrakenapi)
                try:
                    # Use the proper ticker method based on your API version
                    ticker = self.kraken.query_public('Ticker', {'pair': symbol})
                    if ticker and 'result' in ticker and symbol in ticker['result']:
                        # The 'c' field contains the last trade closed info: [price, volume]
                        price = float(ticker['result'][symbol]['c'][0])
                        if price > 0:
                            self.logger.info(f"Got real-time ticker price for {symbol}: ${price}")
                            # Cache the price
                            if hasattr(self, 'demo_rate_limiter'):
                                self.demo_rate_limiter.update_price(symbol, round(price, precision))
                            return round(price, precision)
                except Exception as ticker_error:
                    self.logger.warning(f"Ticker fetch error for {symbol}: {str(ticker_error)}")
                
                # Fallback to OHLC if ticker fails
                ohlc = self.k.get_ohlc_data(symbol, interval=1)[0]
                if ohlc is not None and not ohlc.empty:
                    price = float(ohlc.iloc[-1]['close'])
                    if price > 0:
                        self.logger.info(f"Got OHLC price for {symbol}: ${price}")
                        # Cache the price
                        if hasattr(self, 'demo_rate_limiter'):
                            self.demo_rate_limiter.update_price(symbol, round(price, precision))
                        return round(price, precision)
                        
                # Fallback to recent trades
                try:
                    trades = self.k.get_recent_trades(symbol)[0]
                    if trades is not None and not trades.empty:
                        price = float(trades.iloc[0]['price'])
                        if price > 0:
                            self.logger.info(f"Got recent trades price for {symbol}: ${price}")
                            # Cache the price
                            if hasattr(self, 'demo_rate_limiter'):
                                self.demo_rate_limiter.update_price(symbol, round(price, precision))
                            return round(price, precision)
                except Exception as trades_error:
                    self.logger.warning(f"Recent trades fetch error for {symbol}: {str(trades_error)}")
        
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying price fetch for {symbol}")
                    time.sleep(1)
        
            except Exception as e:
                self.logger.error(f"Price fetch attempt {attempt+1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        self.logger.error(f"Failed to get price for {symbol}")
        return None
    
    def handle_demo_position_monitoring(self):
        """Enhanced position monitoring with dynamic exit strategies"""
        try:
            current_time = datetime.now()
            positions_to_close = []  # Track positions that need to be closed
            
            for symbol, position in self.demo_positions.items():
                current_price = self.get_latest_price(symbol)
                if not current_price:
                    self.logger.warning(f"Could not get current price for {symbol}")
                    continue
                    
                entry_price = position['entry_price']
                quantity = position['volume']
                entry_time = position['entry_time']
                position_age = (current_time - entry_time).total_seconds() / 3600  # Hours
                
                # Calculate position metrics
                position_value = quantity * current_price
                unrealized_pnl = (current_price - entry_price) * quantity
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                
                # Update high price if we have a new high
                if current_price > position['high_price']:
                    position['high_price'] = current_price
                
                # Log position status
                self.logger.info(f"\nPosition Update - {symbol}:")
                self.logger.info(f"Quantity: {quantity:.8f}")
                self.logger.info(f"Entry: ${entry_price:.8f}")
                self.logger.info(f"Current: ${current_price:.8f}")
                self.logger.info(f"P&L: ${unrealized_pnl:.2f} ({pnl_percentage:.2f}%)")
                
                # TIGHTER STOP LOSS - Reduced from 0.8% to 0.6%
                base_stop_loss_pct = 0.006  # 0.6% initial stop loss
                
                # ADVANCED AGE-BASED STOP LOSS ADJUSTMENT
                # Tighten stop loss as position ages
                stop_loss_pct = base_stop_loss_pct
                
                if position_age > 12:  # Reduced from 24 to 12 hours
                    # Tighten stop loss significantly for older positions
                    if pnl_percentage > 0.5:  # In profit > 0.5%
                        stop_loss_pct = 0  # Move to breakeven
                        self.logger.info(f"Position age: {position_age:.1f} hours, moved stop to breakeven")
                    else:
                        # If losing and old, exit quicker
                        stop_loss_pct = base_stop_loss_pct * 0.7  # 30% tighter
                        self.logger.info(f"Position age: {position_age:.1f} hours, tightened stop by 30%")
                
                # IMPROVED TRAILING STOP - More aggressive trailing
                # Use tiered trailing stops based on profit level
                trailing_stop_pct = self.trailing_stop_pct  # Base trailing stop
                
                if pnl_percentage > 5.0:  # Large profit (>5%)
                    trailing_stop_pct = 0.02  # Wider 2% trailing stop to let profits run
                    self.logger.info(f"Using wider trailing stop (2%) for large profit position")
                elif pnl_percentage > 2.0:  # Medium profit (2-5%)
                    trailing_stop_pct = 0.015  # Medium 1.5% trailing stop
                    self.logger.info(f"Using medium trailing stop (1.5%) for profitable position")
                elif pnl_percentage > 0.8:  # Small profit (0.8-2%)
                    trailing_stop_pct = 0.01  # Tighter 1% trailing stop
                    self.logger.info(f"Using tight trailing stop (1%) to protect small profit")
                
                # FASTER EXIT ON REVERSAL SIGNALS
                try:
                    df = self.k.get_ohlc_data(symbol, interval=5, since=time.time()-86400)[0]
                    if df is not None and len(df) > 20:
                        # Add more sophisticated trend reversal detection
                        short_ma = df['close'].rolling(5).mean().iloc[-1]
                        med_ma = df['close'].rolling(10).mean().iloc[-1]
                        
                        # If shorter MA crosses below medium MA and we're in profit, exit
                        if short_ma < med_ma and pnl_percentage > 0.3:  # Lowered threshold from 0.5% to 0.3%
                            self.logger.info(f"Trend reversal detected, taking profits at {pnl_percentage:.2f}%")
                            positions_to_close.append({
                                'symbol': symbol,
                                'reason': 'trend_reversal',
                                'price': current_price
                            })
                            continue
                except:
                    pass
                
                # Check take profit with dynamic target
                # Lower the take profit target from 2.5% to 1.8%
                take_profit_pct = 0.018  # 1.8% take profit
                
                if pnl_percentage >= take_profit_pct * 100:
                    self.logger.info(f"Take profit triggered for {symbol} at {pnl_percentage:.2f}%")
                    positions_to_close.append({
                        'symbol': symbol,
                        'reason': 'take_profit',
                        'price': current_price
                    })
                    continue
                
                # Check stop loss with dynamic adjustment
                if pnl_percentage <= -stop_loss_pct * 100:
                    self.logger.info(f"Stop loss triggered for {symbol} at {pnl_percentage:.2f}%")
                    positions_to_close.append({
                        'symbol': symbol,
                        'reason': 'stop_loss',
                        'price': current_price
                    })
                    continue
                
                # Check trailing stop (only in profit)
                if pnl_percentage > 0.8:  # Lowered from 1.0% to 0.8%
                    highest_price = position['high_price']
                    trailing_stop_price = highest_price * (1 - trailing_stop_pct)
                    
                    if current_price < trailing_stop_price:
                        self.logger.info(f"Trailing stop triggered for {symbol} at ${current_price:.8f}")
                        positions_to_close.append({
                            'symbol': symbol,
                            'reason': 'trailing_stop',
                            'price': current_price
                        })
                        continue
                
                # Time-based exit - much faster (12h vs 24h)
                if position_age > 12 and pnl_percentage < 0:  # Reduced from 24h to 12h
                    self.logger.info(f"Time-based exit for losing position {symbol} after {position_age:.1f} hours")
                    positions_to_close.append({
                        'symbol': symbol,
                        'reason': 'time_exit',
                        'price': current_price
                    })
                    continue
                
                # Maximum drawdown protection (unchanged)
                if pnl_percentage <= -self.max_drawdown * 100:
                    self.logger.info(f"Maximum drawdown triggered for {symbol} at {pnl_percentage:.2f}%")
                    positions_to_close.append({
                        'symbol': symbol,
                        'reason': 'max_drawdown',
                        'price': current_price
                    })
                    continue
                    
            # Close positions that triggered exit conditions
            for close_order in positions_to_close:
                symbol = close_order['symbol']
                self.execute_trade_demo(
                    symbol=symbol,
                    signal={'action': 'sell', 'confidence': 1.0},
                    price=close_order['price']
                )
                
            # Update portfolio history
            total_equity = self.calculate_total_equity()
            self.portfolio_history.append({
                'timestamp': current_time,
                'balance': self.demo_balance['ZUSD'],
                'equity': total_equity
            })
            
            return True
        except Exception as e:
            self.logger.error(f"Error in demo position monitoring: {str(e)}")
            return False
            
    def init_database(self):  # Changed method name to avoid conflict
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
        
            # Create tables
            c.execute('''CREATE TABLE IF NOT EXISTS demo_balance
                        (currency TEXT PRIMARY KEY, amount REAL)''')
                        
            c.execute('''CREATE TABLE IF NOT EXISTS demo_positions
                        (symbol TEXT PRIMARY KEY, volume REAL, entry_price REAL, 
                        entry_time TEXT, high_price REAL)''')
                        
            c.execute('''CREATE TABLE IF NOT EXISTS demo_trade_history
                        (timestamp TEXT, symbol TEXT, type TEXT, price REAL,
                        quantity REAL, value REAL, balance_after REAL)''')
                        
            c.execute('''CREATE TABLE IF NOT EXISTS demo_portfolio_history
                        (timestamp TEXT, balance REAL, equity REAL)''')
        
            # Initialize demo balance if empty
            c.execute('SELECT COUNT(*) FROM demo_balance')
            if c.fetchone()[0] == 0:
                c.execute('INSERT INTO demo_balance VALUES (?, ?)',
                         ('ZUSD', self.demo_balance['ZUSD']))
        
            conn.commit()
            conn.close()
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise  # Re-raise to handle in __init__
        
    def load_demo_state(self) -> None:
        """Load demo bot state from database"""
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
        
            # Create tables if they don't exist
            c.execute('''CREATE TABLE IF NOT EXISTS demo_balance
                        (currency TEXT PRIMARY KEY, amount REAL)''')
                        
            c.execute('''CREATE TABLE IF NOT EXISTS demo_positions
                        (symbol TEXT PRIMARY KEY, volume REAL, entry_price REAL, 
                        entry_time TEXT, high_price REAL)''')
                        
            c.execute('''CREATE TABLE IF NOT EXISTS demo_trade_history
                        (timestamp TEXT, symbol TEXT, type TEXT, price REAL,
                        quantity REAL, value REAL, balance_after REAL)''')
                        
            c.execute('''CREATE TABLE IF NOT EXISTS demo_portfolio_history
                        (timestamp TEXT, balance REAL, equity REAL)''')
        
            # Load balance data
            c.execute('SELECT * FROM demo_balance')
            balance_data = c.fetchall()
            if balance_data:
                self.demo_balance = {row[0]: row[1] for row in balance_data}
        
            # Load positions
            c.execute('SELECT * FROM demo_positions')
            position_data = c.fetchall()
            if position_data:
                self.demo_positions = {}
                for row in position_data:
                    self.demo_positions[row[0]] = {
                        'volume': row[1],
                        'entry_price': row[2],
                        'entry_time': datetime.fromisoformat(row[3]),
                        'high_price': row[4]
                    }
        
            # Load trade history
            c.execute('SELECT * FROM demo_trade_history')
            trade_data = c.fetchall()
            if trade_data:
                self.trade_history = []
                for row in trade_data:
                    self.trade_history.append({
                        'timestamp': datetime.fromisoformat(row[0]),
                        'symbol': row[1],
                        'type': row[2],
                        'price': row[3],
                        'quantity': row[4],
                        'value': row[5],
                        'balance_after': row[6]
                    })
        
            # Load portfolio history
            c.execute('SELECT * FROM demo_portfolio_history ORDER BY timestamp DESC LIMIT 100')
            portfolio_data = c.fetchall()
            if portfolio_data:
                self.portfolio_history = []
                for row in portfolio_data:
                    self.portfolio_history.append({
                        'timestamp': datetime.fromisoformat(row[0]),
                        'balance': row[1],
                        'equity': row[2]
                    })
        
            conn.close()
            self.logger.info("Demo state loaded successfully")
            
            # Log current state
            self.logger.info("\n=== Loaded Demo State ===")
            self.logger.info(f"USD Balance: ${self.demo_balance['ZUSD']:.2f}")
            self.logger.info(f"Active Positions: {len(self.demo_positions)}")
            self.logger.info(f"Trade History: {len(self.trade_history)} trades")
            self.logger.info(f"Portfolio History: {len(self.portfolio_history)} entries")
        
        except Exception as e:
            self.logger.error(f"Error loading demo state: {str(e)}")
    
    def save_demo_state(self):
        """Save current demo state to database"""
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
        
            # Save current balance
            c.execute('DELETE FROM demo_balance')
            for currency, amount in self.demo_balance.items():
                c.execute('INSERT INTO demo_balance VALUES (?, ?)',
                         (currency, amount))
        
            # Save positions
            c.execute('DELETE FROM demo_positions')
            for symbol, pos in self.demo_positions.items():
                c.execute('INSERT INTO demo_positions VALUES (?, ?, ?, ?, ?)',
                         (symbol, pos['volume'], pos['entry_price'],
                          pos['entry_time'].isoformat(), pos['high_price']))
        
            # Save trade history
            c.execute('DELETE FROM demo_trade_history')
            for trade in self.trade_history:
                c.execute('''INSERT INTO demo_trade_history 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (trade['timestamp'].isoformat(), trade['symbol'],
                          trade['type'], trade['price'], trade['quantity'],
                          trade['value'], trade['balance_after']))
        
            # Save portfolio history
            c.execute('DELETE FROM demo_portfolio_history')
            for entry in self.portfolio_history:
                c.execute('INSERT INTO demo_portfolio_history VALUES (?, ?, ?)',
                         (entry['timestamp'].isoformat(), entry['balance'],
                          entry['equity']))
        
            conn.commit()
            conn.close()
            self.logger.info("Demo state saved successfully")
        
        except Exception as e:
            self.logger.error(f"Error saving demo state: {str(e)}")

    async def run(self):
        """Main run loop for demo trading bot"""
        cleanup_interval = 3600  # Cleanup every hour
        last_cleanup = time.time()
        cycle_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            self.logger.info("\n=== DEMO KRAKEN TRADING BOT STARTED ===")
            self.logger.info(f"Starting Balance: ${self.demo_balance['ZUSD']:.2f}")
            self.logger.info("Trading Pairs:")
            for symbol, allocation in self.symbols.items():
                self.logger.info(f"  {symbol}: {allocation*100:.1f}% allocation")
            
            # Initialize rate limiter
            rate_limiter = DemoRateLimiter()
            
            # Initial data collection and model training
            self.logger.info("\nInitial Setup Phase:")
            if not self.training_completed:
                self.logger.info("Starting initial model training...")
                training_success = await self.perform_initial_training()
                if not training_success:
                    self.logger.error("Initial training failed!")
                    return
                self.logger.info("Initial training completed successfully!")
                self.training_completed = True
                self.is_initially_trained = True
            
            # Initialize position tracking
            self.logger.info("Initializing position tracking...")
            await self.initialize_position_tracking()
            
            self.logger.info("\nStarting main trading loop...")
            while self.running:
                try:
                    cycle_count += 1
                    current_time = time.time()
                    self.logger.info(f"\n=== Trading Cycle {cycle_count} ===")
                    self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Reset balance if needed
                    self.check_and_reset_balance()
                    
                    # Check if cleanup is needed
                    if current_time - last_cleanup > cleanup_interval:
                        self.logger.info("Performing routine cleanup...")
                        self.cleanup_old_data()
                        last_cleanup = current_time
                    
                    # Update portfolio status
                    metrics = self.get_portfolio_metrics()
                    self.logger.info("\nPortfolio Status:")
                    self.logger.info(f"Current Equity: ${metrics['current_equity']:.2f}")
                    self.logger.info(f"P&L: ${metrics['total_pnl']:.2f} ({metrics['pnl_percentage']:.2f}%)")
                    
                    # Save current state
                    self.save_demo_state()
                    
                    # Process each trading pair
                    for symbol in self.symbols:
                        await rate_limiter.wait()
                        try:
                            self.logger.info(f"\nAnalyzing {symbol}:")
                            
                            # Get market data
                            df = await self.get_historical_data(symbol)
                            if df is not None and not df.empty:
                                # Calculate indicators and generate signals
                                df = self.calculate_indicators(df)
                                signal = self.generate_enhanced_signals(df, symbol)
                                
                                # Get current price and position info
                                current_price = df['close'].iloc[-1]
                                in_position = symbol in self.demo_positions
                                
                                self.logger.info(f"Current Price: ${self.format_price_for_log(symbol, current_price)}")
                                self.logger.info(f"Position: {'Yes' if in_position else 'No'}")
                                self.logger.info(f"Signal: {signal['action'].upper()} (Confidence: {signal['confidence']:.3f})")
                                
                                if signal['action'] != 'hold':
                                    if self.check_market_conditions(symbol, df):
                                        position_size = self.calculate_position_size(symbol, signal)
                                        if position_size >= self.min_position_value:
                                            self.logger.info(f"Executing {signal['action'].upper()} order:")
                                            self.logger.info(f"Position Size: ${position_size:.2f}")
                                            
                                            trade_result = self.execute_trade_demo(
                                                symbol, signal, current_price
                                            )
                                            
                                            if trade_result:
                                                self.logger.info("Trade executed successfully")
                                                self.save_demo_state()
                                            else:
                                                self.logger.warning("Trade execution failed")
                                        else:
                                            self.logger.info(f"Position size ${position_size:.2f} below minimum ${self.min_position_value}")
                                    else:
                                        self.logger.info("Market conditions not suitable for trading")
                                else:
                                    self.logger.info("No action needed")
                                    
                        except Exception as e:
                            self.logger.error(f"Error processing {symbol}: {str(e)}")
                            continue
                    
                    
                    # Monitor positions
                    self.logger.info("\nMonitoring existing positions...")
                    if len(self.demo_positions) > 0:
                        # Use special demo handler instead of API-based monitoring
                        self.handle_demo_position_monitoring()
                    else:
                        self.logger.info("No positions to monitor")
                    
                    # Reset consecutive errors on successful cycle
                    consecutive_errors = 0
                    
                    # Wait for next cycle
                    self.logger.info("\nWaiting for next cycle (150 seconds)...")
                    await asyncio.sleep(150)
                    
                except Exception as e:
                    consecutive_errors += 1
                    self.logger.error(f"Error in main loop: {str(e)}")
                    
                    # Implement circuit breaker pattern
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.critical(f"Too many consecutive errors ({consecutive_errors}). Pausing for 5 minutes.")
                        await asyncio.sleep(300)  # 5 minute cooling off period
                        consecutive_errors = 0  # Reset after cooling off
                    else:
                        await asyncio.sleep(5)
                        
        except Exception as e:
            self.logger.error(f"Fatal error in bot run loop: {str(e)}")
            traceback.print_exc()

async def main():
    # Initialize and run the bot
    bot = DemoKrakenBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\nStopping bot gracefully...")
        bot.running = False
    except Exception as e:
        print(f"Bot stopped due to error: {str(e)}")

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
