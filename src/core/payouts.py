"""Payout scheduling and eligibility logic."""

import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from src.core.config import PayoutsConfig, ProgramType

logger = logging.getLogger(__name__)


@dataclass
class PayoutPeriod:
    """Represents a payout eligibility period."""

    period_id: str
    start_date: datetime
    end_date: datetime
    first_trade_date: Optional[datetime]
    last_trade_date: Optional[datetime]
    net_profit: float
    starting_balance: float
    best_day_profit: float
    breaches: int
    eligible: bool
    reason: str


class PayoutScheduler:
    """
    Manages payout eligibility and scheduling.

    IF funded accounts:
    - First eligibility: 14 days after first trade
    - Subsequent: 7 days after next trade following payout
    - Min payout: $25 AND ≥1.5% of starting balance profit
    - Best-day cap: varies by program (40% for One/Two-Phase, 15% for IF Micro)
    """

    def __init__(
        self,
        config: PayoutsConfig,
        program: ProgramType,
        starting_balance: float,
    ):
        """
        Initialize payout scheduler.

        Args:
            config: Payout configuration
            program: Program type
            starting_balance: Account starting balance
        """
        self.config = config
        self.program = program
        self.starting_balance = starting_balance

        self.first_trade_date: Optional[datetime] = None
        self.last_payout_date: Optional[datetime] = None
        self.periods: List[PayoutPeriod] = []

        # Best-day cap by program
        self.best_day_cap_pct = self._get_best_day_cap()

        logger.info(
            f"Payout scheduler initialized: program={program.value}, "
            f"first_wait={config.first_wait_days}d, "
            f"subsequent_wait={config.subsequent_wait_days}d, "
            f"best_day_cap={self.best_day_cap_pct}%"
        )

    def _get_best_day_cap(self) -> float:
        """Get best-day cap percentage for the program."""
        if self.program == ProgramType.INSTANT_FUNDING_MICRO:
            return 15.0
        elif self.program in (
            ProgramType.ONE_PHASE,
            ProgramType.ONE_PHASE_MICRO,
            ProgramType.TWO_PHASE,
            ProgramType.TWO_PHASE_MAX,
            ProgramType.INSTANT_FUNDING,
        ):
            return 40.0
        return self.config.best_day_cap_pct

    def record_trade(self, trade_date: Optional[datetime] = None) -> None:
        """
        Record a trade execution.

        Args:
            trade_date: Trade timestamp (uses utcnow if None)
        """
        if trade_date is None:
            trade_date = datetime.now(timezone.utc)

        if self.first_trade_date is None:
            self.first_trade_date = trade_date
            logger.info(f"First trade recorded: {trade_date.isoformat()}")

    def record_payout(self, payout_date: Optional[datetime] = None) -> None:
        """
        Record a payout.

        Args:
            payout_date: Payout timestamp
        """
        if payout_date is None:
            payout_date = datetime.now(timezone.utc)

        self.last_payout_date = payout_date
        logger.info(f"Payout recorded: {payout_date.isoformat()}")

    def check_eligibility(
        self,
        current_date: Optional[datetime] = None,
        net_profit: float = 0.0,
        breaches: int = 0,
        best_day_profit: float = 0.0,
    ) -> Tuple[bool, str]:
        """
        Check payout eligibility.

        Args:
            current_date: Current date (uses utcnow if None)
            net_profit: Net profit for period
            breaches: Number of rule breaches
            best_day_profit: Profit from best single day

        Returns:
            (eligible, reason)
        """
        if current_date is None:
            current_date = datetime.now(timezone.utc)

        # No trades yet
        if self.first_trade_date is None:
            return False, "No trades executed yet"

        # Check time eligibility
        if self.last_payout_date is None:
            # First payout
            wait_days = self.config.first_wait_days
            eligible_date = self.first_trade_date + timedelta(days=wait_days)

            if current_date < eligible_date:
                remaining = (eligible_date - current_date).days
                return False, f"First payout wait period: {remaining} days remaining"
        else:
            # Subsequent payout
            wait_days = self.config.subsequent_wait_days
            eligible_date = self.last_payout_date + timedelta(days=wait_days)

            if current_date < eligible_date:
                remaining = (eligible_date - current_date).days
                return False, f"Subsequent payout wait period: {remaining} days remaining"

        # Check minimum profit amount
        min_amount = self.config.min_amount_usd
        if net_profit < min_amount:
            return False, f"Profit ${net_profit:.2f} < minimum ${min_amount:.2f}"

        # Check minimum profit percentage
        min_pct = self.config.min_profit_pct_of_start
        profit_pct = (net_profit / self.starting_balance) * 100.0
        if profit_pct < min_pct:
            return False, f"Profit {profit_pct:.2f}% < minimum {min_pct:.2f}%"

        # Check for breaches
        if breaches > 0:
            return False, f"Account has {breaches} rule breach(es)"

        # Check best-day cap (if applicable)
        if self.best_day_cap_pct > 0:
            best_day_pct = (best_day_profit / self.starting_balance) * 100.0
            if best_day_pct > self.best_day_cap_pct:
                return (
                    False,
                    f"Best day profit {best_day_pct:.1f}% exceeds cap {self.best_day_cap_pct:.0f}%",
                )

        # Eligible
        return True, "Eligible for payout"

    def create_period_report(
        self,
        period_id: str,
        start_date: datetime,
        end_date: datetime,
        net_profit: float,
        breaches: int = 0,
        best_day_profit: float = 0.0,
        first_trade: Optional[datetime] = None,
        last_trade: Optional[datetime] = None,
    ) -> PayoutPeriod:
        """
        Create a payout period report.

        Args:
            period_id: Period identifier
            start_date: Period start
            end_date: Period end
            net_profit: Net profit for period
            breaches: Rule breaches count
            best_day_profit: Best single day profit
            first_trade: First trade in period
            last_trade: Last trade in period

        Returns:
            PayoutPeriod object
        """
        eligible, reason = self.check_eligibility(
            current_date=end_date,
            net_profit=net_profit,
            breaches=breaches,
            best_day_profit=best_day_profit,
        )

        period = PayoutPeriod(
            period_id=period_id,
            start_date=start_date,
            end_date=end_date,
            first_trade_date=first_trade,
            last_trade_date=last_trade,
            net_profit=net_profit,
            starting_balance=self.starting_balance,
            best_day_profit=best_day_profit,
            breaches=breaches,
            eligible=eligible,
            reason=reason,
        )

        self.periods.append(period)
        return period

    def export_periods_csv(
        self,
        filepath: str = "runs/reports/payout_periods.csv",
    ) -> Path:
        """
        Export payout periods to CSV.

        Args:
            filepath: Output file path

        Returns:
            Path to exported file
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            if not self.periods:
                f.write("No payout periods recorded\n")
                return path

            fieldnames = [
                "period_id",
                "start_date",
                "end_date",
                "first_trade_date",
                "last_trade_date",
                "net_profit",
                "starting_balance",
                "profit_pct",
                "best_day_profit",
                "best_day_pct",
                "breaches",
                "eligible",
                "reason",
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for period in self.periods:
                profit_pct = (period.net_profit / period.starting_balance) * 100.0
                best_day_pct = (period.best_day_profit / period.starting_balance) * 100.0

                writer.writerow(
                    {
                        "period_id": period.period_id,
                        "start_date": period.start_date.isoformat(),
                        "end_date": period.end_date.isoformat(),
                        "first_trade_date": period.first_trade_date.isoformat()
                        if period.first_trade_date
                        else "",
                        "last_trade_date": period.last_trade_date.isoformat()
                        if period.last_trade_date
                        else "",
                        "net_profit": f"{period.net_profit:.2f}",
                        "starting_balance": f"{period.starting_balance:.2f}",
                        "profit_pct": f"{profit_pct:.2f}",
                        "best_day_profit": f"{period.best_day_profit:.2f}",
                        "best_day_pct": f"{best_day_pct:.2f}",
                        "breaches": period.breaches,
                        "eligible": period.eligible,
                        "reason": period.reason,
                    }
                )

        logger.info(f"Exported {len(self.periods)} payout periods to {path}")
        return path

    def get_summary(self) -> dict:
        """Get payout scheduler summary."""
        return {
            "program": self.program.value,
            "starting_balance": self.starting_balance,
            "first_trade_date": self.first_trade_date.isoformat() if self.first_trade_date else None,
            "last_payout_date": self.last_payout_date.isoformat() if self.last_payout_date else None,
            "first_wait_days": self.config.first_wait_days,
            "subsequent_wait_days": self.config.subsequent_wait_days,
            "min_amount_usd": self.config.min_amount_usd,
            "min_profit_pct": self.config.min_profit_pct_of_start,
            "best_day_cap_pct": self.best_day_cap_pct,
            "periods_recorded": len(self.periods),
        }
