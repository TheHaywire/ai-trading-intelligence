"""
FINAL TEST - Simple trend following on H4.
If this doesn't work, nothing will.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.simple_trend_h4 import SimpleTrendH4
from src.engine.backtester import Backtester

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test(symbol, months, config):
    """Quick test."""
    end = datetime.now()
    start = end - timedelta(days=months * 30)

    strategy = SimpleTrendH4(config=config)
    backtester = Backtester(strategy=strategy, initial_capital=10000.0, risk_per_trade_pct=1.0)
    metrics = backtester.run(symbol, "H4", start, end)

    if metrics and metrics.total_trades > 0:
        return {
            "symbol": symbol,
            "months": months,
            "trades": metrics.total_trades,
            "win_rate": metrics.win_rate,
            "pnl": metrics.total_pnl,
            "exp": metrics.expectancy,
            "pf": metrics.profit_factor,
            "dd": metrics.max_drawdown_pct,
        }
    return None


def main():
    logger.info("FINAL TEST - Simple H4 Trend Following")
    logger.info("="*60)

    if not mt5.initialize():
        return

    config = {}

    # Test matrix
    tests = [
        ("EURUSD", 12),
        ("GBPUSD", 12),
        ("EURUSD", 6),
    ]

    results = []
    for symbol, months in tests:
        logger.info(f"Testing {symbol} {months}m...")
        r = test(symbol, months, config)
        if r:
            results.append(r)
            status = "WIN" if r['pnl'] > 0 else "LOSE"
            logger.info(f"  {status}: ${r['pnl']:+,.0f} | {r['trades']} trades | {r['win_rate']:.0%} WR | PF={r['pf']:.2f}")

    logger.info("\n" + "="*60)
    logger.info(f"Profitable: {sum(1 for r in results if r['pnl'] > 0)}/{len(results)}")

    best = max(results, key=lambda x: x['pnl']) if results else None
    if best and best['pnl'] > 0:
        logger.info(f"\nBEST: {best['symbol']} {best['months']}m")
        logger.info(f"  P&L: ${best['pnl']:+,.2f}")
        logger.info(f"  Trades: {best['trades']}")
        logger.info(f"  Win%: {best['win_rate']:.1%}")
        logger.info(f"  Exp: ${best['exp']:.2f}")
        logger.info(f"  PF: {best['pf']:.2f}")
        logger.info(f"  DD: {best['dd']:.1%}")

        if best['pnl'] > 500 and best['pf'] > 1.3:
            logger.info("\n>>> VIABLE FOR PAPER TRADING")
        elif best['pnl'] > 0:
            logger.info("\n>>> MARGINAL - barely profitable")
        else:
            logger.info("\n>>> NOT VIABLE")
    else:
        logger.info("\n>>> ALL LOSING - Markets are tough")

    mt5.shutdown()


if __name__ == "__main__":
    main()
