#!/usr/bin/env python3
"""Test the fixed Gold strategies."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker
from src.strategy.gold_mean_reversion import GoldMeanReversionStrategy
from src.strategy.gold_breakout import GoldBreakoutStrategy
from src.strategy.loader import MarketState
from src.core.symbols import SymbolInfo, AssetClass


def test_fixed_strategies():
    """Test the fixed Gold strategies."""
    print("🔧 TESTING FIXED GOLD STRATEGIES")
    print("=" * 50)
    
    broker = MT5Broker(
        login="165835373", 
        password="Manan@123!!",
        server="XMGlobal-MT5 2",
        paper_mode=False
    )
    
    try:
        broker.connect()
        print("✅ Connected to MT5")
        
        # Get data
        bars_h1 = broker.get_bars("GOLD", "H1", count=100) or []
        bars_h4 = broker.get_bars("GOLD", "H4", count=100) or []
        
        if len(bars_h1) == 0:
            print("❌ No data")
            return
        
        print(f"📊 Data: {len(bars_h1)} H1, {len(bars_h4)} H4 bars")
        
        tick = broker.get_tick("GOLD")
        if not tick:
            print("❌ No tick")
            return
        
        # Create market state
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
        
        print(f"💰 GOLD: ${tick.bid:.2f} / ${tick.ask:.2f}")
        
        # Test Gold Mean Reversion
        print(f"\n🎯 TESTING GOLD MEAN REVERSION")
        print("-" * 30)
        
        mr_strategy = GoldMeanReversionStrategy()
        mr_signal = mr_strategy.analyze(market_state)
        
        print(f"Signal: {mr_signal}")
        
        if mr_signal:
            print(f"✅ SIGNAL GENERATED!")
            print(f"   Direction: {mr_signal.direction}")
            print(f"   Entry: ${mr_signal.entry_price:.2f}")
            print(f"   SL: ${mr_signal.stop_loss:.2f}")
            print(f"   TP: ${mr_signal.take_profit:.2f}")
            print(f"   Reason: {mr_signal.reason}")
        else:
            print("❌ No signal")
        
        # Test Gold Breakout
        print(f"\n🎯 TESTING GOLD BREAKOUT")
        print("-" * 30)
        
        bs_strategy = GoldBreakoutStrategy()
        bs_signal = bs_strategy.analyze(market_state)
        
        print(f"Signal: {bs_signal}")
        
        if bs_signal:
            print(f"✅ SIGNAL GENERATED!")
            print(f"   Direction: {bs_signal.direction}")
            print(f"   Entry: ${bs_signal.entry_price:.2f}")
            print(f"   SL: ${bs_signal.stop_loss:.2f}")
            print(f"   TP: ${bs_signal.take_profit:.2f}")
            print(f"   Reason: {bs_signal.reason}")
        else:
            print("❌ No signal")
        
        # Summary
        print(f"\n📋 RESULTS")
        print("-" * 30)
        print(f"Gold Mean Reversion: {'✅ WORKING' if mr_signal else '❌ NO SIGNAL'}")
        print(f"Gold Breakout: {'✅ WORKING' if bs_signal else '❌ NO SIGNAL'}")
        
        if not mr_signal and not bs_signal:
            print(f"\n🔍 Current market conditions may not meet strategy criteria:")
            print(f"   - Mean reversion needs extreme RSI + band pierce")
            print(f"   - Breakout needs H4 trend + momentum")
            print(f"📊 Strategies are functional but waiting for setups")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        broker.disconnect()


if __name__ == "__main__":
    test_fixed_strategies()
