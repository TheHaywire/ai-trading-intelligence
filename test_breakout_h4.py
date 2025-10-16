"""
Test H4 breakout strategy - last hope for something viable.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.breakout_h4 import BreakoutH4Trader
from src.engine.backtester import Backtester

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def run_test(name, symbol, start_date, end_date, config):
    """Run backtest."""
    logger.info(f"\n[{name}] {symbol}")

    # Use H4 as primary timeframe
    strategy = BreakoutH4Trader(config=config)
    backtester = Backtester(strategy=strategy, initial_capital=10000.0, risk_per_trade_pct=1.0)

    # Changed: Use H4 as analysis timeframe
    metrics = backtester.run(symbol, "H4", start_date, end_date)

    if metrics:
        status = "WIN" if metrics.total_pnl > 0 else "LOSE"
        logger.info(f"  {status}: ${metrics.total_pnl:+,.2f} | {metrics.total_trades} trades | {metrics.win_rate:.1%} win | ${metrics.expectancy:.2f} exp | PF={metrics.profit_factor:.2f}")

        return {
            "name": name,
            "symbol": symbol,
            "trades": metrics.total_trades,
            "win_rate": metrics.win_rate,
            "total_pnl": metrics.total_pnl,
            "expectancy": metrics.expectancy,
            "profit_factor": metrics.profit_factor,
            "max_dd": metrics.max_drawdown_pct,
        }
    return None


def main():
    """Test H4 breakout."""
    logger.info("="*70)
    logger.info("H4 BREAKOUT STRATEGY TEST")
    logger.info("="*70)

    if not mt5.initialize():
        logger.error(f"MT5 failed: {mt5.last_error()}")
        return

    logger.info(f"MT5: {mt5.version()}\n")

    config = {
        "lookback_period": 20,
        "adx_threshold": 20,
        "breakout_size_multiplier": 1.5,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.0,
    }

    end = datetime.now()
    start_12m = end - timedelta(days=365)
    mid = end - timedelta(days=180)

    results = []

    # Quick tests
    logger.info("TESTING...")

    r1 = run_test("12m", "EURUSD", start_12m, end, config)
    if r1: results.append(r1)

    r2 = run_test("12m", "GBPUSD", start_12m, end, config)
    if r2: results.append(r2)

    r3 = run_test("First 6m", "EURUSD", start_12m, mid, config)
    if r3: results.append(r3)

    r4 = run_test("Last 6m", "EURUSD", mid, end, config)
    if r4: results.append(r4)

    # Summary
    logger.info("\n" + "="*70)
    logger.info("RESULTS")
    logger.info("="*70)

    for r in results:
        status = "PROFIT" if r['total_pnl'] > 0 else "LOSS"
        logger.info(f"{r['symbol']} {r['name']:<12} {status:<6} ${r['total_pnl']:>9,.2f} | {r['trades']:>3} trades | PF={r['profit_factor']:.2f}")

    # Verdict
    profitable = [r for r in results if r['total_pnl'] > 0]
    logger.info(f"\nProfitable: {len(profitable)}/{len(results)}")

    if len(profitable) >= 3:
        logger.info("\n>>> VIABLE - Majority profitable")
    elif len(profitable) >= 2:
        logger.info("\n>>> MAYBE - Mixed results")
    else:
        logger.info("\n>>> NOT VIABLE - Mostly losing")

    mt5.shutdown()


if __name__ == "__main__":
    main()
