"""
ULTIMATE OPTIMIZATION - Test 10,000+ Combinations in Parallel

This will test:
- 40+ EMA combinations (fast/slow pairs)
- 12 filter combinations (ADX, session, etc)
- 8 stop/target ratios
- = 3,840 unique strategies

Using multiprocessing to run 8 tests simultaneously.
Expected runtime: 30-60 minutes on 8-core CPU.

Will find the TOP 10 best performers and validate them.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from multiprocessing import Pool, cpu_count
import itertools

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

from src.strategy.ema_crossover import EMACrossover
from src.engine.backtester import Backtester

# Suppress logs
logging.basicConfig(level=logging.ERROR)


def test_config(params):
    """Test single configuration."""
    config, symbol, start, end = params

    try:
        # Initialize MT5 in this process
        if not mt5.initialize():
            return None

        strategy = EMACrossover(config=config)
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000.0,
            risk_per_trade_pct=1.0,
            spread_pips=1.5,
            commission_per_lot=7.0
        )

        metrics = backtester.run(symbol, "H1", start, end)

        mt5.shutdown()

        if metrics and metrics.total_trades >= 5:  # Need minimum trades
            return {
                "config": config,
                "symbol": symbol,
                "trades": metrics.total_trades,
                "win_rate": metrics.win_rate,
                "pnl": metrics.total_pnl,
                "pnl_pct": metrics.total_pnl_pct,
                "expectancy": metrics.expectancy,
                "profit_factor": metrics.profit_factor,
                "max_dd": metrics.max_drawdown_pct,
                "sharpe": metrics.sharpe_ratio,
            }
    except Exception as e:
        pass

    return None


def generate_configs():
    """Generate all parameter combinations."""

    # EMA combinations
    fast_emas = [10, 15, 20, 25, 30, 40, 50]
    slow_emas = [30, 40, 50, 55, 60, 80, 100, 150, 200]

    ema_pairs = []
    for fast in fast_emas:
        for slow in slow_emas:
            if slow > fast * 1.5:  # Slow must be at least 1.5x fast
                ema_pairs.append((fast, slow))

    # Filter combinations
    filters = [
        {"name": "None", "use_adx_filter": False, "use_session_filter": False},
        {"name": "ADX20", "use_adx_filter": True, "adx_threshold": 20, "use_session_filter": False},
        {"name": "ADX25", "use_adx_filter": True, "adx_threshold": 25, "use_session_filter": False},
        {"name": "ADX30", "use_adx_filter": True, "adx_threshold": 30, "use_session_filter": False},
        {"name": "NY", "use_adx_filter": False, "use_session_filter": True, "ny_only": True},
        {"name": "London+NY", "use_adx_filter": False, "use_session_filter": True, "ny_only": False},
        {"name": "ADX20+NY", "use_adx_filter": True, "adx_threshold": 20, "use_session_filter": True, "ny_only": True},
        {"name": "ADX25+NY", "use_adx_filter": True, "adx_threshold": 25, "use_session_filter": True, "ny_only": True},
        {"name": "ATR", "use_atr_filter": True, "atr_min_pct": 0.08, "atr_max_pct": 0.25, "use_session_filter": False},
        {"name": "ATR+NY", "use_atr_filter": True, "atr_min_pct": 0.08, "atr_max_pct": 0.25, "use_session_filter": True, "ny_only": True},
        {"name": "ATR+ADX20", "use_atr_filter": True, "atr_min_pct": 0.08, "atr_max_pct": 0.25, "use_adx_filter": True, "adx_threshold": 20, "use_session_filter": False},
        {"name": "ATR+ADX25+NY", "use_atr_filter": True, "atr_min_pct": 0.08, "atr_max_pct": 0.25, "use_adx_filter": True, "adx_threshold": 25, "use_session_filter": True, "ny_only": True},
    ]

    # Stop/Target combinations
    stop_target_pairs = [
        (1.5, 2.0),
        (1.5, 3.0),
        (2.0, 3.0),
        (2.0, 4.0),
        (2.5, 3.0),
        (2.5, 4.0),
        (2.5, 5.0),
        (3.0, 6.0),
    ]

    # Generate all combinations
    configs = []
    for (fast, slow), filter_dict, (stop, target) in itertools.product(ema_pairs, filters, stop_target_pairs):
        config = {
            "fast_ema": fast,
            "slow_ema": slow,
            "atr_stop_multiplier": stop,
            "atr_target_multiplier": target,
            **{k: v for k, v in filter_dict.items() if k != "name"}
        }

        config["_name"] = f"{fast}/{slow} {filter_dict['name']} SL{stop}:TP{target}"
        configs.append(config)

    return configs


def main():
    print("="*80)
    print("ULTIMATE OPTIMIZATION - Testing Thousands of Combinations")
    print("="*80)

    # Generate all configs
    all_configs = generate_configs()
    print(f"\nGenerated {len(all_configs)} unique strategy configurations")

    # Test periods
    end = datetime.now()
    start_12m = end - timedelta(days=365)

    # Test on both pairs
    symbols = ["EURUSD", "GBPUSD"]

    # Create parameter list for parallel execution
    print(f"\nPreparing {len(all_configs) * len(symbols)} tests...")
    print(f"Using {cpu_count()} CPU cores for parallel execution")

    test_params = []
    for config in all_configs:
        for symbol in symbols:
            test_params.append((config, symbol, start_12m, end))

    print(f"\nRunning optimization... (this will take 20-40 minutes)")
    print("Progress: ", end="", flush=True)

    # Run in parallel
    results = []
    chunk_size = 100
    total_chunks = len(test_params) // chunk_size + 1

    with Pool(processes=cpu_count()) as pool:
        for i, result in enumerate(pool.imap_unordered(test_config, test_params, chunksize=10)):
            if result:
                results.append(result)

            # Progress indicator
            if i % chunk_size == 0:
                progress = (i / len(test_params)) * 100
                print(f"{progress:.0f}%...", end="", flush=True)

    print(" DONE!\n")

    print(f"Completed {len(test_params)} tests")
    print(f"Valid results: {len(results)}")

    if not results:
        print("\nNo valid results found. Check MT5 connection and data availability.")
        return

    # Rank by multiple criteria
    print("\n" + "="*80)
    print("TOP 10 PERFORMERS - Ranked by Total P&L")
    print("="*80)

    # Sort by P&L
    results.sort(key=lambda x: x['pnl'], reverse=True)

    print(f"\n{'#':<4} {'Strategy':<45} {'Symbol':<8} {'Trades':<8} {'P&L':<12} {'PF':<6} {'WR':<6}")
    print("-" * 100)

    for i, r in enumerate(results[:10], 1):
        print(f"{i:<4} {r['config']['_name']:<45} {r['symbol']:<8} {r['trades']:<8} "
              f"${r['pnl']:>9.0f}  {r['profit_factor']:<6.2f} {r['win_rate']:>5.0%}")

    # Find configs that work on BOTH pairs
    print("\n" + "="*80)
    print("CROSS-PAIR CONSISTENCY - Strategies Profitable on BOTH Pairs")
    print("="*80)

    # Group by config name
    config_performance = {}
    for r in results:
        name = r['config']['_name']
        if name not in config_performance:
            config_performance[name] = {}
        config_performance[name][r['symbol']] = r

    # Find strategies profitable on both
    both_profitable = []
    for name, perf in config_performance.items():
        if 'EURUSD' in perf and 'GBPUSD' in perf:
            eur = perf['EURUSD']
            gbp = perf['GBPUSD']
            if eur['pnl'] > 0 and gbp['pnl'] > 0:
                combined_pnl = eur['pnl'] + gbp['pnl']
                avg_pf = (eur['profit_factor'] + gbp['profit_factor']) / 2
                both_profitable.append({
                    'name': name,
                    'config': eur['config'],
                    'eur_pnl': eur['pnl'],
                    'gbp_pnl': gbp['pnl'],
                    'combined_pnl': combined_pnl,
                    'eur_trades': eur['trades'],
                    'gbp_trades': gbp['trades'],
                    'avg_pf': avg_pf,
                })

    both_profitable.sort(key=lambda x: x['combined_pnl'], reverse=True)

    print(f"\nFound {len(both_profitable)} strategies profitable on BOTH pairs\n")

    if both_profitable:
        print(f"{'#':<4} {'Strategy':<45} {'EUR P&L':<12} {'GBP P&L':<12} {'Combined':<12} {'Avg PF':<8}")
        print("-" * 110)

        for i, s in enumerate(both_profitable[:10], 1):
            print(f"{i:<4} {s['name']:<45} ${s['eur_pnl']:>9.0f}  ${s['gbp_pnl']:>9.0f}  "
                  f"${s['combined_pnl']:>9.0f}  {s['avg_pf']:<8.2f}")

        # Best overall
        best = both_profitable[0]
        print("\n" + "="*80)
        print("WINNER - Best Strategy Across Both Pairs")
        print("="*80)
        print(f"\nStrategy: {best['name']}")
        print(f"\nEURUSD:")
        print(f"  P&L: ${best['eur_pnl']:,.0f}")
        print(f"  Trades: {best['eur_trades']}")
        print(f"\nGBPUSD:")
        print(f"  P&L: ${best['gbp_pnl']:,.0f}")
        print(f"  Trades: {best['gbp_trades']}")
        print(f"\nCombined P&L: ${best['combined_pnl']:,.0f}")
        print(f"Average Profit Factor: {best['avg_pf']:.2f}")

        # Show config
        print("\nConfiguration:")
        for key, value in best['config'].items():
            if not key.startswith('_'):
                print(f"  {key}: {value}")

        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("\n1. Save this configuration")
        print("2. Run extended validation (18-24 months if data available)")
        print("3. Paper trade for 1-2 months")
        print("4. Go live if paper trading confirms results")

    else:
        print("\nNo strategies were profitable on BOTH pairs.")
        print("This suggests:")
        print("  - Market conditions are tough")
        print("  - EMA crossover may not have edge in current regime")
        print("  - Consider different strategy types (mean reversion, breakout, etc)")

    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
