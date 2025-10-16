"""Backtesting CLI interface."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import TradingConfig
from src.engine.backtester import Backtester
from src.strategy.ema_trend import EMATrendStrategy
from src.strategy.mean_reversion_bands import MeanReversionBandsStrategy
from src.strategy.breakout_session_open import BreakoutSessionOpenStrategy


def run_backtest(args):
    """Run backtest command."""
    print("=" * 70)
    print("PROPSHOP IF - BACKTEST ENGINE")
    print("=" * 70)

    # Load config
    config = TradingConfig.from_yaml(args.config)
    print(f"\nConfig loaded: {args.config}")

    # Load strategy
    strategy_map = {
        "ema_trend": lambda: EMATrendStrategy("ema_trend", dict(config.strategies.ema_trend)),
        "mean_reversion_bands": lambda: MeanReversionBandsStrategy(
            "mean_reversion_bands", dict(config.strategies.mean_reversion_bands)
        ),
        "breakout_session_open": lambda: BreakoutSessionOpenStrategy(
            "breakout_session_open", dict(config.strategies.breakout_session_open)
        ),
    }

    if args.strategy not in strategy_map:
        print(f"\nError: Unknown strategy '{args.strategy}'")
        print(f"Available: {', '.join(strategy_map.keys())}")
        return 1

    strategy = strategy_map[args.strategy]()
    print(f"Strategy: {args.strategy}")

    # Parse dates
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    else:
        start_date = datetime.now() - timedelta(days=730)  # 2 years default

    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    else:
        end_date = datetime.now()

    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Initial capital: ${args.initial_capital:,.2f}")
    print(f"Risk per trade: {args.risk_pct}%")

    # Initialize backtester
    backtester = Backtester(
        strategy=strategy,
        initial_capital=args.initial_capital,
        risk_per_trade_pct=args.risk_pct,
        spread_pips=args.spread_pips,
        slippage_pips=args.slippage_pips,
        commission_per_lot=args.commission,
    )

    print("\nRunning backtest...")
    print("-" * 70)

    # Run backtest
    metrics = backtester.run(args.symbol, args.timeframe, start_date, end_date)

    if not metrics:
        print("\nBacktest failed - check logs")
        return 1

    # Display results
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)

    results = metrics.to_dict()
    for key, value in results.items():
        print(f"{key.replace('_', ' ').title():.<50} {value}")

    # Export trades if requested
    if args.export:
        export_path = f"runs/backtests/{args.strategy}_{args.symbol}_{args.timeframe}_{start_date.date()}_to_{end_date.date()}.csv"
        Path(export_path).parent.mkdir(parents=True, exist_ok=True)
        backtester.export_trades(export_path)
        print(f"\nTrades exported to: {export_path}")

    # Verdict
    print("\n" + "=" * 70)
    if metrics.win_rate >= 0.50 and metrics.profit_factor >= 1.5 and metrics.sharpe_ratio >= 1.0:
        print("[PASS] Strategy shows positive expectancy - APPROVED for live trading")
    elif metrics.win_rate >= 0.45 and metrics.profit_factor >= 1.2:
        print("[WARN] Strategy marginal - consider optimization or different parameters")
    else:
        print("[FAIL] Strategy underperforming - DO NOT use live")

    print("=" * 70)

    return 0


def main():
    parser = argparse.ArgumentParser(description="Backtest trading strategies")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/example_if_100k_profitmax.yaml",
        help="Config file path",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        required=True,
        choices=["ema_trend", "mean_reversion_bands", "breakout_session_open"],
        help="Strategy to backtest",
    )
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Symbol to trade")
    parser.add_argument("--timeframe", type=str, default="H1", help="Timeframe (H1, H4, D1)")
    parser.add_argument(
        "--start-date", type=str, help="Start date (YYYY-MM-DD), default: 2 years ago"
    )
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD), default: today")
    parser.add_argument(
        "--initial-capital", type=float, default=100000.0, help="Initial capital"
    )
    parser.add_argument("--risk-pct", type=float, default=2.0, help="Risk % per trade")
    parser.add_argument("--spread-pips", type=float, default=2.0, help="Average spread in pips")
    parser.add_argument(
        "--slippage-pips", type=float, default=1.0, help="Average slippage in pips"
    )
    parser.add_argument(
        "--commission", type=float, default=7.0, help="Commission per lot (round trip)"
    )
    parser.add_argument("--export", action="store_true", help="Export trades to CSV")

    args = parser.parse_args()

    return run_backtest(args)


if __name__ == "__main__":
    sys.exit(main())
