# Role: Execution Alpha (Non-HFT, Spread-Aware)
Within `broker_mt5.py` + `compliance_guard.py`:

1) Smart Limit Routing
   - If spread <= spread_threshold and queue depth (proxy via tick volume delta) improving -> use passive limit with 3s timeout, then flip to market-if-touched.
   - Else immediate-or-cancel market with max slippage ticks from config.

2) Adaptive Slippage Budget
   - Tighten slippage near news windows, widen during liquid sessions (London/NY overlap).

3) TWAP for Scale-ins
   - Split adds over N slices with min 65s separation (respect min-hold & no-HFT).

4) Spread/Commission Filter
   - Reject entries when (spread_in_points > spread_cap_points) or (commission impact > X% of stop distance).
