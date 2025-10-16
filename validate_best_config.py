"""Validate best configuration with walk-forward analysis."""

from walk_forward_validation import walk_forward_analysis

# Best config from optimization (highest score)
best_config = {
    "atr_multiplier": 3.0,
    "ema_trend_period": 50,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "volume_threshold": 1.5,
    "pullback_tolerance": 0.5,
    "adx_period": 14,
    "atr_period": 14,
    "volume_period": 20,
}

print("=" * 80)
print("WALK-FORWARD VALIDATION - BEST OPTIMIZED CONFIG")
print("=" * 80)
print(f"\nConfiguration:")
for key, value in best_config.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 80)
print("RUNNING WALK-FORWARD ANALYSIS (18 periods, 2023-2024)")
print("=" * 80)

results = walk_forward_analysis(best_config, window_months=3, forward_months=1)

if results:
    print("\n" + "=" * 80)
    print("FINAL VERDICT:")
    print("=" * 80)

    if results["avg_win_rate"] > 50 and results["avg_profit_factor"] > 1.0 and results["consistency"] > 60:
        print("✅ STRATEGY VALIDATED - Robust across multiple periods")
        print("✅ READY FOR LIVE DEPLOYMENT with proper risk management")
    elif results["avg_win_rate"] > 50 and results["avg_profit_factor"] > 1.0:
        print("⚠️  STRATEGY MARGINAL - Good averages but inconsistent")
        print("⚠️  DEPLOY WITH CAUTION - Use reduced position sizes (0.5% risk)")
    else:
        print("❌ STRATEGY FAILED VALIDATION - Not robust")
        print("❌ DO NOT DEPLOY - Needs fundamental redesign")
