"""
Extended testing of the WINNER: 20/50 EMA + NY Session

Tests:
1. Maximum available data (2+ years if possible)
2. Different risk levels (0.5%, 1%, 2%)
3. Parameter tweaks (ADX addition, different EMAs)
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.ema_crossover import EMACrossover
from src.engine.backtester import Backtester

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def test(name, symbol, start, end, config, risk_pct=1.0):
    """Run test."""
    strategy = EMACrossover(config=config)
    backtester = Backtester(strategy=strategy, initial_capital=10000.0, risk_per_trade_pct=risk_pct)

    logging.getLogger('src.engine.backtester').setLevel(logging.ERROR)
    logging.getLogger('src.strategy.ema_crossover').setLevel(logging.ERROR)

    metrics = backtester.run(symbol, "H1", start, end)

    if metrics:
        return {
            "name": name,
            "trades": metrics.total_trades,
            "win_rate": metrics.win_rate,
            "pnl": metrics.total_pnl,
            "pnl_pct": metrics.total_pnl_pct,
            "exp": metrics.expectancy,
            "pf": metrics.profit_factor,
            "dd": metrics.max_drawdown_pct,
            "sharpe": metrics.sharpe_ratio,
        }
    return None


def main():
    print("="*70)
    print("EXTENDED TESTING - WINNER (20/50 + NY Session)")
    print("="*70)

    if not mt5.initialize():
        print("MT5 failed")
        return

    # Baseline config (our winner)
    baseline_config = {
        "fast_ema": 20,
        "slow_ema": 50,
        "use_session_filter": True,
        "ny_only": True,
    }

    end = datetime.now()

    # Try to get 2+ years of data
    start_24m = end - timedelta(days=730)
    start_18m = end - timedelta(days=545)
    start_12m = end - timedelta(days=365)

    results = []

    print("\n1. EXTENDED TIME PERIODS")
    print("-" * 70)

    # Test on maximum available periods
    for months, start in [("24m", start_24m), ("18m", start_18m), ("12m", start_12m)]:
        print(f"\n{months} Period:")

        r1 = test(f"EURUSD {months}", "EURUSD", start, end, baseline_config)
        if r1:
            results.append(r1)
            print(f"  EURUSD: ${r1['pnl']:>7.0f} | {r1['trades']:>2}T | {r1['win_rate']:>4.0%}WR | PF={r1['pf']:.2f} | DD={r1['dd']:.1%}")

        r2 = test(f"GBPUSD {months}", "GBPUSD", start, end, baseline_config)
        if r2:
            results.append(r2)
            print(f"  GBPUSD: ${r2['pnl']:>7.0f} | {r2['trades']:>2}T | {r2['win_rate']:>4.0%}WR | PF={r2['pf']:.2f} | DD={r2['dd']:.1%}")

    print("\n" + "="*70)
    print("2. DIFFERENT RISK LEVELS (12m EURUSD)")
    print("-" * 70)

    for risk in [0.5, 1.0, 2.0]:
        r = test(f"Risk {risk}%", "EURUSD", start_12m, end, baseline_config, risk_pct=risk)
        if r:
            results.append(r)
            print(f"  Risk {risk}%: ${r['pnl']:>7.0f} | Exp=${r['exp']:>6.2f} | DD={r['dd']:.1%}")

    print("\n" + "="*70)
    print("3. PARAMETER TWEAKS (12m EURUSD)")
    print("-" * 70)

    tweaks = [
        ("Baseline", baseline_config),
        ("+ADX>20", {**baseline_config, "use_adx_filter": True, "adx_threshold": 20}),
        ("+ADX>25", {**baseline_config, "use_adx_filter": True, "adx_threshold": 25}),
        ("+ADX>30", {**baseline_config, "use_adx_filter": True, "adx_threshold": 30}),
        ("15/45 EMAs", {**baseline_config, "fast_ema": 15, "slow_ema": 45}),
        ("25/55 EMAs", {**baseline_config, "fast_ema": 25, "slow_ema": 55}),
    ]

    tweak_results = []
    for name, config in tweaks:
        r = test(name, "EURUSD", start_12m, end, config)
        if r:
            tweak_results.append(r)
            print(f"  {name:<15}: ${r['pnl']:>7.0f} | {r['trades']:>2}T | PF={r['pf']:.2f}")

    # Find best tweak
    if tweak_results:
        best_tweak = max(tweak_results, key=lambda x: x['pnl'])

        print("\n" + "="*70)
        print("BEST CONFIGURATION")
        print("="*70)
        print(f"\n{best_tweak['name']}")
        print(f"  P&L: ${best_tweak['pnl']:,.0f}")
        print(f"  Trades: {best_tweak['trades']}")
        print(f"  Win Rate: {best_tweak['win_rate']:.1%}")
        print(f"  Expectancy: ${best_tweak['exp']:.2f}")
        print(f"  Profit Factor: {best_tweak['pf']:.2f}")
        print(f"  Max Drawdown: {best_tweak['dd']:.1%}")
        print(f"  Sharpe: {best_tweak['sharpe']:.2f}")

        # Test best config on GBPUSD
        print("\n" + "="*70)
        print("CROSS-ASSET VALIDATION (Best Config)")
        print("="*70)

        best_config = next(c for n, c in tweaks if n == best_tweak['name'])
        r_gbp = test("GBPUSD", "GBPUSD", start_12m, end, best_config)

        if r_gbp:
            print(f"\nGBPUSD 12m: ${r_gbp['pnl']:+,.0f} | {r_gbp['trades']}T | {r_gbp['win_rate']:.0%}WR | PF={r_gbp['pf']:.2f}")

            both_profitable = best_tweak['pnl'] > 0 and r_gbp['pnl'] > 0

            print("\n" + "="*70)
            print("FINAL VERDICT")
            print("="*70)

            if both_profitable and best_tweak['pf'] > 1.3 and r_gbp['pf'] > 1.2:
                print("\n>>> VIABLE FOR PAPER TRADING")
                print(f">>> Expected annual return: {(best_tweak['pnl']/10000)*100:.1f}% on EURUSD")
                print(f">>> Expected annual return: {(r_gbp['pnl']/10000)*100:.1f}% on GBPUSD")
                print("\n>>> NEXT STEPS:")
                print("    1. Paper trade for 1-2 months")
                print("    2. Monitor real slippage/spreads")
                print("    3. Go live with $10k if still profitable")
                print("    4. Scale to $50k after 6 months if consistent")

            elif both_profitable:
                print("\n>>> MARGINALLY VIABLE")
                print(f">>> Profit too small: ${best_tweak['pnl']+r_gbp['pnl']:.0f} total on 12m")
                print(">>> Consider:")
                print("    - Paper trading to validate")
                print("    - Increasing risk to 2% per trade")
                print("    - Trading multiple pairs simultaneously")

            else:
                print("\n>>> NOT VIABLE")
                if not both_profitable:
                    print(">>> One pair is unprofitable")
                print(">>> Consider manual/discretionary trading instead")

    mt5.shutdown()
    print("\n" + "="*70)
    print("EXTENDED TESTING COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
