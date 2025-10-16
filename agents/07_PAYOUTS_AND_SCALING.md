# Role: Payouts & Scaling
Implement program-specific logic.

## Payouts (`payouts.py`)
- IF funded: first eligibility at 14 days after first trade; then every 7 days following the next trade.
- Min payout: $25 and ≥1.5% of starting balance profit.
- Best-day cap (apply where relevant): One-/Two-Phase 40%; IF Micro 15%.
- Export CSV summary with range, net profit, breaches=0, and eligibility flag.

## Scaling (`scaling.py`)
- Smart DD programs:
  - On overall gain ≥10%, allow scaling event (e.g., starting balance increases by plan).
  - Reset DD floor to −5% of the NEW starting balance (profits excluded).
  - Enforce global max account and starting-balance caps (from config).
- Static DD programs:
  - Allow +25% scale every 90 days upon 10% gain.

Include deterministic unit tests for these flows.
