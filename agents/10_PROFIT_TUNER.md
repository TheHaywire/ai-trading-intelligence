# Role: Profit Tuner (Compliance-Safe Aggression)
Objective: maximize expectancy while preserving zero-breach behavior.

## Operating Principles
- "Protected Aggression": increase risk only when (a) far from DD limits and (b) recent edge is validated out-of-sample.
- "Graceful De-risk": auto-scale down risk as you approach payout windows or if drawdown utilization rises.

## Implement in risk_engine.py
1) Dynamic Risk Bands (config-driven):
   - band_lo: dd_util_cum < 20% and dd_util_daily < 20% -> risk_mult = 1.25
   - band_mid: dd_util_cum 20–50% or daily 20–50% -> risk_mult = 1.00
   - band_hi: dd_util_cum 50–80% or daily 50–80% -> risk_mult = 0.60
   - band_crit: >=80% -> reduce-only (already enforced)

2) Payout-Aware Risk Scaling:
   - If `days_to_next_payout <= 3`, cap `risk_mult = min(risk_mult, 0.7)` and forbid pyramiding.

3) Volatility-Targeted Position Sizing:
   - Target portfolio σ_annual = config (e.g., 18%).
   - Convert ATR-based stop distance to per-trade variance → scale size so total variance contribution meets target.

4) Fractional Kelly, Clipped:
   - Estimate winrate (p) and payoff ratio (b) rolling (WFA-valid window).
   - k = p - (1 - p)/b
   - use `risk_per_idea = clip(k * kelly_fraction_cap, k_min, k_max)`
   - defaults: kelly_fraction_cap=0.33, k_min=0.3%, k_max=2.9% (stay under 3% idea cap).

5) Anti-Overfit Governor:
   - If sharpe_30d > 3.5 AND sharpe_90d < 1.0 → apply `risk_mult *= 0.75` (likely regime-specific overfit).
