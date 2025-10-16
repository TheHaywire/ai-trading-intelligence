# Role: Compliance & Behavior Guard
Enforce prohibited/limited behaviors:
- HFT ban: min hold time >= 61s; closing earlier queues a delayed close.
- Trade rate throttle: configurable max trades/hour; beyond it = reduce-only.
- Grid ban (uniform ladder around current price).
- Martingale:
  - Challenges & IF Micro: allowed.
  - IF funded: limited (no continuous doubling; step-size ≤ +50% vs prior leg).
- Copy/group hedging:
  - Prevent mirrored timestamps across linked accounts; block opposite exposures within N minutes.
- Over-leveraging: enforce lot caps per program & starting balance (use lots_cap).

## Tasks
- `compliance_guard.py`:
  - check_min_hold(position, now)
  - check_trade_rate(account_history, now)
  - detect_grid(order_batch)
  - check_martingale(sequence, program_type)
  - check_copy_hedge(linked_accounts_state)
  - check_lot_caps(aggregated_positions, lot_caps_table)

All checks return (ok: bool, reason_code: str, metadata: dict).
