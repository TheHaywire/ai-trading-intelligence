"""
Run Momentum Matrix Trader Full Analysis

This script runs a comprehensive backtest analysis with all reports.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.engine.matrix_analyzer import MomentumMatrixAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run full Momentum Matrix analysis."""
    logger.info("="*80)
    logger.info("MOMENTUM MATRIX TRADER - FULL BACKTEST ANALYSIS")
    logger.info("="*80)

    # Initialize MT5
    if not mt5.initialize():
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        return

    logger.info(f"MT5 initialized: {mt5.version()}")
    logger.info(f"MT5 account: {mt5.account_info()}")

    # Configuration
    symbol = "EURUSD"  # Use EURUSD (most reliable data)
    timeframe = "H1"   # H1 timeframe for better signals
    initial_capital = 10000.0
    risk_per_trade_pct = 0.5  # 0.5R per trade

    # Date range: Last 3 months for comprehensive analysis
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    logger.info(f"\nAnalysis Parameters:")
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Timeframe: {timeframe}")
    logger.info(f"  Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"  Initial Capital: ${initial_capital:,.2f}")
    logger.info(f"  Risk per Trade: {risk_per_trade_pct}%")

    # Create analyzer
    analyzer = MomentumMatrixAnalyzer(
        symbol=symbol,
        timeframe=timeframe,
        initial_capital=initial_capital,
        risk_per_trade_pct=risk_per_trade_pct
    )

    # Run full analysis
    try:
        output_file = f"momentum_matrix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        logger.info(f"\nGenerating comprehensive report...")
        logger.info(f"Output file: {output_file}")

        report_path = analyzer.run_full_analysis(start_date, end_date, output_file)

        logger.info(f"\n{'='*80}")
        logger.info(f"ANALYSIS COMPLETE!")
        logger.info(f"{'='*80}")
        logger.info(f"\nReport saved to: {report_path}")
        logger.info(f"\nOpen the report to view:")
        logger.info(f"  - Single trade examples with layer scoring")
        logger.info(f"  - Threshold optimization (≥2, ≥3, ≥4, ≥5)")
        logger.info(f"  - Weight optimization results")
        logger.info(f"  - Component backtests (individual layers)")
        logger.info(f"  - Ablation analysis (layer importance)")
        logger.info(f"  - Walk-forward validation")
        logger.info(f"  - Session segmentation (London/NY/Asia)")
        logger.info(f"  - Final recommended settings")
        logger.info(f"  - Next steps checklist")

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)

    finally:
        mt5.shutdown()
        logger.info("\nMT5 connection closed")


if __name__ == "__main__":
    main()
