"""Account scaling logic for Smart DD and Static DD programs."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from src.core.config import AccountCapsConfig, DrawdownModel, ScalingConfig, ProgramType

logger = logging.getLogger(__name__)


@dataclass
class ScalingEvent:
    """Record of a scaling event."""

    timestamp: datetime
    old_balance: float
    new_balance: float
    trigger_reason: str
    equity_at_trigger: float
    profit_pct: float


class ScalingManager:
    """
    Manages account scaling logic.

    Smart DD (IF):
    - Trigger: Overall gain ≥ 10%
    - Effect: Increase starting balance (as per program plan)
    - Reset DD floor to -5% of NEW starting balance

    Static DD:
    - Trigger: Gain ≥ 10% every 90 days
    - Effect: +25% starting balance increase
    """

    def __init__(
        self,
        program: ProgramType,
        drawdown_model: DrawdownModel,
        starting_balance: float,
        scaling_config: ScalingConfig,
        account_caps: AccountCapsConfig,
    ):
        """
        Initialize scaling manager.

        Args:
            program: Program type
            drawdown_model: Drawdown model (smart/static)
            starting_balance: Initial starting balance
            scaling_config: Scaling configuration
            account_caps: Global account caps
        """
        self.program = program
        self.drawdown_model = drawdown_model
        self.current_starting_balance = starting_balance
        self.original_starting_balance = starting_balance
        self.scaling_config = scaling_config
        self.account_caps = account_caps

        self.scaling_events: List[ScalingEvent] = []
        self.last_scale_date: Optional[datetime] = None

        logger.info(
            f"Scaling manager initialized: program={program.value}, "
            f"model={drawdown_model.value}, balance={starting_balance:.0f}"
        )

    def check_scaling_eligibility(
        self,
        current_equity: float,
        now: Optional[datetime] = None,
    ) -> tuple[bool, str, float]:
        """
        Check if account is eligible for scaling.

        Args:
            current_equity: Current account equity
            now: Current timestamp

        Returns:
            (eligible, reason, new_balance_if_eligible)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        profit = current_equity - self.current_starting_balance
        profit_pct = (profit / self.current_starting_balance) * 100.0

        if self.drawdown_model == DrawdownModel.SMART:
            return self._check_smart_scaling(profit_pct, current_equity)
        else:
            return self._check_static_scaling(profit_pct, current_equity, now)

    def _check_smart_scaling(
        self,
        profit_pct: float,
        current_equity: float,
    ) -> tuple[bool, str, float]:
        """Check Smart DD scaling eligibility."""
        trigger_pct = self.scaling_config.smart_dd.trigger_gain_pct

        if profit_pct < trigger_pct:
            return (
                False,
                f"Profit {profit_pct:.1f}% < trigger {trigger_pct:.0f}%",
                0.0,
            )

        # Calculate new balance (program-specific scaling plan)
        new_balance = self._calculate_scaled_balance_smart(self.current_starting_balance)

        # Check against caps
        if not self._check_caps(new_balance):
            return (
                False,
                f"Scaling to {new_balance:.0f} would exceed account caps",
                0.0,
            )

        return (
            True,
            f"Eligible: {profit_pct:.1f}% gain >= {trigger_pct:.0f}% trigger",
            new_balance,
        )

    def _check_static_scaling(
        self,
        profit_pct: float,
        current_equity: float,
        now: datetime,
    ) -> tuple[bool, str, float]:
        """Check Static DD scaling eligibility."""
        trigger_pct = self.scaling_config.static_dd.gain_pct
        interval_days = self.scaling_config.static_dd.interval_days

        # Check profit threshold
        if profit_pct < trigger_pct:
            return (
                False,
                f"Profit {profit_pct:.1f}% < trigger {trigger_pct:.0f}%",
                0.0,
            )

        # Check time interval
        if self.last_scale_date is not None:
            days_since_scale = (now - self.last_scale_date).days
            if days_since_scale < interval_days:
                remaining = interval_days - days_since_scale
                return (
                    False,
                    f"Must wait {remaining} more days (interval: {interval_days}d)",
                    0.0,
                )

        # Calculate new balance (+25%)
        scale_increment_pct = self.scaling_config.static_dd.scale_increment_pct
        new_balance = self.current_starting_balance * (1.0 + scale_increment_pct / 100.0)

        # Check against caps
        if not self._check_caps(new_balance):
            return (
                False,
                f"Scaling to {new_balance:.0f} would exceed account caps",
                0.0,
            )

        return (
            True,
            f"Eligible: {profit_pct:.1f}% gain and {interval_days}d elapsed",
            new_balance,
        )

    def _calculate_scaled_balance_smart(self, current_balance: float) -> float:
        """
        Calculate scaled balance for Smart DD programs.

        This is program-specific. For IF, typical scaling:
        - $625 -> $1,250 -> $2,500 -> $5,000 -> $10,000 -> ...
        """
        # Simplified: double the balance (adjust based on actual program plan)
        return current_balance * 2.0

    def _check_caps(self, new_balance: float) -> bool:
        """Check if new balance would violate caps."""
        # Check program-specific caps
        if self.program == ProgramType.INSTANT_FUNDING:
            return new_balance <= self.account_caps.max_instant_total
        elif self.program == ProgramType.INSTANT_FUNDING_MICRO:
            return new_balance <= self.account_caps.max_instant_micro_total
        elif self.program in (
            ProgramType.ONE_PHASE,
            ProgramType.ONE_PHASE_MICRO,
            ProgramType.TWO_PHASE,
            ProgramType.TWO_PHASE_MAX,
        ):
            return new_balance <= self.account_caps.max_challenge_total

        # Check global cap
        return new_balance <= self.account_caps.max_starting_balances_total

    def execute_scaling(
        self,
        new_balance: float,
        current_equity: float,
        reason: str,
        now: Optional[datetime] = None,
    ) -> ScalingEvent:
        """
        Execute a scaling event.

        Args:
            new_balance: New starting balance
            current_equity: Current equity at scaling
            reason: Reason for scaling
            now: Current timestamp

        Returns:
            ScalingEvent record
        """
        if now is None:
            now = datetime.now(timezone.utc)

        old_balance = self.current_starting_balance
        profit_pct = ((current_equity - old_balance) / old_balance) * 100.0

        event = ScalingEvent(
            timestamp=now,
            old_balance=old_balance,
            new_balance=new_balance,
            trigger_reason=reason,
            equity_at_trigger=current_equity,
            profit_pct=profit_pct,
        )

        self.current_starting_balance = new_balance
        self.last_scale_date = now
        self.scaling_events.append(event)

        logger.info(
            f"SCALING EXECUTED: {old_balance:.0f} -> {new_balance:.0f} "
            f"(equity: {current_equity:.2f}, profit: {profit_pct:.1f}%)"
        )

        return event

    def get_total_scaled_amount(self) -> float:
        """Get total amount scaled from original balance."""
        return self.current_starting_balance - self.original_starting_balance

    def get_scaling_history(self) -> List[ScalingEvent]:
        """Get all scaling events."""
        return self.scaling_events.copy()

    def get_summary(self) -> dict:
        """Get scaling manager summary."""
        return {
            "program": self.program.value,
            "model": self.drawdown_model.value,
            "original_balance": self.original_starting_balance,
            "current_balance": self.current_starting_balance,
            "total_scaled": self.get_total_scaled_amount(),
            "scaling_events": len(self.scaling_events),
            "last_scale_date": self.last_scale_date.isoformat() if self.last_scale_date else None,
        }
