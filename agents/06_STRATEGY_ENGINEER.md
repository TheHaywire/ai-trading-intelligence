# Role: Strategy Engineer
Deliver two example strategies **that must pass all guards first**:

1) `trend_breakout.py`:
   - MTF bias (EMA50/200 on H1/H4)
   - ATR filter
   - Break of structure entry
   - SL at structure/ATR multiple
   - Profit taking: partial at 1R, trail at 2R, final 3R

2) `ema_trend.py`:
   - Trend-following pullback to EMA50
   - RSI divergence filter (avoid countertrend)
   - Same SL/TP framework

Both:
- Never emit orders without SL
- Provide `propose_orders(state) -> list[Order]`
- Orders then go through risk + compliance + news guards; only then route via MT5.
- Configurable via YAML.
