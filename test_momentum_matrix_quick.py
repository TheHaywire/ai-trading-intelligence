"""
Quick test of Momentum Matrix Trader with small dataset.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.momentum_matrix import MomentumMatrixTrader
from src.engine.backtester import Backtester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Quick test."""
    logger.info("Quick test: Momentum Matrix Trader")

    # Initialize MT5
    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return

    logger.info(f"MT5 connected: {mt5.version()}")

    # Test configuration
    symbol = "EURUSD"  # Using EURUSD since XAUUSD may not have data
    timeframe = "M15"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 1 month for more trades

    logger.info(f"Testing {symbol} {timeframe} from {start_date.date()} to {end_date.date()}")

    # Create strategy (lower threshold for testing)
    strategy = MomentumMatrixTrader(config={
        "threshold": 2,  # Lower threshold to get more trades in test
        "weights": {
            "trend": 2,
            "momentum": 1,
            "price_action": 2,
            "mtf_confluence": 3,
            "volatility": 1,
            "intermarket": 2,
            "session": 1
        }
    })

    logger.info(f"Strategy created: {strategy.name}")

    # Create backtester
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        risk_per_trade_pct=0.5
    )

    logger.info("Running backtest...")

    try:
        metrics = backtester.run(symbol, timeframe, start_date, end_date)

        if metrics:
            logger.info("\nBacktest Results:")
            logger.info(f"  Total Trades: {metrics.total_trades}")
            logger.info(f"  Win Rate: {metrics.win_rate:.1%}")
            logger.info(f"  Total P&L: ${metrics.total_pnl:,.2f}")
            logger.info(f"  Expectancy: ${metrics.expectancy:.2f}")
            logger.info(f"  Profit Factor: {metrics.profit_factor:.2f}")
            logger.info(f"  Max Drawdown: {metrics.max_drawdown_pct:.1%}")
            logger.info(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")

            # Show sample trades
            if backtester.trades:
                logger.info(f"\nSample Trades (first 3):")
                for i, trade in enumerate(backtester.trades[:3]):
                    logger.info(f"  Trade {i+1}:")
                    logger.info(f"    Entry: {trade.entry_time} @ ${trade.entry_price:.2f}")
                    logger.info(f"    Exit: {trade.exit_time} @ ${trade.exit_price:.2f}")
                    logger.info(f"    P&L: ${trade.pnl:.2f} ({trade.pnl_pct:+.2%})")
                    logger.info(f"    Reason: {trade.exit_reason}")

            logger.info("\n✓ Quick test PASSED")
        else:
            logger.warning("No metrics returned (possibly no data or no trades)")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

    finally:
        mt5.shutdown()
        logger.info("MT5 closed")


if __name__ == "__main__":
    main()
