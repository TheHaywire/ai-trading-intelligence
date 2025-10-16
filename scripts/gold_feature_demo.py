#!/usr/bin/env python3
"""
GOLD (XAUUSD) Feature Demonstration
Demonstrates quantitative features using existing MT5 broker infrastructure.
"""

import logging
import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker
from src.core.symbols import get_registry
from src.strategy.ema_trend import EMATrendStrategy
from src.strategy.loader import MarketState


def calculate_momentum_features(bars: List[Dict], windows: List[int] = [5, 10, 20]) -> Dict[str, float]:
    """Calculate momentum features."""
    closes = np.array([bar["close"] for bar in bars])
    features = {}
    
    for window in windows:
        if len(closes) > window:
            # Rate of Change
            roc = (closes[-1] / closes[-window-1]) - 1
            features[f"roc_{window}"] = roc
            
            # Price acceleration (momentum of momentum)
            if window >= 10:
                momentum = closes[-1] - closes[-5]
                prev_momentum = closes[-window//2] - closes[-window//2-5]
                features[f"accel_{window}"] = momentum - prev_momentum
    
    return features


def calculate_mean_reversion_features(bars: List[Dict], window: int = 20) -> Dict[str, float]:
    """Calculate mean reversion features."""
    closes = np.array([bar["close"] for bar in bars])
    features = {}
    
    if len(closes) < window:
        return features
    
    # Bollinger Band Percentile
    window_closes = closes[-window:]
    mean_price = np.mean(window_closes)
    std_price = np.std(window_closes)
    
    if std_price > 0:
        upper_band = mean_price + (2.0 * std_price)
        lower_band = mean_price - (2.0 * std_price)
        band_range = upper_band - lower_band
        
        if band_range > 0:
            bb_percentile = (closes[-1] - lower_band) / band_range
            features["bb_percentile"] = bb_percentile
    
    # Price Z-Score
    z_score = (closes[-1] - mean_price) / std_price if std_price > 0 else 0
    features["price_zscore"] = z_score
    
    # RSI Percentile (simplified calculation)
    deltas = np.diff(closes[-14:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0
    
    if avg_loss > 0:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        features["rsi"] = rsi
    
    return features


def calculate_volatility_features(bars: List[Dict], window: int = 20) -> Dict[str, float]:
    """Calculate volatility features."""
    closes = np.array([bar["close"] for bar in bars])
    features = {}
    
    if len(closes) < window:
        return features
    
    # Historical Volatility
    returns = np.diff(np.log(closes[-window:]))
    hv = np.std(returns) * np.sqrt(252)  # Annualized for daily data
    features[f"historical_vol_{window}"] = hv
    
    # Volatility Regime (simplified)
    rolling_vols = []
    for i in range(window, len(closes)):
        period_returns = np.diff(np.log(closes[i-window:i]))
        period_vol = np.std(period_returns)
        rolling_vols.append(period_vol)
    
    if len(rolling_vols) >= 10:
        vol_mean = np.mean(rolling_vols[-10:])
        current_vol = rolling_vols[-1] if rolling_vols else 0
        vol_percentile = (current_vol / vol_mean) - 1 if vol_mean > 0 else 0
        features["vol_regime"] = vol_percentile
    
    return features


def run_gold_demo():
    """Run GOLD feature demonstration."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize broker in paper mode for demo
    broker = MT5Broker(
        login="demo", 
        password="demo",
        server="demo",
        paper_mode=True  # Paper mode for demonstration
    )
    
    # Get symbol info
    registry = get_registry()
    gold_info = registry.get("XAUUSD")
    
    if not gold_info:
        logger.error("XAUUSD not found in registry")
        return
    
    logger.info(f"=== GOLD (XAUUSD) Feature Analysis ===")
    logger.info(f"Contract Size: {gold_info.contract_size}")
    logger.info(f"Pip Size: {gold_info.pip_size}")
    logger.info(f"Description: {gold_info.description}")
    logger.info(f"Asset Class: {gold_info.asset_class}")
    
    # Connect to broker
    try:
        broker.connect()
        logger.info("Connected to broker (paper mode)")
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return
    
    # Fetch historical data
    logger.info("Fetching historical data...")
    
    bars_h1 = broker.get_bars("XAUUSD", "H1", count=300) or []
    bars_h4 = broker.get_bars("XAUUSD", "H4", count=300) or []
    bars_d1 = broker.get_bars("XAUUSD", "D1", count=100) or []
    
    logger.info(f"H1 bars: {len(bars_h1)}")
    logger.info(f"H4 bars: {len(bars_h4)}")
    logger.info(f"D1 bars: {len(bars_d1)}")
    
    if len(bars_h1) == 0:
        logger.warning("No H1 data available")
        return
    
    # Calculate features
    logger.info("\n=== QUANTITATIVE FEATURES ===")
    
    # Momentum Features
    mtm_h1 = calculate_momentum_features(bars_h1)
    mtm_h4 = calculate_momentum_features(bars_h4)
    
    logger.info("Momentum Features (H1):")
    for key, value in mtm_h1.items():
        logger.info(f"  {key}: {value:.4f}")
    
    logger.info("Momentum Features (H4):")
    for key, value in mtm_h4.items():
        logger.info(f"  {key}: {value:.4f}")
    
    # Mean Reversion Features
    mr_h1 = calculate_mean_reversion_features(bars_h1)
    mr_h4 = calculate_mean_reversion_features(bars_h4)
    
    logger.info("\nMean Reversion Features (H1):")
    for key, value in mr_h1.items():
        logger.info(f"  {key}: {value:.4f}")
    
    logger.info("Mean Reversion Features (H4):")
    for key, value in mr_h4.items():
        logger.info(f"  {key}: {value:.4f}")
    
    # Volatility Features
    vol_h1 = calculate_volatility_features(bars_h1)
    vol_h4 = calculate_volatility_features(bars_h4)
    
    logger.info("\nVolatility Features (H1):")
    for key, value in vol_h1.items():
        logger.info(f"  {key}: {value:.4f}")
    
    logger.info("Volatility Features (H4):")
    for key, value in vol_h4.items():
        logger.info(f"  {key}: {value:.4f}")
    
    # Strategy Signal Generation
    logger.info("\n=== STRATEGY SIGNALS ===")
    
    # Create market state
    tick = broker.get_tick("XAUUSD")
    if tick:
        market_state = MarketState(
            symbol="XAUUSD",
            timestamp=tick.time,
            bid=tick.bid,
            ask=tick.ask,
            bars_h1=bars_h1,
            bars_h4=bars_h4,
            bars_d1=bars_d1,
            symbol_info=gold_info,
        )
        
        # Run EMA Trend Strategy
        ema_strategy = EMATrendStrategy("ema_trend", {"enabled": True})
        signal = ema_strategy.analyze(market_state)
        
        if signal:
            logger.info("🎯 EMA TREND SIGNAL:")
            logger.info(f"  Direction: {signal.direction.value}")
            logger.info(f"  Entry: {signal.entry_price:.2f}")
            logger.info(f"  Stop Loss: {signal.stop_loss:.2f}")
            logger.info(f"  Take Profit: {signal.take_profit:.2f}")
            logger.info(f"  Volume: {signal.volume:.2f}")
            logger.info(f"  Reason: {signal.reason}")
            logger.info(f"  Confidence: {signal.confidence:.2f}")
            logger.info(f"  Metadata: {signal.metadata}")
        else:
            logger.info("❌ No EMA trend signal")
    
    # Feature Summary
    logger.info("\n=== FEATURE SUMMARY ===")
    all_features = {**mtm_h1, **mtm_h4, **mr_h1, **mr_h4, **vol_h1, **vol_h4}
    
    for feat_type in ["momentum", "mean_revert", "volatility"]:
        feat_keys = [k for k in all_features.keys() if feat_type.replace("mean_revert", "bb") in k or feat_type.replace("mean_revert", "rsi") in k or feat_type.replace("mean_revert", "zscore") in k]
        logger.info(f"\n{feat_type.replace('_', ' ').title()}:")
        for key in sorted(feat_keys):
            value = all_features.get(key, "N/A")
            logger.info(f"  {key}: {value}")
    
    # Current Price Analysis
    if bars_h1:
        current_price = bars_h1[-1]["close"]
        prev_price = bars_h1[-2]["close"] if len(bars_h1) > 1 else current_price
        price_change = (current_price - prev_price) / prev_price * 100
        
        logger.info(f"\n=== CURRENT MARKET STATE ===")
        logger.info(f"Current Price: ${current_price:.2f}")
        logger.info(f"Change from prev bar: {price_change:.2f}%")
        logger.info(f"High: ${bars_h1[-1]['high']:.2f}")
        logger.info(f"Low: ${bars_h1[-1]['low']:.2f}")
        logger.info(f"Volume: {bars_h1[-1]['volume']}")
    
    broker.disconnect()
    logger.info("\n=== DEMO COMPLETE ===")


if __name__ == "__main__":
    run_gold_demo()
