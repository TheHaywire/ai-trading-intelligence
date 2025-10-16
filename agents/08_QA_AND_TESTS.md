# Role: QA & Tests
Provide pytest suite covering:

1) Smart DD lock/scale behavior
2) Static DD loss bounds
3) Daily DD halt at 80% utilization
4) News blackout ±240s logic, impacted symbols only
5) HFT min hold and trade-rate throttle
6) Lot caps per program/balance
7) Martingale rules by program
8) Payout eligibility timeline & thresholds
9) Inactivity closure at 60 days
10) Reduce-only engagement & release

Include factories/mocks for broker data and clock control (freezegun-like pattern or manual time injection).
