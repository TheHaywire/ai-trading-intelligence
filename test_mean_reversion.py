"""Quick backtest for Mean Reversion strategy."""

import sys
from datetime import datetime, timedelta
from src.engine.backtester import Backtester
from src.strategy.mean_reversion_bands import MeanReversionBandsStrategy

# Mean Reversion config from yaml
mr_config = {
    "enabled": True,
    "vwap_period": 20,
    "atr_period": 14,
    "band_multiplier": 2.0,
    "rsi_period": 2,
    "rsi_oversold": 5,
    "rsi_overbought": 95,
    "max_spread_points": 8,
    "allowed_symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"],
    "allowed_sessions": ["asia", "london"],
}

print("=" * 80)
print("MEAN REVERSION STRATEGY BACKTEST")
print("=" * 80)
print("\nConfiguration:")
for key, value in mr_config.items():
    print(f"  {key}: {value}")

# Initialize strategy
strategy = MeanReversionBandsStrategy(config=mr_config)

# Test on EURUSD 2024 data (same period as EMA Trend)
backtester = Backtester(
    strategy=strategy,
    initial_capital=100000,
    risk_per_trade_pct=2.0,  # Same as EMA Trend test
    spread_pips=2.0,
    slippage_pips=1.0,
    commission_per_lot=7.0,
)

print("\n" + "=" * 80)
print("RUNNING BACKTEST: EURUSD H1 (2024-01-01 to 2024-10-01)")
print("=" * 80)

results = backtester.run(
    symbol="EURUSD",
    timeframe="H1",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 10, 1),
)

if results:
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)

    total_trades = results.total_trades
    win_rate = results.win_rate * 100  # Convert to percentage

    print(f"\nTotal Trades: {total_trades}")
    print(f"Winning Trades: {results.winning_trades}")
    print(f"Losing Trades: {results.losing_trades}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit Factor: {results.profit_factor:.2f}")
    print(f"Total P/L: {results.total_pnl_pct:.1f}%")
    print(f"Max Drawdown: {results.max_drawdown_pct:.1f}%")
    print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
    print(f"Average Win: ${results.avg_win:.2f}")
    print(f"Average Loss: ${results.avg_loss:.2f}")
    print(f"Expectancy: ${results.expectancy:.2f} per trade")

    print("\n" + "=" * 80)
    print("VERDICT:")
    print("=" * 80)

    # Compare to EMA Trend benchmarks
    ema_win_rate = 51.2
    ema_pf = 0.93

    if win_rate > 50 and results.profit_factor > 1.0:
        print("✅ STRATEGY PASSES - Better than EMA Trend baseline")
        print(f"   Win Rate: {win_rate:.1f}% vs {ema_win_rate}% (EMA Trend)")
        print(f"   Profit Factor: {results.profit_factor:.2f} vs {ema_pf:.2f} (EMA Trend)")
        if results.profit_factor > 1.5:
            print("✅ EXCELLENT - Exceeds 1.5 PF target!")
    elif win_rate > 50 or results.profit_factor > 1.0:
        print("⚠️  STRATEGY MARGINAL - Some metrics pass, some fail")
        print(f"   Win Rate: {win_rate:.1f}% (target: >50%)")
        print(f"   Profit Factor: {results.profit_factor:.2f} (target: >1.0)")
        print("   Consider optimization or disable in live trading")
    else:
        print("❌ STRATEGY FAILS - Worse than baseline")
        print(f"   Win Rate: {win_rate:.1f}% (target: >50%) - FAIL")
        print(f"   Profit Factor: {results.profit_factor:.2f} (target: >1.0) - FAIL")
        print("   ⚠️  RECOMMENDATION: DISABLE IMMEDIATELY FROM LIVE TRADING")

    print("\n" + "=" * 80)

    # Recommendation
    if win_rate < 50 or results.profit_factor < 1.0:
        print("\n🚨 CRITICAL ACTION REQUIRED:")
        print("   1. Stop live trading system")
        print("   2. Disable mean_reversion_bands in config")
        print("   3. Optimize parameters or redesign strategy")
        print("   4. Re-validate before re-enabling")
else:
    print("\n❌ Backtest failed - check errors above")
    sys.exit(1)
