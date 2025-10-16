"""
Test the IMPROVED multi-factor regime filter.

This tests the new regime detection that uses:
1. ADX (trend strength)
2. Trend Consistency (key differentiator!)
3. Reversal Rate (choppiness)
4. Volatility (ATR)
5. Bollinger Width (range)

The filter uses a scoring system (0-100) to classify regimes.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.momentum_matrix import MomentumMatrixTrader
from src.engine.backtester import Backtester

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def run_test(name, symbol, start_date, end_date, config):
    """Run single backtest."""
    logger.info(f"[{name}] Testing {symbol} from {start_date.date()} to {end_date.date()}...")

    strategy = MomentumMatrixTrader(config=config)
    backtester = Backtester(strategy=strategy, initial_capital=10000.0, risk_per_trade_pct=0.5)
    metrics = backtester.run(symbol, "H1", start_date, end_date)

    if metrics:
        return {
            "name": name,
            "symbol": symbol,
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
    """Run improved regime filter tests."""
    logger.info("="*80)
    logger.info("TESTING IMPROVED MULTI-FACTOR REGIME FILTER")
    logger.info("="*80)
    logger.info("\nNew filter uses:")
    logger.info("  1. ADX (trend strength) - 30 points max")
    logger.info("  2. Trend Consistency - 40 points max (KEY FACTOR)")
    logger.info("  3. Reversal Rate - 20 points max")
    logger.info("  4. Volatility (ATR) - 10 points max")
    logger.info("  5. Bollinger Width - (calculated but not scored yet)")
    logger.info("\n  Score >= 70: Trending (trade)")
    logger.info("  Score 50-69: Moderate (trade)")
    logger.info("  Score < 50: Ranging (NO TRADE)")

    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return

    logger.info(f"\nMT5 connected: {mt5.version()}")

    # Base config (optimized settings)
    base_config = {
        "threshold": 5,
        "weights": {
            "trend": 1,
            "momentum": 0,
            "price_action": 4,
            "mtf_confluence": 2,
            "volatility": 1,
            "intermarket": 1,
            "session": 1
        },
        "session_filter_enabled": True,
        "ny_only_mode": True,
    }

    end_date = datetime.now()

    # Define test periods
    tests = []

    # Test 1: April-June (BAD PERIOD) with improved filter
    april_start = datetime(2025, 4, 1)
    june_end = datetime(2025, 6, 30, 23, 59, 59)

    # Test 2: July-October (GOOD PERIOD) with improved filter
    july_start = datetime(2025, 7, 1)
    oct_end = end_date

    # Test 3: Full 6 months with improved filter
    six_month_start = april_start

    logger.info("\n" + "="*80)
    logger.info("RUNNING TESTS")
    logger.info("="*80)

    results = []

    # Test 1: 6-month WITHOUT improved filter (baseline)
    logger.info("\n[1/5] 6-month EURUSD - NO FILTER (baseline)")
    config1 = base_config.copy()
    config1["regime_filter_enabled"] = False
    r1 = run_test("6m No Filter", "EURUSD", six_month_start, end_date, config1)
    if r1: results.append(r1)

    # Test 2: 6-month WITH old simple ADX filter
    logger.info("\n[2/5] 6-month EURUSD - OLD ADX FILTER")
    config2 = base_config.copy()
    config2["regime_filter_enabled"] = True
    config2["use_improved_regime_filter"] = False  # Use old simple filter
    r2 = run_test("6m Old Filter", "EURUSD", six_month_start, end_date, config2)
    if r2: results.append(r2)

    # Test 3: 6-month WITH new improved filter
    logger.info("\n[3/5] 6-month EURUSD - NEW IMPROVED FILTER")
    config3 = base_config.copy()
    config3["regime_filter_enabled"] = True
    r3 = run_test("6m NEW Filter", "EURUSD", six_month_start, end_date, config3)
    if r3: results.append(r3)

    # Test 4: April-June only (bad period) with improved filter
    logger.info("\n[4/5] April-June EURUSD - NEW IMPROVED FILTER")
    config4 = base_config.copy()
    config4["regime_filter_enabled"] = True
    r4 = run_test("Apr-Jun NEW Filter", "EURUSD", april_start, june_end, config4)
    if r4: results.append(r4)

    # Test 5: July-Oct only (good period) with improved filter
    logger.info("\n[5/5] July-Oct EURUSD - NEW IMPROVED FILTER")
    config5 = base_config.copy()
    config5["regime_filter_enabled"] = True
    r5 = run_test("Jul-Oct NEW Filter", "EURUSD", july_start, oct_end, config5)
    if r5: results.append(r5)

    # Results table
    logger.info("\n" + "="*80)
    logger.info("RESULTS COMPARISON")
    logger.info("="*80)

    logger.info(f"\n{'Test Name':<25} {'Trades':<8} {'Win%':<8} {'P&L':<14} {'Exp':<10} {'PF':<6} {'DD%':<8}")
    logger.info("-" * 80)

    for r in results:
        pnl_str = f"+${r['total_pnl']:,.2f}" if r['total_pnl'] > 0 else f"${r['total_pnl']:,.2f}"
        logger.info(
            f"{r['name']:<25} {r['trades']:<8} {r['win_rate']:>6.1%} "
            f"{pnl_str:>13} ${r['expectancy']:>7.2f} "
            f"{r['profit_factor']:<6.2f} {r['max_dd']:>6.1%}"
        )

    # Analysis
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS")
    logger.info("="*80)

    # Find results
    no_filter = next((r for r in results if "No Filter" in r['name']), None)
    old_filter = next((r for r in results if "Old Filter" in r['name']), None)
    new_filter = next((r for r in results if "NEW Filter" in r['name'] and "6m" in r['name']), None)

    if no_filter and old_filter and new_filter:
        logger.info("\n1. FILTER COMPARISON (6-month EURUSD):")
        logger.info(f"   No Filter:     ${no_filter['total_pnl']:>9,.2f} ({no_filter['trades']} trades)")
        logger.info(f"   Old Filter:    ${old_filter['total_pnl']:>9,.2f} ({old_filter['trades']} trades)")
        logger.info(f"   NEW Filter:    ${new_filter['total_pnl']:>9,.2f} ({new_filter['trades']} trades)")

        improvement_old = old_filter['total_pnl'] - no_filter['total_pnl']
        improvement_new = new_filter['total_pnl'] - no_filter['total_pnl']

        logger.info(f"\n   Old Filter Improvement: ${improvement_old:+,.2f}")
        logger.info(f"   NEW Filter Improvement: ${improvement_new:+,.2f}")

        if improvement_new > improvement_old:
            delta = improvement_new - improvement_old
            logger.info(f"\n   NEW filter is ${delta:+,.2f} BETTER than old filter!")
        else:
            delta = improvement_old - improvement_new
            logger.info(f"\n   Old filter was ${delta:+,.2f} better (NEW filter needs work)")

        if new_filter['total_pnl'] > 0:
            logger.info(f"\n   VERDICT: NEW FILTER MADE STRATEGY PROFITABLE!")
        elif new_filter['total_pnl'] > no_filter['total_pnl']:
            logger.info(f"\n   VERDICT: NEW FILTER HELPED BUT STILL NEGATIVE")
        else:
            logger.info(f"\n   VERDICT: NEW FILTER DID NOT HELP")

    # Period-specific analysis
    apr_jun = next((r for r in results if "Apr-Jun" in r['name']), None)
    jul_oct = next((r for r in results if "Jul-Oct" in r['name']), None)

    if apr_jun and jul_oct:
        logger.info("\n2. PERIOD-SPECIFIC PERFORMANCE:")
        logger.info(f"   April-June (bad period): ${apr_jun['total_pnl']:,.2f} ({apr_jun['trades']} trades)")
        logger.info(f"   July-Oct (good period):  ${jul_oct['total_pnl']:,.2f} ({jul_oct['trades']} trades)")

        if apr_jun['total_pnl'] > -500 and jul_oct['total_pnl'] > 0:
            logger.info(f"\n   SUCCESS: Filter blocked bad period and allowed good period!")
        elif apr_jun['trades'] < jul_oct['trades'] * 0.3:
            logger.info(f"\n   PARTIAL SUCCESS: Filter blocked most of bad period")
        else:
            logger.info(f"\n   Filter needs more tuning to separate good vs bad periods")

    # Final verdict
    logger.info("\n" + "="*80)
    logger.info("FINAL VERDICT")
    logger.info("="*80)

    if new_filter:
        if new_filter['total_pnl'] > 0:
            logger.info("\n>>> SUCCESS! NEW IMPROVED REGIME FILTER MADE STRATEGY PROFITABLE!")
            logger.info(f">>> 6-month P&L: ${new_filter['total_pnl']:+,.2f}")
            logger.info(f">>> Expectancy: ${new_filter['expectancy']:+.2f}")
            logger.info(f">>> Win Rate: {new_filter['win_rate']:.1%}")
            logger.info(f">>> Profit Factor: {new_filter['profit_factor']:.2f}")
            logger.info("\n>>> RECOMMENDATION: PROCEED TO PAPER TRADING")
        elif new_filter['total_pnl'] > -500:
            logger.info("\n>>> CLOSE! Strategy near breakeven with improved filter.")
            logger.info(f">>> 6-month P&L: ${new_filter['total_pnl']:,.2f}")
            logger.info("\n>>> RECOMMENDATION: Further tuning needed, or consider paper trading with caution")
        else:
            logger.info("\n>>> INSUFFICIENT: Improved filter helped but strategy still losing.")
            logger.info(f">>> 6-month P&L: ${new_filter['total_pnl']:,.2f}")
            logger.info("\n>>> RECOMMENDATION: Consider pivoting to different approach")

    mt5.shutdown()
    logger.info("\n" + "="*80)
    logger.info("TESTING COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
