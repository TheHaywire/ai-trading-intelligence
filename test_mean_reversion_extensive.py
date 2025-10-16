"""
Test mean reversion strategy EXTENSIVELY.

Tests:
1. 12 months EURUSD
2. 12 months GBPUSD
3. Walk-forward validation
4. Different parameter sets
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.mean_reversion import MeanReversionTrader
from src.engine.backtester import Backtester

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def run_test(name, symbol, start_date, end_date, config):
    """Run backtest."""
    logger.info(f"\n[{name}]")
    logger.info(f"  Testing {symbol} from {start_date.date()} to {end_date.date()}")

    strategy = MeanReversionTrader(config=config)
    backtester = Backtester(strategy=strategy, initial_capital=10000.0, risk_per_trade_pct=1.0)
    metrics = backtester.run(symbol, "H1", start_date, end_date)

    if metrics:
        status = "PROFIT" if metrics.total_pnl > 0 else "LOSS"
        logger.info(f"  Result: {status} - ${metrics.total_pnl:,.2f}")
        logger.info(f"  Trades: {metrics.total_trades}, Win%: {metrics.win_rate:.1%}, Exp: ${metrics.expectancy:.2f}")

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
    """Run extensive mean reversion tests."""
    logger.info("="*80)
    logger.info("MEAN REVERSION STRATEGY - EXTENSIVE TESTING")
    logger.info("="*80)
    logger.info("\nStrategy: Price overshoots → Bet on return to mean")
    logger.info("Entry: RSI extreme + Price outside 2 std dev")
    logger.info("Exit: Price returns to EMA")

    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return

    logger.info(f"\nMT5 connected: {mt5.version()}")

    # Base config
    base_config = {
        "ema_period": 20,
        "bb_std_dev": 2.0,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "session_filter": False,  # Test without filter first
    }

    # Date ranges
    end_date = datetime.now()
    start_12m = end_date - timedelta(days=365)
    start_6m = end_date - timedelta(days=180)
    mid_6m = start_12m + timedelta(days=180)

    results = []

    logger.info("\n" + "="*80)
    logger.info("TEST 1: 12-MONTH VALIDATION")
    logger.info("="*80)

    # Test 1: EURUSD 12 months
    r1 = run_test("EURUSD 12m", "EURUSD", start_12m, end_date, base_config)
    if r1: results.append(r1)

    # Test 2: GBPUSD 12 months
    r2 = run_test("GBPUSD 12m", "GBPUSD", start_12m, end_date, base_config)
    if r2: results.append(r2)

    logger.info("\n" + "="*80)
    logger.info("TEST 2: WALK-FORWARD VALIDATION")
    logger.info("="*80)

    # Test 3: First 6 months
    r3 = run_test("EURUSD First 6m", "EURUSD", start_12m, mid_6m, base_config)
    if r3: results.append(r3)

    # Test 4: Last 6 months
    r4 = run_test("EURUSD Last 6m", "EURUSD", mid_6m, end_date, base_config)
    if r4: results.append(r4)

    logger.info("\n" + "="*80)
    logger.info("TEST 3: PARAMETER VARIATIONS")
    logger.info("="*80)

    # Test 5: Tighter bands (1.5 std dev)
    config_tight = base_config.copy()
    config_tight["bb_std_dev"] = 1.5
    config_tight["rsi_overbought"] = 75
    config_tight["rsi_oversold"] = 25
    r5 = run_test("EURUSD 12m (Tight)", "EURUSD", start_12m, end_date, config_tight)
    if r5: results.append(r5)

    # Test 6: Wider bands (2.5 std dev)
    config_wide = base_config.copy()
    config_wide["bb_std_dev"] = 2.5
    config_wide["rsi_overbought"] = 65
    config_wide["rsi_oversold"] = 35
    r6 = run_test("EURUSD 12m (Wide)", "EURUSD", start_12m, end_date, config_wide)
    if r6: results.append(r6)

    # Test 7: With session filter (NY only)
    config_ny = base_config.copy()
    config_ny["session_filter"] = True
    config_ny["ny_only"] = True
    r7 = run_test("EURUSD 12m (NY-only)", "EURUSD", start_12m, end_date, config_ny)
    if r7: results.append(r7)

    # Results table
    logger.info("\n" + "="*80)
    logger.info("RESULTS SUMMARY")
    logger.info("="*80)

    logger.info(f"\n{'Test':<25} {'Trades':<8} {'Win%':<8} {'P&L':<14} {'Exp':<10} {'PF':<6}")
    logger.info("-" * 80)

    for r in results:
        pnl_str = f"+${r['total_pnl']:,.2f}" if r['total_pnl'] > 0 else f"${r['total_pnl']:,.2f}"
        logger.info(
            f"{r['name']:<25} {r['trades']:<8} {r['win_rate']:>6.1%} "
            f"{pnl_str:>13} ${r['expectancy']:>7.2f} {r['profit_factor']:<6.2f}"
        )

    # Analysis
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS")
    logger.info("="*80)

    eurusd_12m = next((r for r in results if r['name'] == "EURUSD 12m"), None)
    gbpusd_12m = next((r for r in results if r['name'] == "GBPUSD 12m"), None)

    if eurusd_12m and gbpusd_12m:
        logger.info("\n1. CROSS-ASSET VALIDATION:")
        logger.info(f"   EURUSD: ${eurusd_12m['total_pnl']:>9,.2f} ({eurusd_12m['trades']} trades)")
        logger.info(f"   GBPUSD: ${gbpusd_12m['total_pnl']:>9,.2f} ({gbpusd_12m['trades']} trades)")

        if eurusd_12m['total_pnl'] > 0 and gbpusd_12m['total_pnl'] > 0:
            logger.info("\n   SUCCESS: Profitable on BOTH pairs!")
        elif eurusd_12m['total_pnl'] > 0 or gbpusd_12m['total_pnl'] > 0:
            logger.info("\n   PARTIAL: Profitable on one pair only")
        else:
            logger.info("\n   FAILURE: Not profitable on either pair")

    # Walk-forward
    first_6m = next((r for r in results if "First 6m" in r['name']), None)
    last_6m = next((r for r in results if "Last 6m" in r['name']), None)

    if first_6m and last_6m:
        logger.info("\n2. WALK-FORWARD CONSISTENCY:")
        logger.info(f"   First 6 months: ${first_6m['total_pnl']:>9,.2f}")
        logger.info(f"   Last 6 months:  ${last_6m['total_pnl']:>9,.2f}")

        if first_6m['total_pnl'] > 0 and last_6m['total_pnl'] > 0:
            logger.info("\n   CONSISTENT: Profitable in both periods!")
        else:
            logger.info("\n   INCONSISTENT: Performance varies by period")

    # Parameter robustness
    tight = next((r for r in results if "Tight" in r['name']), None)
    wide = next((r for r in results if "Wide" in r['name']), None)

    if tight and wide and eurusd_12m:
        logger.info("\n3. PARAMETER ROBUSTNESS:")
        logger.info(f"   Baseline (2.0 std): ${eurusd_12m['total_pnl']:>9,.2f}")
        logger.info(f"   Tight (1.5 std):    ${tight['total_pnl']:>9,.2f}")
        logger.info(f"   Wide (2.5 std):     ${wide['total_pnl']:>9,.2f}")

        all_profitable = all(r['total_pnl'] > 0 for r in [eurusd_12m, tight, wide])
        if all_profitable:
            logger.info("\n   ROBUST: Profitable across all parameter sets!")
        else:
            logger.info("\n   SENSITIVE: Performance varies with parameters")

    # Final verdict
    logger.info("\n" + "="*80)
    logger.info("FINAL VERDICT")
    logger.info("="*80)

    if eurusd_12m:
        logger.info(f"\nBest Configuration: EURUSD 12-month baseline")
        logger.info(f"  P&L: ${eurusd_12m['total_pnl']:+,.2f}")
        logger.info(f"  Trades: {eurusd_12m['trades']}")
        logger.info(f"  Win Rate: {eurusd_12m['win_rate']:.1%}")
        logger.info(f"  Expectancy: ${eurusd_12m['expectancy']:.2f}")
        logger.info(f"  Profit Factor: {eurusd_12m['profit_factor']:.2f}")
        logger.info(f"  Max Drawdown: {eurusd_12m['max_dd']:.1%}")
        logger.info(f"  Sharpe: {eurusd_12m['sharpe']:.2f}")

        # Determine viability
        checks = {
            "Profitable": eurusd_12m['total_pnl'] > 0,
            "Positive Expectancy": eurusd_12m['expectancy'] > 0,
            "Profit Factor > 1.2": eurusd_12m['profit_factor'] > 1.2,
            "Max DD < 25%": eurusd_12m['max_dd'] < 0.25,
            "Adequate Sample": eurusd_12m['trades'] > 100,
        }

        logger.info(f"\nVIABILITY CHECKLIST:")
        for check, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"  [{status}] {check}")

        passed_count = sum(checks.values())
        total_checks = len(checks)

        logger.info(f"\nPassed: {passed_count}/{total_checks} checks")

        if passed_count >= 4:
            logger.info("\n>>> RECOMMENDATION: VIABLE FOR PAPER TRADING")
            logger.info(">>> Next step: Paper trade for 1-2 months, then go live if still profitable")
        elif passed_count >= 3:
            logger.info("\n>>> RECOMMENDATION: PROMISING but needs refinement")
            logger.info(">>> Consider adjusting parameters or adding filters")
        else:
            logger.info("\n>>> RECOMMENDATION: NOT READY for live trading")
            logger.info(">>> Back to drawing board or try different approach")

    mt5.shutdown()
    logger.info("\n" + "="*80)
    logger.info("TESTING COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
