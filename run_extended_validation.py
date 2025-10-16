"""
Extended validation of optimized strategy:
1. 6-month backtest on EURUSD
2. Cross-asset test on GBPUSD
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


def run_backtest(symbol, months, config):
    """Run backtest for given symbol and period."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)

    logger.info(f"\n{'='*80}")
    logger.info(f"BACKTEST: {symbol} ({months} months)")
    logger.info(f"Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"{'='*80}")

    strategy = MomentumMatrixTrader(config=config)
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        risk_per_trade_pct=0.5
    )

    metrics = backtester.run(symbol, "H1", start_date, end_date)

    if metrics:
        logger.info(f"\nResults:")
        logger.info(f"  Total Trades: {metrics.total_trades}")
        logger.info(f"  Win Rate: {metrics.win_rate:.1%}")
        logger.info(f"  Total P&L: ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:+.2%})")
        logger.info(f"  Expectancy: ${metrics.expectancy:.2f}")
        logger.info(f"  Profit Factor: {metrics.profit_factor:.2f}")
        logger.info(f"  Max Drawdown: {metrics.max_drawdown_pct:.1%}")
        logger.info(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        logger.info(f"  Final Equity: ${metrics.final_equity:,.2f}")

        return {
            "symbol": symbol,
            "months": months,
            "trades": metrics.total_trades,
            "win_rate": metrics.win_rate,
            "total_pnl": metrics.total_pnl,
            "expectancy": metrics.expectancy,
            "profit_factor": metrics.profit_factor,
            "max_dd": metrics.max_drawdown_pct,
            "sharpe": metrics.sharpe_ratio,
            "final_equity": metrics.final_equity
        }
    else:
        logger.warning(f"  No metrics returned for {symbol}")
        return None


def main():
    """Run extended validation."""
    logger.info("="*80)
    logger.info("MOMENTUM MATRIX TRADER - EXTENDED VALIDATION")
    logger.info("="*80)

    # Initialize MT5
    if not mt5.initialize():
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        return

    logger.info(f"MT5 connected: {mt5.version()}")

    # Optimized configuration
    optimized_config = {
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

    logger.info("\nOptimized Configuration:")
    logger.info(f"  Threshold: 5")
    logger.info(f"  Weights: PA-Heavy (Price Action x4)")
    logger.info(f"  Session: NY-ONLY")
    logger.info(f"  Momentum: REMOVED")

    results = []

    # Test 1: 6-month EURUSD
    logger.info("\n" + "="*80)
    logger.info("TEST 1: EURUSD 6-MONTH VALIDATION")
    logger.info("="*80)
    result1 = run_backtest("EURUSD", 6, optimized_config)
    if result1:
        results.append(result1)

    # Test 2: 3-month GBPUSD (cross-asset validation)
    logger.info("\n" + "="*80)
    logger.info("TEST 2: GBPUSD 3-MONTH (Cross-Asset Validation)")
    logger.info("="*80)
    result2 = run_backtest("GBPUSD", 3, optimized_config)
    if result2:
        results.append(result2)

    # Summary comparison
    if len(results) >= 2:
        logger.info("\n" + "="*80)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*80)

        logger.info(f"\n{'Symbol':<10} {'Period':<10} {'Trades':<8} {'Win%':<8} {'P&L':<12} {'Exp':<10} {'PF':<6} {'DD%':<8}")
        logger.info("-" * 80)

        for r in results:
            logger.info(
                f"{r['symbol']:<10} {r['months']}m{'':<7} {r['trades']:<8} "
                f"{r['win_rate']:.1%}{'':<3} ${r['total_pnl']:>9,.2f} "
                f"${r['expectancy']:>7.2f} {r['profit_factor']:<6.2f} {r['max_dd']:.1%}"
            )

        # Baseline comparison (3-month EURUSD)
        baseline_3m = {"symbol": "EURUSD", "months": 3, "total_pnl": 207.32, "win_rate": 0.382, "expectancy": 1.26}

        logger.info("\n" + "="*80)
        logger.info("ROBUSTNESS CHECK")
        logger.info("="*80)

        if results[0]["months"] == 6:
            logger.info(f"\nEURUSD 6-month vs 3-month baseline:")
            logger.info(f"  3-month P&L: ${baseline_3m['total_pnl']:,.2f}")
            logger.info(f"  6-month P&L: ${results[0]['total_pnl']:,.2f}")

            if results[0]['total_pnl'] > 0:
                logger.info(f"  Status: POSITIVE over extended period")
                if results[0]['expectancy'] > 0:
                    logger.info(f"  Verdict: ROBUST - Positive expectancy maintained")
                else:
                    logger.info(f"  Verdict: BORDERLINE - Profitable but negative expectancy")
            else:
                logger.info(f"  Status: NEGATIVE over extended period")
                logger.info(f"  Verdict: NOT ROBUST - Failed extended validation")

        if len(results) > 1 and results[1]["symbol"] == "GBPUSD":
            logger.info(f"\nCross-Asset Validation (GBPUSD):")
            logger.info(f"  P&L: ${results[1]['total_pnl']:,.2f}")
            logger.info(f"  Win Rate: {results[1]['win_rate']:.1%}")
            logger.info(f"  Expectancy: ${results[1]['expectancy']:.2f}")

            if results[1]['total_pnl'] > 0:
                logger.info(f"  Verdict: GENERALIZES - Works on other pairs")
            else:
                logger.info(f"  Verdict: PAIR-SPECIFIC - May be overfit to EURUSD")

    mt5.shutdown()
    logger.info("\n" + "="*80)
    logger.info("EXTENDED VALIDATION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
