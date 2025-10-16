#!/usr/bin/env python
"""Export daily trading report."""

import argparse
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Export daily trading report")
    parser.add_argument(
        "--logs-dir",
        type=str,
        default="runs/logs",
        help="Logs directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="runs/reports/daily_report.csv",
        help="Output file path",
    )

    args = parser.parse_args()

    logger.info("Exporting daily report...")
    logger.info(f"  Logs: {args.logs_dir}")
    logger.info(f"  Output: {args.output}")

    # Load telemetry from logs directory
    logs_path = Path(args.logs_dir)
    if not logs_path.exists():
        logger.error(f"Logs directory not found: {logs_path}")
        return

    # Find latest telemetry
    log_files = list(logs_path.glob("trading_*.log"))
    if not log_files:
        logger.warning("No log files found")
        return

    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Processing: {latest_log.name}")

    # Generate report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Daily Trading Report - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("=" * 60 + "\n")
        f.write(f"Log file: {latest_log.name}\n")
        f.write("\n")
        f.write("NOTE: Full report generation requires telemetry module integration\n")

    logger.info(f"Report exported to: {output_path}")


if __name__ == "__main__":
    main()
