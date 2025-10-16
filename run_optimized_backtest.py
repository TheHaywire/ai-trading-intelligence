"""
Run backtest with FULL OPTIMIZATION:
- Threshold 5 (stricter entries)
- PA-Heavy weights (Price Action focused)
- NY-only session
- Remove momentum layer (zero impact)
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
    """Run fully optimized backtest."""
    logger.info("="*80)
    logger.info("MOMENTUM MATRIX TRADER - FULLY OPTIMIZED")
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
    logger.info(f"\nOptimizations Applied:")
    logger.info(f"  1. Threshold: 5 (stricter entries)")
    logger.info(f"  2. Weights: PA-Heavy (Price Action focus)")
    logger.info(f"  3. Session: NY ONLY (13:00-21:00 UTC)")
    logger.info(f"  4. Momentum layer: REMOVED (zero impact)")

    # Create fully optimized strategy
    strategy = MomentumMatrixTrader(config={
        "threshold": 5,  # Stricter
        "weights": {
            "trend": 1,
            "momentum": 0,  # Removed
            "price_action": 4,  # Heavily weighted
            "mtf_confluence": 2,
            "volatility": 1,
            "intermarket": 1,
            "session": 1
        },
        "session_filter_enabled": True,
        "ny_only_mode": True,  # NY only
    })

    logger.info(f"\nStrategy: {strategy.name} (FULLY OPTIMIZED)")

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
            logger.info("BACKTEST RESULTS - FULLY OPTIMIZED")
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
            logger.info(f"  Avg Trade Duration: {metrics.avg_trade_duration_hours:.1f} hours")

            # Calculate improvements
            baseline_pnl = -1701.38
            ny_only_pnl = -602.01

            improvement_vs_baseline = metrics.total_pnl - baseline_pnl
            improvement_vs_ny = metrics.total_pnl - ny_only_pnl

            logger.info(f"\n" + "="*80)
            logger.info("COMPARISON")
            logger.info("="*80)
            logger.info(f"\n1. BASELINE (No optimization)")
            logger.info(f"   Total P&L: ${baseline_pnl:,.2f}")
            logger.info(f"   Win Rate: 26.2%")
            logger.info(f"   Expectancy: $-10.37")
            logger.info(f"   Trades: 164")

            logger.info(f"\n2. NY-ONLY")
            logger.info(f"   Total P&L: ${ny_only_pnl:,.2f}")
            logger.info(f"   Win Rate: 34.4%")
            logger.info(f"   Expectancy: $-3.34")
            logger.info(f"   Trades: 180")
            logger.info(f"   Improvement vs Baseline: ${ny_only_pnl - baseline_pnl:+,.2f} ({(ny_only_pnl - baseline_pnl)/abs(baseline_pnl)*100:+.1f}%)")

            logger.info(f"\n3. FULLY OPTIMIZED (This run)")
            logger.info(f"   Total P&L: ${metrics.total_pnl:,.2f}")
            logger.info(f"   Win Rate: {metrics.win_rate:.1%}")
            logger.info(f"   Expectancy: ${metrics.expectancy:.2f}")
            logger.info(f"   Trades: {metrics.total_trades}")
            logger.info(f"   Improvement vs Baseline: ${improvement_vs_baseline:+,.2f} ({improvement_vs_baseline/abs(baseline_pnl)*100:+.1f}%)")
            logger.info(f"   Improvement vs NY-Only: ${improvement_vs_ny:+,.2f}")

            # Verdict
            logger.info(f"\n" + "="*80)
            if metrics.total_pnl > 0:
                logger.info("VERDICT: FULLY OPTIMIZED STRATEGY IS PROFITABLE!")
                logger.info(f"Total gain from baseline: ${improvement_vs_baseline:+,.2f}")
            elif metrics.total_pnl > ny_only_pnl:
                logger.info("VERDICT: FULLY OPTIMIZED IS BEST VERSION (Still negative but improved)")
                logger.info(f"Reduced losses by: ${improvement_vs_baseline:,.2f} ({abs(improvement_vs_baseline/baseline_pnl)*100:.1f}%)")
            elif metrics.total_pnl > baseline_pnl:
                logger.info("VERDICT: OPTIMIZATIONS HELPED, BUT NY-ONLY WAS BETTER")
            else:
                logger.info("VERDICT: OPTIMIZATIONS DID NOT IMPROVE PERFORMANCE")
            logger.info("="*80)

            # Export trades for analysis
            if backtester.trades:
                export_file = "optimized_trades.csv"
                backtester.export_trades(export_file)
                logger.info(f"\nTrades exported to: {export_file}")

        else:
            logger.warning("No metrics returned")

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)

    finally:
        mt5.shutdown()
        logger.info("\nMT5 connection closed")


if __name__ == "__main__":
    main()
