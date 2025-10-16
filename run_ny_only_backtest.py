"""
Run backtest with NY-ONLY session filter.

This tests the hypothesis that the strategy is profitable during NY session.
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run NY-only backtest."""
    logger.info("="*80)
    logger.info("MOMENTUM MATRIX TRADER - NY SESSION ONLY")
    logger.info("="*80)

    # Initialize MT5
    if not mt5.initialize():
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        return

    logger.info(f"MT5 connected: {mt5.version()}")

    # Configuration
    symbol = "EURUSD"
    timeframe = "H1"
    initial_capital = 10000.0
    risk_per_trade_pct = 0.5

    # Date range: Last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    logger.info(f"\nBacktest Parameters:")
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Timeframe: {timeframe}")
    logger.info(f"  Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"  Session Filter: NY ONLY (13:00-21:00 UTC)")

    # Create NY-only strategy
    strategy = MomentumMatrixTrader(config={
        "threshold": 3,
        "session_filter_enabled": True,
        "ny_only_mode": True,  # KEY: Only trade NY session
    })

    logger.info(f"\nStrategy: {strategy.name} (NY-ONLY MODE)")

    # Run backtest
    backtester = Backtester(
        strategy=strategy,
        initial_capital=initial_capital,
        risk_per_trade_pct=risk_per_trade_pct
    )

    logger.info("\nRunning backtest...")

    try:
        metrics = backtester.run(symbol, timeframe, start_date, end_date)

        if metrics:
            logger.info("\n" + "="*80)
            logger.info("BACKTEST RESULTS - NY SESSION ONLY")
            logger.info("="*80)
            logger.info(f"\nPerformance Metrics:")
            logger.info(f"  Total Trades: {metrics.total_trades}")
            logger.info(f"  Winning Trades: {metrics.winning_trades}")
            logger.info(f"  Losing Trades: {metrics.losing_trades}")
            logger.info(f"  Win Rate: {metrics.win_rate:.1%}")
            logger.info(f"  Total P&L: ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:+.2%})")
            logger.info(f"  Expectancy: ${metrics.expectancy:.2f}")
            logger.info(f"  Avg Win: ${metrics.avg_win:.2f}")
            logger.info(f"  Avg Loss: ${metrics.avg_loss:.2f}")
            logger.info(f"  Profit Factor: {metrics.profit_factor:.2f}")
            logger.info(f"  Max Drawdown: ${metrics.max_drawdown:,.2f} ({metrics.max_drawdown_pct:.1%})")
            logger.info(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
            logger.info(f"  Final Equity: ${metrics.final_equity:,.2f}")

            # Calculate improvement vs baseline
            baseline_pnl = -1701.38  # From original report
            baseline_trades = 164
            baseline_win_rate = 0.262
            baseline_expectancy = -10.37

            improvement_pnl = metrics.total_pnl - baseline_pnl
            improvement_trades = metrics.total_trades - baseline_trades
            improvement_wr = (metrics.win_rate - baseline_win_rate) * 100
            improvement_exp = metrics.expectancy - baseline_expectancy

            logger.info(f"\n" + "="*80)
            logger.info("COMPARISON VS BASELINE (NO SESSION FILTER)")
            logger.info("="*80)
            logger.info(f"  Baseline Total P&L: ${baseline_pnl:,.2f}")
            logger.info(f"  NY-Only Total P&L: ${metrics.total_pnl:,.2f}")
            logger.info(f"  Improvement: ${improvement_pnl:,.2f} ({improvement_pnl/abs(baseline_pnl)*100:+.1f}%)")
            logger.info(f"")
            logger.info(f"  Baseline Trades: {baseline_trades}")
            logger.info(f"  NY-Only Trades: {metrics.total_trades}")
            logger.info(f"  Change: {improvement_trades:+d} ({improvement_trades/baseline_trades*100:+.1f}%)")
            logger.info(f"")
            logger.info(f"  Baseline Win Rate: {baseline_win_rate:.1%}")
            logger.info(f"  NY-Only Win Rate: {metrics.win_rate:.1%}")
            logger.info(f"  Change: {improvement_wr:+.1f}pp")
            logger.info(f"")
            logger.info(f"  Baseline Expectancy: ${baseline_expectancy:.2f}")
            logger.info(f"  NY-Only Expectancy: ${metrics.expectancy:.2f}")
            logger.info(f"  Change: ${improvement_exp:+.2f}")

            # Verdict
            logger.info(f"\n" + "="*80)
            if metrics.total_pnl > 0:
                logger.info("VERDICT: NY-ONLY STRATEGY IS PROFITABLE!")
            elif metrics.expectancy > baseline_expectancy:
                logger.info("VERDICT: NY-ONLY STRATEGY IMPROVED BUT STILL NEGATIVE")
            else:
                logger.info("VERDICT: NY-ONLY FILTER DID NOT IMPROVE PERFORMANCE")
            logger.info("="*80)

        else:
            logger.warning("No metrics returned")

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)

    finally:
        mt5.shutdown()
        logger.info("\nMT5 connection closed")


if __name__ == "__main__":
    main()
