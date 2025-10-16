# Role: Portfolio Allocator (HRP + Correlation Guard)
Implement `portfolio_allocator.py` and integrate into `risk_engine`:

1) Correlation Matrix (rolling 90d, fallback 30d)
2) Hierarchical Risk Parity (HRP)
   - Allocate per-symbol risk budgets so total portfolio variance meets target.
3) Correlation Clamp
   - If |rho| > 0.8 between two open ideas, scale the later idea's risk to 50% of intended.
4) Exposure Caps
   - Per currency (e.g., USD, JPY) max concurrent risk ≤ X% of account.
