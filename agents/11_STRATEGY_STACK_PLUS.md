# Role: Strategy Stack (Alpha Upgrade)
Deliver two **additional** strategies (comply with all guards):

1) `mean_reversion_bands.py`
   - Symbols: major FX + gold only during Asia/London open when spreads are tight.
   - Entry: price pierces k*ATR beyond rolling VWAP band; confirm with RSI(2) < 5 or > 95.
   - Exit: revert to VWAP, time stop 4h, hard SL at band+ATR.
   - Notes: block on red news; min hold 61s enforced.

2) `breakout_session_open.py`
   - Pre-session box (e.g., first 30 min of London).
   - Entry: break + retest; filter with H4 EMA trend alignment.
   - Partial at 1R, trail by ATR(14).
   - One re-entry allowed if stop-out and structure holds.

All orders route through risk/compliance; provide `propose_orders(state)`.
Expose toggles in YAML to enable/disable per symbol & session.
