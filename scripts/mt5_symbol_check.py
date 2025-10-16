#!/usr/bin/env python3
"""
Check available symbols on MT5 broker
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker

def check_symbols():
    """Check available symbols."""
    broker = MT5Broker(
        login="165835373", 
        password="Manan@123!!",
        server="XMGlobal-MT5 2",
        paper_mode=False
    )
    
    try:
        broker.connect()
        print("✅ Connected to MT5")
        
        # Try to get account info first
        account_info = broker.get_account_info()
        print(f"Account Balance: ${account_info.balance}")
        print(f"Account Equity: ${account_info.equity}")
        print(f"Account Currency: {account_info.currency}")
        print(f"Leverage: {account_info.leverage}")
        
        # Test different symbol names for gold
        gold_symbols = ["XAUUSD", "GOLD", "GOLDUSD", "XAUUSD.", "GOLD.m"]
        
        print("\n🔍 Testing Gold Symbol Names:")
        for symbol in gold_symbols:
            print(f"Testing {symbol}...")
            bars = broker.get_bars(symbol, "H1", count=5)
            if bars and len(bars) > 0:
                print(f"✅ {symbol} - {len(bars)} bars available")
                print(f"   Latest: {bars[-1]['close']}")
                break
            else:
                print(f"❌ {symbol} - No data")
        
        print("\n🧪 Testing Other Symbols:")
        test_symbols = ["EURUSD", "GBPUSD", "USDJPY", "US30", "BTCUSD"]
        for symbol in test_symbols:
            bars = broker.get_bars(symbol, "H1", count=3)
            if bars and len(bars) > 0:
                print(f"✅ {symbol} - {len(bars)} bars")
            else:
                print(f"❌ {symbol} - No data")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        broker.disconnect()

if __name__ == "__main__":
    check_symbols()
