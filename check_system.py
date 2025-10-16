#!/usr/bin/env python3
"""System health check script."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.broker_mt5 import MT5Broker
from src.core.config import TradingConfig

def check_broker_methods():
    """Check broker has required methods."""
    print("[*] Checking Broker Methods...")
    required = ["get_bars", "get_tick", "place_order", "close_position", "get_positions"]
    missing = []

    for method in required:
        if not hasattr(MT5Broker, method):
            missing.append(method)
            print(f"  [FAIL] Missing: {method}")
        else:
            print(f"  [OK] Found: {method}")

    return len(missing) == 0

def check_config():
    """Check config loads correctly."""
    print("\n[*] Checking Configuration...")
    try:
        config = TradingConfig.from_yaml("configs/example_if_100k_profitmax.yaml")
        print(f"  [OK] Config loaded")
        print(f"  [OK] Program: {config.account.program}")
        print(f"  [OK] Starting balance: ${config.account.starting_balance:,.2f}")
        print(f"  [OK] Strategies enabled: {sum([1 for s in [config.strategies.ema_trend, config.strategies.mean_reversion_bands, config.strategies.breakout_session_open] if s.enabled])}")
        return True
    except Exception as e:
        print(f"  [FAIL] Config error: {e}")
        return False

def check_broker_connection():
    """Check MT5 connection."""
    print("\n[*] Checking MT5 Connection...")
    try:
        config = TradingConfig.from_yaml("configs/example_if_100k_profitmax.yaml")
        broker = MT5Broker(
            login=config.platform.login,
            password=config.platform.password,
            server=config.platform.server,
            paper_mode=False
        )

        success = broker.connect()
        if success:
            print(f"  [OK] Connected to {config.platform.server}")

            # Get account info
            account = broker.get_account_info()
            print(f"  [OK] Account: {account.login}")
            print(f"  [OK] Equity: ${account.equity:,.2f}")
            print(f"  [OK] Balance: ${account.balance:,.2f}")
            print(f"  [OK] Margin: ${account.margin:,.2f}")
            print(f"  [OK] Free margin: ${account.free_margin:,.2f}")

            # Get positions
            positions = broker.get_positions()
            print(f"  [OK] Open positions: {len(positions)}")

            # Test get_bars
            bars = broker.get_bars("EURUSD", "H1", count=10)
            if bars:
                print(f"  [OK] get_bars() working: {len(bars)} bars fetched")
            else:
                print(f"  [WARN] get_bars() returned None")

            # Test get_tick
            tick = broker.get_tick("EURUSD")
            if tick:
                print(f"  [OK] get_tick() working: bid={tick.bid}, ask={tick.ask}")
            else:
                print(f"  [WARN] get_tick() returned None")

            broker.disconnect()
            return True
        else:
            print(f"  [FAIL] Connection failed")
            return False

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("PROPSHOP IF - SYSTEM HEALTH CHECK")
    print("=" * 60)

    checks = [
        ("Broker Methods", check_broker_methods),
        ("Configuration", check_config),
        ("MT5 Connection", check_broker_connection),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] {name} check failed with exception: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n[SUCCESS] ALL CHECKS PASSED - SYSTEM READY")
        return 0
    else:
        print("\n[WARNING] SOME CHECKS FAILED - REVIEW ABOVE")
        return 1

if __name__ == "__main__":
    sys.exit(main())
