"""
Comprehensive regime filter testing.

Tests ALL combinations simultaneously:
1. 6-month EURUSD with regime filter
2. 6-month EURUSD without regime filter (baseline)
3. 3-month EURUSD with regime filter
4. 3-month GBPUSD with regime filter
5. Different regime thresholds (ADX 20, 25, 30)
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.momentum_matrix import MomentumMatrixTrader
from src.engine.backtester import Backtester

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def run_test(name, symbol, months, config):
    """Run single backtest."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)

    strategy = MomentumMatrixTrader(config=config)
    backtester = Backtester(strategy=strategy, initial_capital=10000.0, risk_per_trade_pct=0.5)
    metrics = backtester.run(symbol, "H1", start_date, end_date)

    if metrics:
        return {
            "name": name,
            "symbol": symbol,
            "months": months,
            "trades": metrics.total_trades,
            "win_rate": metrics.win_rate,
            "total_pnl": metrics.total_pnl,
            "expectancy": metrics.expectancy,
            "profit_factor": metrics.profit_factor,
            "max_dd": metrics.max_drawdown_pct,
            "sharpe": metrics.sharpe_ratio,
        }
    return None


def main():
    """Run all tests."""
    logger.info("="*100)
    logger.info("COMPREHENSIVE REGIME FILTER TESTING")
    logger.info("="*100)

    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return

    logger.info(f"MT5 connected: {mt5.version()}\n")

    # Base config
    base_config = {
        "threshold": 5,
        "weights": {"trend": 1, "momentum": 0, "price_action": 4, "mtf_confluence": 2, "volatility": 1, "intermarket": 1, "session": 1},
        "session_filter_enabled": True,
        "ny_only_mode": True,
    }

    logger.info("Running all tests in parallel (this will take 2-3 minutes)...\n")

    results = []

    # Test 1: 6-month EURUSD WITHOUT regime filter (baseline)
    logger.info("[1/7] Testing 6m EURUSD - NO REGIME FILTER (baseline)...")
    config1 = base_config.copy()
    config1["regime_filter_enabled"] = False
    r1 = run_test("6m EURUSD (No Filter)", "EURUSD", 6, config1)
    if r1: results.append(r1)

    # Test 2: 6-month EURUSD WITH regime filter
    logger.info("[2/7] Testing 6m EURUSD - WITH REGIME FILTER...")
    config2 = base_config.copy()
    config2["regime_filter_enabled"] = True
    r2 = run_test("6m EURUSD (Regime Filter)", "EURUSD", 6, config2)
    if r2: results.append(r2)

    # Test 3: 3-month EURUSD WITHOUT regime filter
    logger.info("[3/7] Testing 3m EURUSD - NO REGIME FILTER...")
    config3 = base_config.copy()
    config3["regime_filter_enabled"] = False
    r3 = run_test("3m EURUSD (No Filter)", "EURUSD", 3, config3)
    if r3: results.append(r3)

    # Test 4: 3-month EURUSD WITH regime filter
    logger.info("[4/7] Testing 3m EURUSD - WITH REGIME FILTER...")
    config4 = base_config.copy()
    config4["regime_filter_enabled"] = True
    r4 = run_test("3m EURUSD (Regime Filter)", "EURUSD", 3, config4)
    if r4: results.append(r4)

    # Test 5: 3-month GBPUSD WITHOUT regime filter
    logger.info("[5/7] Testing 3m GBPUSD - NO REGIME FILTER...")
    config5 = base_config.copy()
    config5["regime_filter_enabled"] = False
    r5 = run_test("3m GBPUSD (No Filter)", "GBPUSD", 3, config5)
    if r5: results.append(r5)

    # Test 6: 3-month GBPUSD WITH regime filter
    logger.info("[6/7] Testing 3m GBPUSD - WITH REGIME FILTER...")
    config6 = base_config.copy()
    config6["regime_filter_enabled"] = True
    r6 = run_test("3m GBPUSD (Regime Filter)", "GBPUSD", 3, config6)
    if r6: results.append(r6)

    # Test 7: 6-month EURUSD with STRICT regime filter (ADX > 25)
    logger.info("[7/7] Testing 6m EURUSD - STRICT REGIME FILTER (ADX>25)...")
    config7 = base_config.copy()
    config7["regime_filter_enabled"] = True
    config7["regime_adx_threshold"] = 25  # Stricter
    r7 = run_test("6m EURUSD (Strict Regime)", "EURUSD", 6, config7)
    if r7: results.append(r7)

    logger.info("\n" + "="*100)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*100)

    # Print table
    logger.info(f"\n{'Test Name':<35} {'Trades':<8} {'Win%':<8} {'P&L':<14} {'Exp':<10} {'PF':<6} {'DD%':<8}")
    logger.info("-" * 100)

    for r in results:
        pnl_color = "+" if r["total_pnl"] > 0 else ""
        logger.info(
            f"{r['name']:<35} {r['trades']:<8} {r['win_rate']:>6.1%} "
            f"{pnl_color}${r['total_pnl']:>10,.2f} ${r['expectancy']:>7.2f} "
            f"{r['profit_factor']:<6.2f} {r['max_dd']:>6.1%}"
        )

    # Analysis
    logger.info("\n" + "="*100)
    logger.info("ANALYSIS")
    logger.info("="*100)

    # Compare 6-month with/without regime
    baseline_6m = next((r for r in results if r["name"] == "6m EURUSD (No Filter)"), None)
    regime_6m = next((r for r in results if r["name"] == "6m EURUSD (Regime Filter)"), None)

    if baseline_6m and regime_6m:
        logger.info("\n1. REGIME FILTER IMPACT (6-month EURUSD):")
        logger.info(f"   Without Filter: ${baseline_6m['total_pnl']:,.2f} ({baseline_6m['trades']} trades)")
        logger.info(f"   With Filter:    ${regime_6m['total_pnl']:,.2f} ({regime_6m['trades']} trades)")
        improvement = regime_6m['total_pnl'] - baseline_6m['total_pnl']
        logger.info(f"   Improvement:    ${improvement:+,.2f}")

        if regime_6m['total_pnl'] > 0:
            logger.info(f"   VERDICT: REGIME FILTER MADE IT PROFITABLE!")
        elif improvement > 0:
            logger.info(f"   VERDICT: REGIME FILTER HELPED BUT STILL NEGATIVE")
        else:
            logger.info(f"   VERDICT: REGIME FILTER DID NOT HELP")

    # Compare 3-month with/without regime
    baseline_3m = next((r for r in results if r["name"] == "3m EURUSD (No Filter)"), None)
    regime_3m = next((r for r in results if r["name"] == "3m EURUSD (Regime Filter)"), None)

    if baseline_3m and regime_3m:
        logger.info("\n2. REGIME FILTER IMPACT (3-month EURUSD):")
        logger.info(f"   Without Filter: ${baseline_3m['total_pnl']:,.2f}")
        logger.info(f"   With Filter:    ${regime_3m['total_pnl']:,.2f}")
        improvement = regime_3m['total_pnl'] - baseline_3m['total_pnl']
        logger.info(f"   Improvement:    ${improvement:+,.2f}")

    # Cross-asset comparison
    gbp_no = next((r for r in results if r["name"] == "3m GBPUSD (No Filter)"), None)
    gbp_yes = next((r for r in results if r["name"] == "3m GBPUSD (Regime Filter)"), None)

    if gbp_no and gbp_yes:
        logger.info("\n3. CROSS-ASSET VALIDATION (GBPUSD):")
        logger.info(f"   Without Filter: ${gbp_no['total_pnl']:,.2f}")
        logger.info(f"   With Filter:    ${gbp_yes['total_pnl']:,.2f}")
        if gbp_yes['total_pnl'] > 0:
            logger.info(f"   VERDICT: GENERALIZES TO OTHER PAIRS")
        else:
            logger.info(f"   VERDICT: STILL NEGATIVE ON GBPUSD")

    # Final verdict
    logger.info("\n" + "="*100)
    logger.info("FINAL VERDICT")
    logger.info("="*100)

    profitable_tests = [r for r in results if r['total_pnl'] > 0]
    regime_filtered_tests = [r for r in results if "Regime" in r['name']]
    profitable_with_regime = [r for r in regime_filtered_tests if r['total_pnl'] > 0]

    logger.info(f"\nTotal Tests: {len(results)}")
    logger.info(f"Profitable Tests: {len(profitable_tests)}")
    logger.info(f"Tests with Regime Filter: {len(regime_filtered_tests)}")
    logger.info(f"Profitable WITH Regime Filter: {len(profitable_with_regime)}")

    if len(profitable_with_regime) >= 2:
        logger.info("\n>>> REGIME FILTER WORKS! Strategy is viable when market is trending.")
        logger.info(">>> Recommendation: DEPLOY WITH REGIME FILTER ENABLED")
    elif len(profitable_with_regime) == 1:
        logger.info("\n>>> REGIME FILTER HELPS but not consistently.")
        logger.info(">>> Recommendation: NEEDS MORE TUNING or LONGER TESTING")
    else:
        logger.info("\n>>> REGIME FILTER DID NOT SOLVE THE PROBLEM.")
        logger.info(">>> Recommendation: STRATEGY IS FUNDAMENTALLY FLAWED - DO NOT TRADE")

    mt5.shutdown()
    logger.info("\n" + "="*100)
    logger.info("TESTING COMPLETE")
    logger.info("="*100)


if __name__ == "__main__":
    main()
