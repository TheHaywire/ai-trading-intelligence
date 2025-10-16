# Role: Software Architect
Design a clean, testable repo with type hints and docstrings. Use Python 3.11, pytest, pydantic, FastAPI (for optional dashboard), and MT5 Python package.

## Deliver
1) Repo tree & files
2) pyproject.toml (ruff, black, pytest)
3) src package layout and module contracts
4) Dependency-light utilities

## Required Structure
instant_bot/
  README.md
  pyproject.toml
  src/
    core/
      broker_mt5.py
      symbols.py
      positions.py
      risk_engine.py
      compliance_guard.py
      news_guard.py
      dd_tracker.py
      lots_cap.py
      payouts.py
      scaling.py
      telemetry.py
      persistence.py
      config.py
    strategy/
      loader.py
      trend_breakout.py
      ema_trend.py
    ui/
      cli.py
      dashboard_api.py
    utils/
      timebox.py
      calc.py
      calendars.py
      throttle.py
  configs/
    example_if_100k.yaml
    lot_caps.yaml
    news_events_seed.json
  tests/
    test_drawdown.py
    test_daily_dd.py
    test_news_window.py
    test_hft_holdtime.py
    test_lot_caps.py
    test_overleveraging.py
    test_payouts_scheduler.py
    test_scaling.py
  scripts/
    run_paper.sh
    run_live.sh
    export_daily_report.py

## Coding Standards
- mypy clean, ruff/black compliant
- No seaborn; matplotlib only if charts needed (not required)
- Pure-Python, no heavy frameworks beyond FastAPI (optional) and pydantic
- Config-first: everything tunable via YAML

## Key Contracts (summaries)
- broker_mt5: connect/login, symbol info, place/modify/close, positions feed.
- dd_tracker: smart/static DD floors and utilization.
- risk_engine: per-idea risk %, daily DD & cumulative DD checks.
- compliance_guard: HFT min-hold, trade-rate throttle, grid/martingale limits, copy-trading prevention hooks.
- news_guard: block windows by symbol set; add-on toggle.
- lots_cap: cumulative lot caps by program & starting balance; class-aware aggregation.
- payouts: schedule/eligibility and CSV export.
- scaling: smart/static behavior, caps.
- telemetry: structured logs, CSV reports.
- loader + strategies: example plugin strategies routed through guards.
- config: pydantic models loading from YAML.

Provide file contents ready to save.
