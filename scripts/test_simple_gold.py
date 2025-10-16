#!/usr/bin/env python3
"""Test simple gold strategy."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker
from src.strategy.gold_simple import GoldSimpleStrategy
from src.strategy.loader import MarketState
from src.core.symbols import SymbolInfo, AssetClass


def test_simple_gold():
    """Test the simple gold strategy."""
    print("🎯 TESTING SIMPLE GOLD STRATEGY")
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
        bars_h1 = broker.get_bars("GOLD", "H1", count=50) or []
        tick = broker.get_tick("GOLD")
        
        if not bars_h1 or not tick:
            print("❌ No data")
            return
        
        print(f"📊 GOLD: ${tick.bid:.2f} / ${tick.ask:.2f}")
        print(f"📊 Bars: {len(bars_h1)} H1 bars")
        
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
            bars_h4=[],
            bars_d1=[],
            symbol_info=gold_info
        )
        
        # Test strategy
        strategy = GoldSimpleStrategy()
        signal = strategy.analyze(market_state)
        
        print(f"\n🎯 SIGNAL RESULT:")
        print("-" * 30)
        
        if signal:
            print(f"✅ SIGNAL GENERATED!")
            print(f"   Direction: {signal.direction}")
            print(f"   Entry: ${signal.entry_price:.2f}")
            print(f"   SL: ${signal.stop_loss:.2f}")
            print(f"   TP: ${signal.take_profit:.2f}")
            print(f"   Reason: {signal.reason}")
            print(f"   Confidence: {signal.confidence}")
            
            # Test position sizing
            risk_amount = 1000  # $1000 risk
            lots = strategy.calculate_position_size(
                signal.entry_price,
                signal.stop_loss, 
                risk_amount,
                gold_info
            )
            print(f"   Position size: {lots:.2f} lots (${risk_amount} risk)")
        else:
            print("❌ No signal - checking market conditions...")
            
            # Debug info
            current_price = bars_h1[-1]["close"]
            prices = [b["close"] for b in bars_h1]
            ma = strategy._calculate_ma(prices, strategy.config["ma_period"])
            
            if ma:
                momentum = (current_price - ma) / ma * 100
                print(f"   Current price: ${current_price:.2f}")
                print(f"   MA20: ${ma:.2f}")
                print(f"   Momentum: {momentum:.2f}%")
                print(f"   Threshold: ±{strategy.config['momentum_threshold']:.1f}%")
                print(f"   Signal needed: {abs(momentum):.2f}% vs {strategy.config['momentum_threshold']:.1f}%")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        broker.disconnect()


if __name__ == "__main__":
    test_simple_gold()
