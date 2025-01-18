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

class EnhancedKrakenCryptoBot:
    def __init__(self, api_key: str, secret_key: str):
        # Initialize logging first
        self.logger = self._setup_logging()

        try:
            # Initialize Kraken API with rate limiting
            self.kraken = krakenex.API(api_key, secret_key)
            self.k = KrakenAPI(self.kraken, retry=0.5)
            self.running = True

            # Add missing attributes
            self.is_initially_trained = False
            self.training_completed = False
            self.min_training_data = 100
            self.initial_training_hours = 1
            self.start_time = datetime.now()
            
            # Initialize MLModelManager and related attributes
            self.model_manager = MLModelManager()
            self.model_name = 'trading_model.joblib'
            self.db_name = 'crypto_trading.db'
            self.is_initially_trained = False
            self.training_completed = False

            self.ai_enhancer = AITradingEnhancer()
            self.ai_trained = False

            # Adjust market conditions for smaller account
            self.market_conditions = {
                'high_volatility': 0.05,    # Lower threshold
                'low_liquidity': 1000,      # Lower requirement
                'excessive_spread': 0.03     # Lower threshold
            }

            # Verify connection and get account info
            account = self.k.get_account_balance()
            self.logger.info(f"Successfully connected to Kraken trading")
            self.logger.info(f"Current account balance: {account}")

            # Trading pairs with adjusted allocations for small account
            self.symbols = {
            "SOLUSD": 0.20,    # SOL/USD
            "AVAXUSD": 0.20,   # AVAX/USD
            "XRPUSD": 0.20,    # XRP/USD
            "XDGUSD": 0.15,    # DOGE/USD
            "SHIBUSD": 0.10,   # SHIB/USD
            "PEPEUSD": 0.15    # PEPE/USD
            }


            # Adjust parameters for smaller account
            self.max_drawdown = 0.10        # Reduced from 0.15
            self.trailing_stop_pct = 0.03   # Tighter stop
            self.max_trades_per_hour = 3    # Fewer trades
            self.trade_cooldown = 300       # Longer cooldown
            self.last_trade_time = {}
            self.trade_history = {}
            self.performance_metrics = {}

            # Technical indicators
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

            self.timeframe = 5  # 1 minute intervals

            # Adjust risk parameters for smaller account
            self.max_position_size = 0.3    # Increased to allow meaningful positions
            self.min_position_value = 2.0    # Reduced minimum
            self.max_total_risk = 0.15       # Reduced risk
            self.stop_loss_pct = 0.03        # Tighter stop loss
            self.take_profit_pct = 0.05      # Lower but realistic profit target

            self.min_zusd_balance = 5.0

            # Rate limiting
            self.last_api_call = time.time()
            self.api_call_delay = 1.0
            self.api_retry_delay = 1  # Initial retry delay for exceeded rate limits
            self.max_retry_delay = 60

            self.market_state = {symbol: {'trend': None, 'volatility': None} for symbol in self.symbols}
            self.logger.info("Kraken trading bot initialization completed successfully")

        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            raise

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
        """Fetch and preprocess historical data"""
        try:
            await self.wait_for_api()
            
            since = time.time() - (lookback_days * 24 * 60 * 60)
            ohlc, last = self.k.get_ohlc_data(symbol, interval=self.timeframe, since=since)
            
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

    def generate_enhanced_signals(self, df: pd.DataFrame, symbol: str) -> dict:
        """Generate trading signals with core confidence values only"""
        try:
            if len(df) < self.sma_long:
                return {'action': 'hold', 'confidence': 0.5}

            df = self.calculate_advanced_indicators(df)
            
            # Get ML prediction (35% weight)
            ml_confidence = 0.5
            if self.is_initially_trained:
                features = self.model_manager.prepare_features(df)
                ml_signal = self.model_manager.predict(features)
                ml_confidence = ml_signal['confidence']

            # Get AI prediction (25% weight)
            ai_confidence = 0.5
            if self.ai_trained:
                ai_signal = self.ai_enhancer.predict_next_movement(df)
                ai_confidence = ai_signal['confidence']

            # Technical analysis (40% weight)
            tech_confidence = 0.5
            market_state = self.analyze_market_state(df)
            last_row = df.iloc[-1]

            # Calculate technical signals
            if market_state['trend'] > 0 and market_state['volume_trend'] > 0:
                tech_confidence += 0.02
            elif market_state['trend'] < 0 and market_state['volume_trend'] < 0:
                tech_confidence -= 0.02

            if all(x in last_row for x in ['macd', 'macd_signal']):
                macd_strength = abs(last_row['macd'] - last_row['macd_signal']) / abs(last_row['macd_signal'])
                volume_boost = min(1.5, last_row.get('volume_ma_ratio', 1))
                volatility = df['close'].pct_change().rolling(20).std().iloc[-1]
                volatility_factor = min(1.0, max(0.5, 1.0 - volatility * 10))
                macd_impact = 0.02 * macd_strength * volume_boost * volatility_factor
                
                if last_row['macd'] > last_row['macd_signal']:
                    tech_confidence += macd_impact
                else:
                    tech_confidence -= macd_impact

            final_confidence = 0.5 + (
                (ml_confidence - 0.5) * 0.25 +
                (ai_confidence - 0.5) * 0.35 +
                (tech_confidence - 0.5) * 0.40
            ) * volatility_factor

            final_confidence = max(0.45, min(0.55, final_confidence))
                
            if final_confidence < 0.47:
                action = 'sell'
            elif final_confidence > 0.52:
                action = 'buy'
            else:
                action = 'hold'

            # Determine signal icon
            if final_confidence < 0.47:
                icon = "🔴"
            elif final_confidence > 0.52:
                icon = "🟢"
            else:
                icon = "⚪"

            # Log only the core confidences
            self.logger.info(f"{symbol}: ML:{ml_confidence:.3f} AI:{ai_confidence:.3f} TECH:{tech_confidence:.3f} => {icon}{final_confidence:.3f}")
            
            return {'action': action, 'confidence': final_confidence}

        except Exception as e:
            self.logger.error(f"Error generating signals: {str(e)}")
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

    async def execute_trade_with_risk_management(self, symbol: str, signal: dict, price: float):
        """Enhanced trade execution with better validation and error handling"""
        try:
            await self.wait_for_api()
            
            # Validate price
            if not price or price <= 0:
                self.logger.error(f"Invalid price for {symbol}: {price}")
                return None
            
            # Get current balance and positions
            balance = self.k.get_account_balance()
            positions = self.k.get_open_positions()
            
            if isinstance(balance, pd.DataFrame):
                balance_dict = balance.to_dict()['vol']
            else:
                balance_dict = balance

            total_usd_balance = float(balance_dict.get('ZUSD', 0))
            self.logger.info(f"Available USD balance: ${total_usd_balance}")

            # SELL LOGIC
            if signal['action'] == 'sell':
                current_position = next(
                    (pos for pos in positions 
                    if self.normalize_symbol(pos['pair']) == self.normalize_symbol(symbol)),
                    None
                )

                if current_position:
                    try:
                        position_size = float(current_position['vol'])
                        min_requirements = self.get_minimum_order_requirements(symbol)
                        
                        if position_size < min_requirements['min_vol']:
                            self.logger.warning(f"Position size {position_size} below minimum {min_requirements['min_vol']}")
                            return None
                            
                        formatted_qty = self.format_order_quantity(symbol, position_size)
                        
                        order_params = {
                            'pair': symbol,
                            'type': 'sell',
                            'ordertype': 'market',
                            'volume': formatted_qty
                        }
                        
                        self.logger.info(f"Executing sell order: {order_params}")
                        response = self.k.add_standard_order(**order_params)
                        
                        if response and 'error' not in response:
                            self.position_tracker.positions.pop(symbol, None)
                            return response
                        else:
                            self.logger.error(f"Error in sell order: {response.get('error') if response else 'No response'}")
                            
                    except Exception as e:
                        self.logger.error(f"Error executing sell: {str(e)}")
                        return None
                else:
                    self.logger.warning(f"No position found for {symbol} (normalized: {self.normalize_symbol(symbol)})")
                    return None

            # BUY LOGIC
            elif signal['action'] == 'buy':
                try:
                    min_requirements = self.get_minimum_order_requirements(symbol)
                    min_volume = min_requirements['min_vol']
                    min_cost = min_volume * price
                    max_possible_position = total_usd_balance * self.max_position_size

                    # First check if we can afford minimum volume
                    if min_cost > max_possible_position:
                        self.logger.warning(f"Cannot afford minimum volume for {symbol}. Needs ${min_cost:.2f}, max allowed ${max_possible_position:.2f}")
                        return None

                    # If we can afford minimum, calculate actual position size
                    position_size = self.calculate_position_size(symbol, signal)
                    qty = position_size / price

                    # Always ensure we meet minimum volume
                    if qty < min_volume:
                        qty = min_volume
                        position_size = qty * price
                        self.logger.info(f"Adjusted order to minimum volume: {qty} {symbol} (${position_size:.2f})")

                    formatted_qty = self.format_order_quantity(symbol, qty)
                    
                    order_params = {
                        'pair': symbol,
                        'type': 'buy',
                        'ordertype': 'market',
                        'volume': formatted_qty
                    }
                    
                    self.logger.info(f"Executing buy order: {order_params}")
                    response = self.k.add_standard_order(**order_params)
                    
                    if response and 'error' not in response:
                        self.position_tracker.update_position(symbol, qty, price)
                        return response
                    else:
                        self.logger.error(f"Error in buy order: {response.get('error') if response else 'No response'}")
                            
                except Exception as e:
                    self.logger.error(f"Error executing buy: {str(e)}")
                    return None

            return None

        except Exception as e:
            self.logger.error(f"Trade execution error: {str(e)}")
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
        """Monitor and manage open positions"""
        try:
            for symbol in self.position_tracker.positions:
                # Get current price
                current_price = self.get_latest_price(symbol)
                position_info = self.position_tracker.update_price(symbol, current_price)
                
                if position_info:
                    self.logger.info(f"\nPosition Update - {symbol}:")
                    self.logger.info(f"Quantity: {position_info['quantity']}")
                    self.logger.info(f"Entry: ${position_info['entry_price']:.4f}")
                    self.logger.info(f"Current: ${position_info['current_price']:.4f}")
                    self.logger.info(f"P&L: {position_info['pnl_pct']:.2f}%")
                    
                    # Check for take profit
                    if position_info['pnl_pct'] >= self.take_profit_pct * 100:
                        self.logger.info(f"Take profit triggered for {symbol}")
                        await self.execute_trade_with_risk_management(
                            symbol, 
                            {'action': 'sell', 'confidence': 1.0}, 
                            current_price
                        )
                    
                    # Check for stop loss
                    elif position_info['pnl_pct'] <= -self.max_drawdown * 100:
                        self.logger.info(f"Stop loss triggered for {symbol}")
                        await self.execute_trade_with_risk_management(
                            symbol, 
                            {'action': 'sell', 'confidence': 1.0}, 
                            current_price
                        )
                    
                    # Check trailing stop
                    elif position_info['pnl_pct'] > 0:
                        trailing_stop_price = position_info['high_price'] * (1 - self.trailing_stop_pct)
                        if current_price < trailing_stop_price:
                            self.logger.info(f"Trailing stop triggered for {symbol}")
                            await self.execute_trade_with_risk_management(
                                symbol, 
                                {'action': 'sell', 'confidence': 1.0}, 
                                current_price
                            )
                            
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {str(e)}")

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
            price = self.get_latest_price(symbol)
            if price is None or price <= 0:
                self.logger.error("Invalid price")
                return 0
                
            balance = self.k.get_account_balance()
            balance_dict = balance.to_dict()['vol'] if isinstance(balance, pd.DataFrame) else balance
            total_usd_balance = float(balance_dict.get('ZUSD', 0))
            
            if total_usd_balance < self.min_zusd_balance:
                self.logger.warning(f"Balance ${total_usd_balance} below minimum ${self.min_zusd_balance}")
                return 0
                
            allocation = self.symbols[symbol]
            position_size = min(
                total_usd_balance * allocation,
                total_usd_balance * self.max_position_size
            )
            
            # Ensure minimum position size
            if position_size < self.min_position_value:
                self.logger.warning(f"Position size ${position_size:.2f} below minimum ${self.min_position_value}")
                return 0
                
            return position_size
            
        except Exception as e:
            self.logger.error(f"Position size calculation error: {str(e)}")
            return 0
        
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
                # Try OHLC first
                ohlc = self.k.get_ohlc_data(symbol, interval=1)[0]
                if ohlc is not None and not ohlc.empty:
                    price = float(ohlc.iloc[-1]['close'])
                    if price > 0:
                        return round(price, precision)
                        
                # Fallback to trades
                trades = self.k.get_recent_trades(symbol)[0]
                if trades is not None and not trades.empty:
                    price = float(trades.iloc[0]['price'])
                    if price > 0:
                        return round(price, precision)

                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying price fetch for {symbol}")
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"Price fetch attempt {attempt+1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        self.logger.error(f"Failed to get price for {symbol}")
        return None

    async def initialize_position_tracking(self):
        """Initialize position tracking with proper async handling"""
        try:
            positions = self.k.get_open_positions()
            for pos in positions:
                symbol = pos['pair']
                qty = float(pos['vol'])
                price = float(pos['cost'])
                self.position_tracker.update_position(symbol, qty, price)
                self.logger.info(f"Loaded existing position: {symbol}, Quantity: {qty}, Entry: ${price}")
            return True
        except Exception as e:
            self.logger.error(f"Error loading positions: {str(e)}")
            return False

    async def monitor_positions(self):
        """Monitor positions with proper validation"""
        try:
            positions = self.k.get_open_positions()
            
            # Reset position tracker if no positions exist
            if not positions or len(positions) == 0:
                self.position_tracker.positions = {}
                return
                
            for pos in positions:
                # Validate position data
                if not all(k in pos for k in ['pair', 'vol', 'price', 'cost']):
                    continue
                    
                if float(pos['vol']) <= 0:
                    continue
                    
                symbol = pos['pair']
                qty = float(pos['vol'])
                price = float(pos['cost']) / qty
                
                current_price = self.get_latest_price(symbol)
                if current_price:
                    pnl = ((current_price - price) / price) * 100
                    self.logger.info(f"\nPosition Update - {symbol}:")
                    self.logger.info(f"Quantity: {qty}")
                    self.logger.info(f"Entry: ${price:.4f}")
                    self.logger.info(f"Current: ${current_price:.4f}")
                    self.logger.info(f"P&L: {pnl:.2f}%")
                    
                await asyncio.sleep(1)  # Rate limiting
                
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {str(e)}")
            self.position_tracker.positions = {}  # Reset on error

    async def run(self):
        self.logger.info("\n=== KRAKEN TRADING BOT STARTED ===")
        
        # Force initial training
        if not self.training_completed:
            self.logger.info("Performing initial model training...")
            training_success = await self.perform_initial_training()
            if not training_success:
                self.logger.error("Initial training failed!")
                return
            else:
                self.logger.info("Initial training completed successfully!")

        # Initialize position tracking
        self.position_tracker = PositionTracker()
        await self.initialize_position_tracking()

        while self.running:
            try:
                # Get and display account balance at start of cycle
                balance_info = self.get_account_balance()
                
                # First monitor existing positions
                await self.monitor_positions()
                
                # Then process new trading opportunities
                for symbol in self.symbols:
                    df = await self.get_historical_data(symbol)
                    
                    if not df.empty:
                        df = self.calculate_indicators(df)
                        signal = self.generate_enhanced_signals(df, symbol)
                        
                        self.logger.info(f"\n--- Processing {symbol} ---")
                        
                        if signal['action'] != 'hold':
                            price = df['close'].iloc[-1]
                            position_size = self.calculate_position_size(symbol, signal)
                            
                            self.logger.info(f"Signal Generated:")
                            self.logger.info(f"Action: {signal['action']}")
                            self.logger.info(f"Confidence: {signal['confidence']:.2f}")
                            self.logger.info(f"Price: ${price:.4f}")
                            self.logger.info(f"Position Size: ${position_size:.2f}")
                            
                            if position_size >= self.min_position_value:
                                self.logger.info(f"Executing trade for {symbol}...")
                                trade_result = await self.execute_trade_with_risk_management(
                                    symbol, signal, price
                                )
                                if trade_result:
                                    self.logger.info(f"Trade executed successfully: {trade_result}")
                                else:
                                    self.logger.warning(f"Trade execution failed for {symbol}")
                            else:
                                self.logger.warning(f"Position size ${position_size:.2f} below minimum ${self.min_position_value}")

                # Sleep for 150 seconds before next cycle
                await asyncio.sleep(150)
                    
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(5)

async def main():
    # Initialize and run the bot
    api_key = "P6J5R5pPLXjRGiqgL/4j9ZNGN4bormuJEDTnvsT/NTk/uzQITcsLFiFa"
    secret_key = "FqCqZqTC+HWQ2b24BCWb24hnLieqDunV+4QgGR1098SrOEgXqRd6Yq/3Ih8bU9aussbBRBbhMQeVSUroFRX+PA=="
    
    bot = EnhancedKrakenCryptoBot(api_key, secret_key)
    
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