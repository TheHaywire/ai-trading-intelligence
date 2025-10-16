# Role: Live Health Monitor
Extend `telemetry.py` + `dashboard_api.py`:

- "Breach Probability Nowcast": compute probability of hitting 80% of daily DD in next N hours based on recent vol.
- "Alpha Drift" alert: if 30d expectancy falls > 40% vs 180d baseline, cut `risk_mult *= 0.8`.
- "Fill Quality" report: track slippage distribution; widen/tighten routing accordingly.
- "Payout Horizon" card: shows next eligible date, suggested de-risk level.
