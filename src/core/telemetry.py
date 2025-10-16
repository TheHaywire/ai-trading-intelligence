"""Telemetry, logging, and reporting utilities."""

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeLog:
    """Individual trade execution log."""

    timestamp: datetime
    event_type: str  # open, close, modify, reject
    ticket: Optional[int]
    symbol: str
    order_type: str
    volume: float
    price: float
    stop_loss: float
    take_profit: float
    profit: float
    commission: float
    swap: float
    idea_id: str
    strategy: str
    reason: str
    metadata: Dict[str, Any]


@dataclass
class RejectionLog:
    """Rejected order log."""

    timestamp: datetime
    symbol: str
    order_type: str
    volume: float
    rejection_reason: str
    guard_type: str  # risk, compliance, news, etc.
    metadata: Dict[str, Any]


@dataclass
class StateSnapshot:
    """Account state snapshot."""

    timestamp: datetime
    balance: float
    equity: float
    margin: float
    free_margin: float
    profit: float
    positions_count: int
    open_ideas_count: int
    dd_state: str
    dd_utilization: float
    daily_dd_utilization: float
    metadata: Dict[str, Any]


class TelemetryRecorder:
    """
    Records and persists trading telemetry.

    Maintains structured logs for:
    - Trade executions
    - Order rejections
    - Account state snapshots
    - System events
    """

    def __init__(self, logs_dir: str = "runs/logs"):
        """
        Initialize telemetry recorder.

        Args:
            logs_dir: Directory for log files
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.trade_logs: List[TradeLog] = []
        self.rejection_logs: List[RejectionLog] = []
        self.state_snapshots: List[StateSnapshot] = []

        self.session_start = datetime.now(timezone.utc)
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")

    def log_trade(
        self,
        event_type: str,
        symbol: str,
        order_type: str,
        volume: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        idea_id: str,
        strategy: str,
        reason: str = "",
        ticket: Optional[int] = None,
        profit: float = 0.0,
        commission: float = 0.0,
        swap: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a trade event."""
        log = TradeLog(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            ticket=ticket,
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            profit=profit,
            commission=commission,
            swap=swap,
            idea_id=idea_id,
            strategy=strategy,
            reason=reason,
            metadata=metadata or {},
        )
        self.trade_logs.append(log)
        logger.info(f"Trade log: {event_type} {symbol} {order_type} {volume} @ {price}")

    def log_rejection(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        rejection_reason: str,
        guard_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an order rejection."""
        log = RejectionLog(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            rejection_reason=rejection_reason,
            guard_type=guard_type,
            metadata=metadata or {},
        )
        self.rejection_logs.append(log)
        logger.warning(f"Rejection: {symbol} {order_type} - {rejection_reason} ({guard_type})")

    def log_state_snapshot(
        self,
        balance: float,
        equity: float,
        margin: float,
        free_margin: float,
        profit: float,
        positions_count: int,
        open_ideas_count: int,
        dd_state: str,
        dd_utilization: float,
        daily_dd_utilization: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an account state snapshot."""
        snapshot = StateSnapshot(
            timestamp=datetime.now(timezone.utc),
            balance=balance,
            equity=equity,
            margin=margin,
            free_margin=free_margin,
            profit=profit,
            positions_count=positions_count,
            open_ideas_count=open_ideas_count,
            dd_state=dd_state,
            dd_utilization=dd_utilization,
            daily_dd_utilization=daily_dd_utilization,
            metadata=metadata or {},
        )
        self.state_snapshots.append(snapshot)

    def export_trades_csv(self, filename: Optional[str] = None) -> Path:
        """
        Export trade logs to CSV.

        Args:
            filename: Optional filename (auto-generated if None)

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"trades_{self.session_id}.csv"

        filepath = self.logs_dir / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not self.trade_logs:
                f.write("No trades recorded\n")
                return filepath

            fieldnames = [
                "timestamp",
                "event_type",
                "ticket",
                "symbol",
                "order_type",
                "volume",
                "price",
                "stop_loss",
                "take_profit",
                "profit",
                "commission",
                "swap",
                "idea_id",
                "strategy",
                "reason",
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for log in self.trade_logs:
                row = asdict(log)
                row.pop("metadata", None)
                row["timestamp"] = log.timestamp.isoformat()
                writer.writerow(row)

        logger.info(f"Exported {len(self.trade_logs)} trades to {filepath}")
        return filepath

    def export_rejections_csv(self, filename: Optional[str] = None) -> Path:
        """
        Export rejection logs to CSV.

        Args:
            filename: Optional filename

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"rejections_{self.session_id}.csv"

        filepath = self.logs_dir / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not self.rejection_logs:
                f.write("No rejections recorded\n")
                return filepath

            fieldnames = [
                "timestamp",
                "symbol",
                "order_type",
                "volume",
                "rejection_reason",
                "guard_type",
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for log in self.rejection_logs:
                row = asdict(log)
                row.pop("metadata", None)
                row["timestamp"] = log.timestamp.isoformat()
                writer.writerow(row)

        logger.info(f"Exported {len(self.rejection_logs)} rejections to {filepath}")
        return filepath

    def export_snapshots_csv(self, filename: Optional[str] = None) -> Path:
        """
        Export state snapshots to CSV.

        Args:
            filename: Optional filename

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"snapshots_{self.session_id}.csv"

        filepath = self.logs_dir / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not self.state_snapshots:
                f.write("No snapshots recorded\n")
                return filepath

            fieldnames = [
                "timestamp",
                "balance",
                "equity",
                "margin",
                "free_margin",
                "profit",
                "positions_count",
                "open_ideas_count",
                "dd_state",
                "dd_utilization",
                "daily_dd_utilization",
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for snapshot in self.state_snapshots:
                row = asdict(snapshot)
                row.pop("metadata", None)
                row["timestamp"] = snapshot.timestamp.isoformat()
                writer.writerow(row)

        logger.info(f"Exported {len(self.state_snapshots)} snapshots to {filepath}")
        return filepath

    def export_all(self) -> Dict[str, Path]:
        """
        Export all telemetry data to CSV files.

        Returns:
            Dictionary mapping data type to file path
        """
        return {
            "trades": self.export_trades_csv(),
            "rejections": self.export_rejections_csv(),
            "snapshots": self.export_snapshots_csv(),
        }

    def get_summary(self) -> dict:
        """Get summary statistics."""
        total_trades = len(self.trade_logs)
        opens = len([t for t in self.trade_logs if t.event_type == "open"])
        closes = len([t for t in self.trade_logs if t.event_type == "close"])
        rejections = len(self.rejection_logs)

        total_profit = sum(t.profit for t in self.trade_logs if t.event_type == "close")
        total_commission = sum(t.commission for t in self.trade_logs)
        total_swap = sum(t.swap for t in self.trade_logs)

        return {
            "session_id": self.session_id,
            "session_start": self.session_start.isoformat(),
            "total_trade_events": total_trades,
            "opens": opens,
            "closes": closes,
            "rejections": rejections,
            "snapshots": len(self.state_snapshots),
            "total_profit": total_profit,
            "total_commission": total_commission,
            "total_swap": total_swap,
            "net_pnl": total_profit + total_commission + total_swap,
        }


def setup_logging(logs_dir: str = "runs/logs", level: int = logging.INFO) -> None:
    """
    Setup structured logging for the application.

    Args:
        logs_dir: Directory for log files
        level: Logging level
    """
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    # Create timestamped log file
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = logs_path / f"trading_{timestamp}.log"

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

    logger.info(f"Logging initialized: {log_file}")
