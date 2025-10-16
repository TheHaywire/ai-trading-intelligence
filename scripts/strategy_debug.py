#!/usr/bin/env python3
"""
Debug why strategies generate 0 trades
"""

import sys
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker
from src.strategy.mean_reversion_bands import MeanReversionBandsStrategy
from src.strategy.breakout_session_open import BreakoutSessionOpenStrategy
from src.strategy.loader import MarketState
from src.core.symbols import SymbolInfo, AssetClass


def debug_strategies():
    """Debug why strategies generate 0 trades."""
    print("🐛 STRATEGY DEBUG ANALYSIS")
    print("=" * 50)
    
    # Connect to broker
    broker = MT5Broker(
        login="165835373", 
        password="Manan@123!!",
        server="XMGlobal-MT5 2",
        paper_mode=False
    )
    
    try:
        broker.connect()
        print("✅ Connected to MT5")
        
        # Get GOLD data
        bars_h1 = broker.get_bars("GOLD", "H1", count=200) or []
        bars_h4 = broker.get_bars("GOLD", "H4", count=100) or []
        
        if len(bars_h1) == 0:
            print("❌ No GOLD data")
            return
        
        print(f"📊 GOLD Data: {len(bars_h1)} H1 bars, {len(bars_h4)} H4 bars")
        
        # Create GOLD symbol info
        gold_info = SymbolInfo(
            symbol="GOLD",
            asset_class=AssetClass.COMMODITIES,
            contract_size=100.0,
            pip_size=0.01,
            min_lot=0.01,
            max_lot=50.0,
            lot_step=0.01,
            base_currency="XAU",
            quote_currency="USD",
            margin_currency="USD",
            description="Gold vs USD",
        )
        
        tick = broker.get_tick("GOLD")
        if not tick:
            print("❌ No current tick")
            return
            
        print(f"💰 Current GOLD: ${tick.bid:.2f} / ${tick.ask:.2f}")
        
        # Test Mean Reversion Strategy
        print(f"\n🔍 DEBUGGING MEAN REVERSION STRATEGY")
        print("-" * 40)
        
        mr_strategy = MeanReversionBandsStrategy("mean_reversion", {"enabled": True})
        
        # Test each condition
        print(f"1. Symbol check: {'XAUUSD' in mr_strategy.config['allowed_symbols']}")
        print(f"2. Config allowed_symbols: {mr_strategy.config['allowed_symbols']}")
        
        # Fix symbol issue
        mr_strategy.config["allowed_symbols"] = ["GOLD"]  # Add GOLD
        
        print(f"3. Fixed allowed_symbols: {mr_strategy.config['allowed_symbols']}")
        
        # Test session
        current_hour_utc = datetime.now().hour
        is_allowed_session = current_hour_utc >= 7 and current_hour_utc < 16  # London session
        print(f"4. Session check: current hour={current_hour_utc}, allowed={is_allowed_session}")
        
        # Test spread
        spread = tick.ask - tick.bid
        spread_points = spread / gold_info.pip_size
        max_spread_points = mr_strategy.config["max_spread_points"]
        print(f"5. Spread check: {spread_points:.1f} points vs max {max_spread_points}")
        
        # Test data sufficiency
        min_bars_needed = max(mr_strategy.config["vwap_period"], mr_strategy.config["atr_period"]) + 10
        print(f"6. Data sufficiency: {len(bars_h1)} bars vs needed {min_bars_needed}")
        
        # Test VWAP calculation
        try:
            vwap, upper_band, lower_band = mr_strategy._calculate_vwap_bands(bars_h1)
            print(f"7. VWAP: ${vwap:.2f}, Upper: ${upper_band:.2f}, Lower: ${lower_band:.2f}")
            
            # Test RSI
            rsi = mr_strategy._calculate_rsi(bars_h1, mr_strategy.config["rsi_period"])
            print(f"8. RSI(2): {rsi:.1f}")
            
            # Test conditions
            current_price = bars_h1[-1]["close"]
            print(f"9. Current price: ${current_price:.2f}")
            
            print(f"10. Long condition: price ${current_price:.2f} < lower_band ${lower_band:.2f} = {current_price < lower_band}")
            print(f"11. RSI oversold: rsi {rsi:.1f} < {mr_strategy.config['rsi_oversold']} = {rsi < mr_strategy.config['rsi_oversold']}")
            
            print(f"12. Short condition: price ${current_price:.2f} > upper_band ${upper_band:.2f} = {current_price > upper_band}")
            print(f"13. RSI overbought: rsi {rsi:.1f} > {mr_strategy.config['rsi_overbought']} = {rsi > mr_strategy.config['rsi_overbought']}")
            
        except Exception as e:
            print(f"❌ VWAP calculation failed: {e}")
        
        # Test Breakout Strategy
        print(f"\n🔍 DEBUGGING BREAKOUT SESSION STRATEGY")
        print("-" * 40)
        
        bs_strategy = BreakoutSessionOpenStrategy("breakout_session", {"enabled": True})
        
        # Test symbol
        print(f"1. Symbol check: 'GOLD' in {bs_strategy.config['allowed_symbols']}")
        
        # Fix symbol
        bs_strategy.config["allowed_symbols"] = ["GOLD"]
        
        # Test session detection
        session = bs_strategy._get_current_session(current_hour_utc)
        print(f"2. Current session: {session}")
        print(f"3. Allowed sessions: {bs_strategy.config['sessions']}")
        
        # Test H4 trend
        try:
            trend = bs_strategy._get_h4_trend(bars_h4)
            print(f"4. H4 trend: {trend}")
        except Exception as e:
            print(f"❌ H4 trend failed: {e}")
        
        # Test session box
        try:
            box_high, box_low = bs_strategy._calculate_session_box(bars_h1, session or "london")
            print(f"5. Session box: ${box_low:.2f} - ${box_high:.2f}")
        except Exception as e:
            print(f"❌ Session box failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test strategy with real data
        print(f"\n🎯 RUNNING STRATEGIES WITH REAL DATA")
        print("-" * 40)
        
        market_state = MarketState(
            symbol="GOLD",
            timestamp=tick.time,
            bid=tick.bid,
            ask=tick.ask,
            bars_h1=bars_h1,
            bars_h4=bars_h4,
            bars_d1=[],
            symbol_info=gold_info,
        )
        
        # Test Mean Reversion
        mr_signal = mr_strategy.analyze(market_state)
        print(f"Mean Reversion Signal: {mr_signal}")
        
        if mr_signal:
            print(f"  Direction: {mr_signal.direction}")
            print(f"  Entry: ${mr_signal.entry_price:.2f}")
            print(f"  SL: ${mr_signal.stop_loss:.2f}")
            print(f"  TP: ${mr_signal.take_profit:.2f}")
            print(f"  Reason: {mr_signal.reason}")
        
        # Test Breakout
        bs_signal = bs_strategy.analyze(market_state)
        print(f"\nBreakout Signal: {bs_signal}")
        
        if bs_signal:
            print(f"  Direction: {bs_signal.context}")
            print(f"  Entry: ${bs_signal.entry_price:.2f}")
            print(f"  SL: ${bs_signal.stop_loss:.2f}")
            print(f"  TP: ${bs_signal.take_profit:.2f}")
            print(f"  Reason: {bs_signal.reason}")
        
        # Summary
        print(f"\n📋 SUMMARY")
        print("-" * 40)
        print(f"Mean Reversion Issues:")
        print(f"  - Missing 'GOLD' from allowed_symbols")
        print(f"  - Possible session timing issues")
        print(f"  - RSI(2) might be too extreme ({mr_strategy.config['rsi_oversold']}/{mr_strategy.config['rsi_overbought']})")
        
        print(f"\nBreakout Issues:")
        print(f"  - Missing 'GOLD' from allowed_symbols")
        print(f"  - Session box calculation likely broken")
        print(f"  - Hour detection algorithm flawed")
        
        print(f"\n🔧 QUICK FIX: Update configs to include 'GOLD'")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        broker.disconnect()


if __name__ == "__main__":
    debug_strategies()
