# Role: Risk & Drawdown Engineer
Implement:
- Smart DD (IF): initial 10% floor; lock to 5% after +5% equity vs start; on scaling, lock to 5% of NEW scaled start; never trail above locked floor.
- Static DD (challenges/others): 6–10% from starting balance (configurable).
- Daily DD: 0–5% depending on program; halt at 80% utilization → reduce-only mode.
- Per-idea risk cap: default 2.9% (below 3% "gambling" threshold).

## Tasks
- `dd_tracker.py`: stateful class with methods:
  - update(equity, balance, now)
  - utilization_daily(), utilization_cum()
  - is_reduce_only(), reason()
  - events: on_lock(), on_scale()
- `risk_engine.py`:
  - risk_per_idea(notional, stop_distance_pts, point_value, balance) -> %
  - preflight(order) enforcing per-idea, daily DD, cumulative DD with buffers.
  - postfill check for slippage risk.
- `positions.py`: model trade ideas (group positions by idea_id).
- `config.yaml` fields: as in example; interpret daily_dd pct=0 as dormant.

Include docstrings and simple formulas in code.
