"""
Test ALL EMA Crossover variations.

7 Tests:
1. Baseline (20/50, no filters)
2. +ADX filter
3. +ATR filter
4. +NY session
5. +ADX + NY (combo)
6. Faster EMAs (10/30)
7. Slower EMAs (50/100)

Each tested on:
- EURUSD 12m
- GBPUSD 12m
- EURUSD first 6m (walk-forward)
- EURUSD last 6m (walk-forward)
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.ema_crossover import EMACrossover
from src.engine.backtester import Backtester

logging.basicConfig(level=logging.WARNING)  # Suppress debug spam
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def test_config(name, symbol, start, end, config):
    """Run single test."""
    strategy = EMACrossover(config=config)
    backtester = Backtester(strategy=strategy, initial_capital=10000.0, risk_per_trade_pct=1.0)

    # Suppress logs during test
    logging.getLogger('src.engine.backtester').setLevel(logging.ERROR)
    logging.getLogger('src.strategy.ema_crossover').setLevel(logging.ERROR)

    metrics = backtester.run(symbol, "H1", start, end)

    if metrics and metrics.total_trades > 0:
        return {
            "name": name,
            "symbol": symbol,
            "trades": metrics.total_trades,
            "win_rate": metrics.win_rate,
            "pnl": metrics.total_pnl,
            "pnl_pct": metrics.total_pnl_pct,
            "exp": metrics.expectancy,
            "pf": metrics.profit_factor,
            "dd": metrics.max_drawdown_pct,
        }
    return None


def main():
    print("="*80)
    print("EMA CROSSOVER - COMPREHENSIVE TEST")
    print("="*80)
    print("\nTesting 7 variations × 4 scenarios = 28 backtests")
    print("This will take 3-5 minutes...\n")

    if not mt5.initialize():
        print("MT5 failed")
        return

    # Date ranges
    end = datetime.now()
    start_12m = end - timedelta(days=365)
    mid_6m = end - timedelta(days=180)

    # Test configurations
    configs = [
        # Test 1: Baseline
        {
            "name": "T1: 20/50 Baseline",
            "config": {"fast_ema": 20, "slow_ema": 50},
        },
        # Test 2: +ADX
        {
            "name": "T2: 20/50 +ADX>25",
            "config": {"fast_ema": 20, "slow_ema": 50, "use_adx_filter": True, "adx_threshold": 25},
        },
        # Test 3: +ATR
        {
            "name": "T3: 20/50 +ATR",
            "config": {"fast_ema": 20, "slow_ema": 50, "use_atr_filter": True, "atr_min_pct": 0.08, "atr_max_pct": 0.25},
        },
        # Test 4: +NY session
        {
            "name": "T4: 20/50 +NY",
            "config": {"fast_ema": 20, "slow_ema": 50, "use_session_filter": True, "ny_only": True},
        },
        # Test 5: +ADX +NY (combo)
        {
            "name": "T5: 20/50 +ADX+NY",
            "config": {"fast_ema": 20, "slow_ema": 50, "use_adx_filter": True, "adx_threshold": 25, "use_session_filter": True, "ny_only": True},
        },
        # Test 6: Faster EMAs
        {
            "name": "T6: 10/30 Fast",
            "config": {"fast_ema": 10, "slow_ema": 30},
        },
        # Test 7: Slower EMAs
        {
            "name": "T7: 50/100 Slow",
            "config": {"fast_ema": 50, "slow_ema": 100},
        },
    ]

    all_results = []

    for test in configs:
        print(f"\n{test['name']}")
        print("-" * 60)

        test_results = []

        # EURUSD 12m
        r1 = test_config(f"{test['name']} EUR12m", "EURUSD", start_12m, end, test['config'])
        if r1:
            test_results.append(r1)
            print(f"  EUR 12m: ${r1['pnl']:>7.0f} | {r1['trades']:>2}T | {r1['win_rate']:>4.0%}WR | PF={r1['pf']:.2f}")

        # GBPUSD 12m
        r2 = test_config(f"{test['name']} GBP12m", "GBPUSD", start_12m, end, test['config'])
        if r2:
            test_results.append(r2)
            print(f"  GBP 12m: ${r2['pnl']:>7.0f} | {r2['trades']:>2}T | {r2['win_rate']:>4.0%}WR | PF={r2['pf']:.2f}")

        # EURUSD first 6m
        r3 = test_config(f"{test['name']} EUR6m-1", "EURUSD", start_12m, mid_6m, test['config'])
        if r3:
            test_results.append(r3)
            print(f"  EUR 6m-1: ${r3['pnl']:>6.0f} | {r3['trades']:>2}T | {r3['win_rate']:>4.0%}WR | PF={r3['pf']:.2f}")

        # EURUSD last 6m
        r4 = test_config(f"{test['name']} EUR6m-2", "EURUSD", mid_6m, end, test['config'])
        if r4:
            test_results.append(r4)
            print(f"  EUR 6m-2: ${r4['pnl']:>6.0f} | {r4['trades']:>2}T | {r4['win_rate']:>4.0%}WR | PF={r4['pf']:.2f}")

        # Score this test
        if test_results:
            avg_pnl = sum(r['pnl'] for r in test_results) / len(test_results)
            avg_pf = sum(r['pf'] for r in test_results) / len(test_results)
            profitable_count = sum(1 for r in test_results if r['pnl'] > 0)

            score = {
                "test_name": test['name'],
                "results": test_results,
                "avg_pnl": avg_pnl,
                "avg_pf": avg_pf,
                "profitable_count": profitable_count,
                "total_tests": len(test_results),
            }
            all_results.append(score)

            print(f"  >>> AVG: ${avg_pnl:.0f} | PF={avg_pf:.2f} | {profitable_count}/{len(test_results)} profitable")

    # Final rankings
    print("\n" + "="*80)
    print("FINAL RANKINGS")
    print("="*80)

    # Sort by average PNL
    all_results.sort(key=lambda x: x['avg_pnl'], reverse=True)

    print(f"\n{'Rank':<6} {'Test':<25} {'Avg P&L':<12} {'Avg PF':<10} {'Win%':<10}")
    print("-" * 80)

    for i, score in enumerate(all_results, 1):
        win_pct = (score['profitable_count'] / score['total_tests']) * 100
        print(f"{i:<6} {score['test_name']:<25} ${score['avg_pnl']:>9.0f}  {score['avg_pf']:>8.2f}  {win_pct:>7.0f}%")

    # Best performer detailed view
    if all_results:
        best = all_results[0]
        print("\n" + "="*80)
        print(f"WINNER: {best['test_name']}")
        print("="*80)
        print(f"\nAverage P&L: ${best['avg_pnl']:,.0f}")
        print(f"Average PF: {best['avg_pf']:.2f}")
        print(f"Win Rate: {best['profitable_count']}/{best['total_tests']} scenarios")

        print("\nDetailed Results:")
        for r in best['results']:
            status = "WIN" if r['pnl'] > 0 else "LOSS"
            print(f"  {r['symbol']}: ${r['pnl']:>7.0f} | {r['trades']}T | {r['win_rate']:.0%}WR | PF={r['pf']:.2f} [{status}]")

        # Viability check
        print("\n" + "="*80)
        print("VIABILITY CHECKLIST")
        print("="*80)

        checks = []
        checks.append(("Avg P&L > $300", best['avg_pnl'] > 300))
        checks.append(("Avg PF > 1.2", best['avg_pf'] > 1.2))
        checks.append(("3+ scenarios profitable", best['profitable_count'] >= 3))

        # Check EURUSD 12m specifically
        eur_12m = next((r for r in best['results'] if 'EUR12m' in r['name']), None)
        if eur_12m:
            checks.append(("EURUSD 12m profitable", eur_12m['pnl'] > 0))
            checks.append(("EURUSD 12m PF > 1.2", eur_12m['pf'] > 1.2))

        for check, passed in checks:
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check}")

        passed_count = sum(1 for _, p in checks if p)

        print(f"\nPassed: {passed_count}/{len(checks)} checks")

        if passed_count >= 4:
            print("\n>>> VERDICT: VIABLE FOR PAPER TRADING")
            print(">>> Next: Paper trade 1-2 months, then go live if still profitable")
        elif passed_count >= 3:
            print("\n>>> VERDICT: MARGINAL - Needs more validation")
            print(">>> Consider longer testing or parameter tweaking")
        else:
            print("\n>>> VERDICT: NOT VIABLE")
            print(">>> EMA crossover doesn't have edge in current market conditions")

    mt5.shutdown()
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
