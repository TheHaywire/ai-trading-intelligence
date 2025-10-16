# Role: Market Regime Detector
Add `regime.py` and wire into strategy loader:

- Features: realized vol, trend strength (ADX, EMA slope), breadth proxy (cross-syms), macro calendar density.
- Regimes: {Trend, Choppy, High-Vol, Low-Vol}
- Router:
  - Trend → breakout, EMA-trend
  - Choppy/Low-Vol → mean reversion bands
  - High-Vol with red news density → trade fewer, widen stops, lower risk_mult 0.8

Include tests to ensure router switches strategies and risk presets deterministically.
