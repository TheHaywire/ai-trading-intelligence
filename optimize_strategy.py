"""Comprehensive strategy parameter optimization."""

import sys
from datetime import datetime
from itertools import product
import pandas as pd

from src.engine.backtester import Backtester
from src.strategy.ema_trend import EMATrendStrategy


def optimize_parameters():
    """Test all parameter combinations to find optimal settings."""

    # Parameter ranges to test (reduced for speed)
    param_grid = {
        "atr_multiplier": [1.5, 2.0, 3.0],
        "ema_trend_period": [20, 50, 100],
        "rsi_overbought": [70, 75, 80],
        "rsi_oversold": [20, 25, 30],
        "volume_threshold": [1.0, 1.5],  # 1.0 = disabled
        "pullback_tolerance": [0.5, 1.0],
    }

    # Generate all combinations
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(product(*values))

    total_tests = len(combinations)
    print(f"Testing {total_tests} parameter combinations...")
    print(f"This will take approximately {total_tests * 2 / 60:.1f} minutes\n")

    results = []

    for idx, combo in enumerate(combinations):
        params = dict(zip(keys, combo))

        # Create strategy with these parameters
        config = {
            "ema_trend_period": params["ema_trend_period"],
            "rsi_overbought": params["rsi_overbought"],
            "rsi_oversold": params["rsi_oversold"],
            "atr_multiplier": params["atr_multiplier"],
            "volume_threshold": params["volume_threshold"],
            "pullback_tolerance": params["pullback_tolerance"],
            "adx_period": 14,
            "atr_period": 14,
            "volume_period": 20,
        }

        # Create strategy with config
        strategy = EMATrendStrategy(config=config)

        # Run backtest
        backtester = Backtester(
            strategy=strategy,
            initial_capital=100000,
            risk_per_trade_pct=2.0,
        )

        try:
            metrics = backtester.run(
                symbol="EURUSD",
                timeframe="H1",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 10, 1),
            )

            # Store results
            results.append({
                **params,
                "trades": metrics.total_trades,
                "win_rate": metrics.win_rate * 100,  # Convert to percentage
                "profit_factor": metrics.profit_factor,
                "sharpe": metrics.sharpe_ratio,
                "max_dd_pct": metrics.max_drawdown_pct,
                "expectancy": metrics.expectancy,
                "total_pnl_pct": metrics.total_pnl_pct,
            })

            # Progress update every 50 tests
            if (idx + 1) % 50 == 0:
                print(f"Progress: {idx + 1}/{total_tests} ({(idx + 1) / total_tests * 100:.1f}%)")

        except Exception as e:
            print(f"Error with params {params}: {e}")
            continue

    # Convert to DataFrame and analyze
    df = pd.DataFrame(results)

    # Save all results
    df.to_csv("optimization_results_full.csv", index=False)
    print(f"\nFull results saved to optimization_results_full.csv")

    # Find best parameters by different criteria
    print("\n" + "=" * 80)
    print("TOP 10 BY WIN RATE:")
    print("=" * 80)
    top_wr = df.nlargest(10, "win_rate")
    print(top_wr.to_string(index=False))

    print("\n" + "=" * 80)
    print("TOP 10 BY PROFIT FACTOR:")
    print("=" * 80)
    top_pf = df.nlargest(10, "profit_factor")
    print(top_pf.to_string(index=False))

    print("\n" + "=" * 80)
    print("TOP 10 BY SHARPE RATIO:")
    print("=" * 80)
    top_sharpe = df.nlargest(10, "sharpe")
    print(top_sharpe.to_string(index=False))

    print("\n" + "=" * 80)
    print("TOP 10 BY EXPECTANCY:")
    print("=" * 80)
    top_exp = df.nlargest(10, "expectancy")
    print(top_exp.to_string(index=False))

    # Filter profitable strategies (win rate > 50%, profit factor > 1.5)
    profitable = df[(df["win_rate"] > 50) & (df["profit_factor"] > 1.5)]

    if len(profitable) > 0:
        print("\n" + "=" * 80)
        print(f"PROFITABLE STRATEGIES ({len(profitable)} found):")
        print("=" * 80)
        print(profitable.sort_values("sharpe", ascending=False).to_string(index=False))

        profitable.to_csv("optimization_results_profitable.csv", index=False)
        print(f"\nProfitable strategies saved to optimization_results_profitable.csv")
    else:
        print("\n" + "=" * 80)
        print("NO PROFITABLE STRATEGIES FOUND (win_rate > 50% AND profit_factor > 1.5)")
        print("=" * 80)

        # Show best performers that came close
        print("\nBest performing strategies (closest to profitable):")
        score = df["win_rate"] * df["profit_factor"]
        df["score"] = score
        print(df.nlargest(10, "score").to_string(index=False))


if __name__ == "__main__":
    optimize_parameters()
