# Role: Session Playbooks (FX/Indices)
Session filters (configurable):
- Asia: mean-reversion bias on FX majors; block thin crosses.
- London: trend/breakout primary; enable execution alpha.
- NY: continuation or reversal post-news; enforce stricter slippage budgets around 13:30–15:00 UTC.

Create `session_filters.py` and wire to strategy loader + execution router.
