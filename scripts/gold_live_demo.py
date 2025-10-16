#!/usr/bin/env python3
"""
GOLD (XAUUSD) Live Feature Demonstration
Connects to real MT5 terminal and demonstrates quantitative features.
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
from src.strategy.mean_reversion_bands import MeanReversionBandsStrategy
from src.strategy.breakout_session_open import BreakoutSessionOpenStrategy
from src.strategy.loader import MarketState


def calculate_quant_features(bars: List[Dict], symbol_info, label: str = "") -> Dict[str, float]:
    """Calculate comprehensive quantitative features."""
    closes = np.array([bar["close"] for bar in bars])
    features = {}
    
    if len(closes) < 10:
        return features
    
    # Momentum Features
    for window in [5, 10, 20]:
        if len(closes) > window:
            # Rate of Change
            roc = (closes[-1] / closes[-window-1]) - 1
            features[f"{label}_roc_{window}"] = roc
            
            # Momentum (price change over window)
            momentum = closes[-1] - closes[-window]
            features[f"{label}_momentum_{window}"] = momentum
    
    # Mean Reversion Features
    if len(closes) >= 20:
        window_closes = closes[-20:]
        mean_price = np.mean(window_closes)
        std_price = np.std(window_closes)
        
        if std_price > 0:
            # Bollinger Band Percentile
            upper_band = mean_price + (2.0 * std_price)
            lower_band = mean_price - (2.0 * std_price)
            band_range = upper_band - lower_band
            
            if band_range > 0:
                bb_percentile = (closes[-1] - lower_band) / band_range
                features[f"{label}_bb_percentile"] = bb_percentile
            
            # Price Z-Score
            z_score = (closes[-1] - mean_price) / std_price
            features[f"{label}_price_zscore"] = z_score
    
    # RSI calculation
    if len(closes) >= 14:
        deltas = np.diff(closes[-14:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
            features[f"{label}_rsi"] = rsi
    
    # Volatility Features
    if len(closes) >= 20:
        returns = np.diff(np.log(closes[-20:]))
        hv = np.std(returns)
        features[f"{label}_volatility"] = hv
        
        # Volatility vs Historical (percentile)
        rolling_vols = []
        for i in range(20, min(len(closes), 60)):
            period_returns = np.diff(np.log(closes[i-20:i]))
            period_vol = np.std(period_returns)
            rolling_vols.append(period_vol)
        
        if len(rolling_vols) >= 5:
            vol_median = np.median(rolling_vols)
            vol_percentile = hv / vol_median if vol_median > 0 else 1.0
            features[f"{label}_vol_percentile"] = vol_percentile
    
    # Trend Signal
    if len(closes) >= 50:
        ema_20 = np.mean(closes[-20:])  # Simplified EMA
        ema_50 = np.mean(closes[-50:])
        features[f"{label}_trend_signal"] = 1.0 if ema_20 > ema_50 else -1.0
    
    return features


def run_live_gold_analysis():
    """Run live GOLD analysis with real MT5 data."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Use actual MT5 credentials from config
    broker = MT5Broker(
        login="165835373", 
        password="Manan@123!!",
        server="XMGlobal-MT5 2",
        paper_mode=False  # Real connection
    )
    
    logger.info("=== GOLD (XAUUSD) LIVE ANALYSIS ===")
    logger.info(f"Server: XMGlobal-MT5 2")
    logger.info(f"Account: 165835373")
    
    # Connect to broker
    try:
        broker.connect()
        logger.info("✅ Connected to real MT5 terminal")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return
    
    # Get symbol info
    registry = get_registry()
    gold_info = registry.get("GOLD")
    
    if not gold_info:
        # Use minimal info for GOLD symbol since not in registry
        logger.info("📊 GOLD Settings (using defaults):")
        logger.info(f"  Contract Size: 100.0")
        logger.info(f"  Pip Size: 0.01")
        logger.info(f"  Min/Max Lot: 0.01/50.0")
        logger.info(f"  Description: Gold vs USD")
        
        # Create minimal symbol info
        class MockSymbolInfo:
            contract_size = 100.0
            pip_size = 0.01
            min_lot = 0.01
            max_lot = 50.0
            lot_step = 0.01
        gold_info = MockSymbolInfo()
    else:
        logger.info(f"📊 GOLD Settings:")
    logger.info(f"  Contract Size: {gold_info.contract_size}")
    logger.info(f"  Pip Size: {gold_info.pip_size}")
    logger.info(f"  Min/Max Lot: {gold_info.min_lot}/{gold_info.max_lot}")
    
    # Get current market data
    logger.info("\n=== MARKET DATA ===")
    
    # Current tick
    tick = broker.get_tick("GOLD")
    if tick:
        logger.info(f"🎯 Current Tick:")
        logger.info(f"  Bid: ${tick.bid:.2f}")
        logger.info(f"  Ask: ${tick.ask:.2f}")
        logger.info(f"  Time: {tick.time}")
        logger.info(f"  Spread: ${tick.ask - tick.bid:.2f}")
    
    # Historical bars
    bars_h1 = broker.get_bars("GOLD", "H1", count=100) or []
    bars_h4 = broker.get_bars("GOLD", "H4", count=100) or []
    bars_d1 = broker.get_bars("GOLD", "D1", count=50) or []
    
    logger.info(f"📈 Retrieved bars:")
    logger.info(f"  H1: {len(bars_h1)} bars")
    logger.info(f"  H4: {len(bars_h4)} bars") 
    logger.info(f"  D1: {len(bars_d1)} bars")
    
    if len(bars_h1) == 0:
        logger.error("❌ No market data available")
        broker.disconnect()
        return
    
    # Calculate quantitative features
    logger.info("\n=== QUANTITATIVE FEATURES ===")
    
    features_h1 = calculate_quant_features(bars_h1, gold_info, "H1")
    features_h4 = calculate_quant_features(bars_h4, gold_info, "H4")
    features_d1 = calculate_quant_features(bars_d1, gold_info, "D1")
    
    def print_features(title: str, feats: Dict[str, float]):
        logger.info(f"{title}:")
        for key, value in sorted(feats.items()):
            if isinstance(value, float):
                logger.info(f"  {key:20}: {value:8.4f}")
            else:
                logger.info(f"  {key:20}: {value}")
    
    print_features("🎯 H1 Momentum", {k: v for k, v in features_h1.items() if "roc" in k or "momentum" in k})
    print_features("📉 H1 Mean Reversion", {k: v for k, v in features_h1.items() if "rsi" in k or "bb_percentile" in k or "zscore" in k})
    print_features("📊 H1 Volatility", {k: v for k, v in features_h1.items() if "volatility" in k or "vol_percentile" in k})
    
    print_features("🎯 H4 Features", features_h4)
    print_features("🎯 D1 Features", features_d1)
    
    # Multi-timeframe trend alignment
    logger.info(f"\n=== MULTI-TIMEFRAME SIGNALS ===")
    
    h1_trend = features_h1.get("H1_trend_signal", 0)
    h4_trend = features_h4.get("H4_trend_signal", 0) 
    d1_trend = features_d1.get("D1_trend_signal", 0)
    
    alignment = "ALIGNED" if h1_trend == h4_trend or h1_trend == d1_trend else "MIXED"
    
    logger.info(f"H1 Trend: {'BULLISH' if h1_trend > 0 else 'BEARISH' if h1_trend < 0 else 'NEUTRAL'}")
    logger.info(f"H4 Trend: {'BULLISH' if h4_trend > 0 else 'BEARISH' if h4_trend < 0 else 'NEUTRAL'}")  
    logger.info(f"D1 Trend: {'BULLISH' if d1_trend > 0 else 'BEARISH' if d1_trend < 0 else 'NEUTRAL'}")
    logger.info(f"Alignment: {alignment}")
    
    # Strategy signals
    logger.info(f"\n=== STRATEGY SIGNALS ===")
    
    if tick and bars_h1:
        market_state = MarketState(
            symbol="GOLD",
            timestamp=tick.time,
            bid=tick.bid,
            ask=tick.ask,
            bars_h1=bars_h1,
            bars_h4=bars_h4,
            bars_d1=bars_d1,
            symbol_info=gold_info,
        )
        
        # Test all strategies
        strategies = [
            EMATrendStrategy("ema_trend", {"enabled": True}),
            MeanReversionBandsStrategy("mean_reversion_bands", {"enabled": True}),
            BreakoutSessionOpenStrategy("breakout_session_open", {"enabled": True}),
        ]
        
        signals_found = []
        for strategy in strategies:
            signal = strategy.analyze(market_state)
            if signal:
                signals_found.append(signal)
                logger.info(f"🎯 {strategy.name.upper()} SIGNAL:")
                logger.info(f"  Direction: {signal.direction.value}")
                logger.info(f"  Entry: ${signal.entry_price:.2f}")
                logger.info(f"  SL: ${signal.stop_loss:.2f}")
                logger.info(f"  TP: ${signal.take_profit:.2f}")
                logger.info(f"  Confidence: {signal.confidence:.2f}")
                logger.info(f"  Reason: {signal.reason}")
                logger.info("")
        
        if not signals_found:
            logger.info("❌ No strategy signals at current market state")
    
    # Risk/Position sizing example
    logger.info(f"\n=== RISK EXAMPLE ===")
    
    if tick and features_h1:
        # Example: 2% risk on $100k account
        account_balance = 100000.0
        risk_percent = 2.0
        risk_amount = account_balance * (risk_percent / 100.0)
        
        # Hypothetical trade
        entry_price = tick.ask
        stop_loss = tick.ask - (10 * gold_info.pip_size)  # 10 pip stop
        
        stop_distance_pips = (entry_price - stop_loss) / gold_info.pip_size
        pip_value_per_lot = gold_info.contract_size * gold_info.pip_size
        
        if stop_distance_pips > 0 and pip_value_per_lot > 0:
            lots = risk_amount / (stop_distance_pips * pip_value_per_lot)
            normalized_lots = max(gold_info.min_lot, min(gold_info.max_lot, round(lots / gold_info.lot_step) * gold_info.lot_step))
            
            logger.info(f"Account Balance: ${account_balance:,.0f}")
            logger.info(f"Risk Target: {risk_percent}% = ${risk_amount:.0f}")
            logger.info(f"Stop Distance: {stop_distance_pips:.0f} pips")
            logger.info(f"Suggested Lot Size: {normalized_lots:.2f}")
            logger.info(f"Max Risk Amount: ${normalized_lots * stop_distance_pips * pip_value_per_lot:.0f}")
    
    # Summary
    logger.info(f"\n=== LIVE ANALYSIS SUMMARY ===")
    
    if tick:
        logger.info(f"Current GOLD Price: ${tick.bid:.2f} / ${tick.ask:.2f}")
        logger.info(f"Spread: ${tick.ask - tick.bid:.2f}")
    
    current_features = {**features_h1, **features_h4, **features_d1}
    logger.info(f"Total features calculated: {len(current_features)}")
    
    # Signal if momentum + mean reversion aligned
    if "H1_roc_10" in features_h1 and "H1_rsi" in features_h1:
        roc = features_h1["H1_roc_10"]
        rsi = features_h1["H1_rsi"]
        
        momentum_bias = "BULLISH" if roc > 0.001 else "BEARISH" if roc < -0.001 else "NEUTRAL"  # 0.1% threshold
        mr_bias = "OVERBOUGHT" if rsi > 70 else "OVERSOLD" if rsi < 30 else "NEUTRAL"
        
        logger.info(f"Momentum Bias (ROC10): {momentum_bias} ({roc:.3f})")
        logger.info(f"Mean Rev Bias (RSI): {mr_bias} ({rsi:.1f})")
        
        # Combined signal
        if momentum_bias == "BULLISH" and mr_bias == "OVERSOLD":
            logger.info("🟢 BULLISH CONFLUENCE: Momentum ↑ + Oversold bounce")
        elif momentum_bias == "BEARISH" and mr_bias == "OVERBOUGHT":
            logger.info("🔴 BEARISH CONFLUENCE: Momentum ↓ + Overbought fade")
        else:
            logger.info("⚪ NEUTRAL: No clear confluence")
    
    broker.disconnect()
    logger.info("\n✅ Analysis complete - disconnected from MT5")


if __name__ == "__main__":
    run_live_gold_analysis()
