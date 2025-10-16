# Role: DevOps & Packaging
Deliver:
- `pyproject.toml` with:
  - dependencies: pydantic, fastapi, uvicorn, pandas, numpy, python-dotenv, MetaTrader5, matplotlib (optional), pytest
  - dev: ruff, black, mypy, pytest-cov
- `scripts/run_paper.sh`: start in paper mode
- `scripts/run_live.sh`: require env vars for MT5 creds
- `scripts/export_daily_report.py`: dump CSV from telemetry
- GitHub Actions YAML (optional) for lint + test

Ensure commands:
- `pytest -q`
- `python -m src.ui.cli trade --config configs/example_if_100k.yaml --paper`
