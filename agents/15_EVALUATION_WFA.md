# Role: Evaluation & Walk-Forward Analysis
Add `backtest/` with:
- Purged & embargoed K-fold CV (avoid leakage across time).
- Walk-forward optimizer: choose params on IS window, validate on OOS; accept only if hit-rate and Sharpe within tolerance bands.
- Metrics:
  - Expectancy per trade
  - Tail risk (max adverse excursion, MAR, ulcer index)
  - Capacity (lot caps & spreads)
- Auto-reject parameter sets that raise trade-rate near HFT thresholds or lower avg hold < 3 min.
