"""Drawdown tracking with Smart DD and Static DD models."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from src.core.config import DrawdownConfig, DrawdownModel
from src.utils.calc import calculate_drawdown_percent, calculate_profit_percent

logger = logging.getLogger(__name__)


class DDState(str, Enum):
    """Drawdown state."""

    NORMAL = "normal"
    LOCKED = "locked"
    REDUCE_ONLY = "reduce_only"
    BREACHED = "breached"


@dataclass
class DDEvent:
    """Drawdown state change event."""

    timestamp: datetime
    event_type: str
    old_state: DDState
    new_state: DDState
    equity: float
    floor_value: float
    message: str


class DrawdownTracker:
    """
    Tracks drawdown limits with support for Smart DD (IF) and Static DD.

    Smart DD (Instant Funding):
    - Initial floor: -10% from starting balance
    - Lock trigger: When equity reaches +5% above starting balance
    - Locked floor: -5% from starting balance (never trails above)
    - On scaling: Reset floor to -5% of NEW starting balance

    Static DD (Challenges):
    - Fixed floor: -6% to -10% from starting balance (configurable)
    - Never changes
    """

    def __init__(
        self,
        starting_balance: float,
        config: DrawdownConfig,
        buffer_pct: float = 0.80,
    ):
        """
        Initialize drawdown tracker.

        Args:
            starting_balance: Initial account balance
            config: Drawdown configuration
            buffer_pct: Halt threshold (0.8 = halt at 80% utilization)
        """
        self.starting_balance = starting_balance
        self.config = config
        self.buffer_pct = buffer_pct

        self.current_equity = starting_balance
        self.peak_equity = starting_balance
        self.state = DDState.NORMAL

        self.events: List[DDEvent] = []

        # Initialize floor based on model
        if config.model == DrawdownModel.SMART:
            # Smart DD: Start with -10% floor
            self.floor_pct = config.smart.initial_pct
            self.floor_value = starting_balance * (1.0 - self.floor_pct)
            self.locked = False
            self.lock_threshold = starting_balance * (1.0 + config.smart.lock_after_gain_pct)
        else:
            # Static DD: Fixed floor
            self.floor_pct = config.static.max_loss_pct
            self.floor_value = starting_balance * (1.0 - self.floor_pct)
            self.locked = True  # Static DD is always "locked"
            self.lock_threshold = 0.0

        logger.info(
            f"DD Tracker initialized: model={config.model.value}, "
            f"starting_balance={starting_balance:.2f}, "
            f"floor={self.floor_value:.2f} ({self.floor_pct*100:.1f}%)"
        )

    def update(self, equity: float, balance: float, now: Optional[datetime] = None) -> None:
        """
        Update tracker with current account state.

        Args:
            equity: Current account equity
            balance: Current account balance
            now: Current timestamp (uses utcnow if None)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        old_state = self.state
        self.current_equity = equity

        # Track peak for potential trailing
        if equity > self.peak_equity:
            self.peak_equity = equity

        # Smart DD: Check for lock trigger
        if (
            self.config.model == DrawdownModel.SMART
            and not self.locked
            and equity >= self.lock_threshold
        ):
            self._lock_floor(equity, now)

        # Check for breaches and state transitions
        self._check_state(equity, now, old_state)

    def _lock_floor(self, equity: float, now: datetime) -> None:
        """Lock the DD floor (Smart DD only)."""
        old_floor = self.floor_value
        old_state = self.state

        self.locked = True
        self.floor_pct = self.config.smart.locked_pct
        self.floor_value = self.starting_balance * (1.0 - self.floor_pct)

        logger.info(
            f"DD floor LOCKED: equity={equity:.2f}, "
            f"floor={old_floor:.2f} -> {self.floor_value:.2f} "
            f"({self.floor_pct*100:.1f}%)"
        )

        event = DDEvent(
            timestamp=now,
            event_type="lock",
            old_state=old_state,
            new_state=DDState.LOCKED,
            equity=equity,
            floor_value=self.floor_value,
            message=f"DD floor locked at {self.floor_pct*100:.1f}% after reaching +5% gain",
        )
        self.events.append(event)
        self.state = DDState.LOCKED

    def _check_state(self, equity: float, now: datetime, old_state: DDState) -> None:
        """Check and update drawdown state."""
        # Check for breach
        if equity <= self.floor_value:
            if self.state != DDState.BREACHED:
                self.state = DDState.BREACHED
                self._log_event(
                    now,
                    "breach",
                    old_state,
                    DDState.BREACHED,
                    equity,
                    f"DD BREACHED: equity {equity:.2f} <= floor {self.floor_value:.2f}",
                )
                logger.error(f"DRAWDOWN BREACHED: equity={equity:.2f}, floor={self.floor_value:.2f}")
            return

        # Check for reduce-only threshold
        utilization = self.utilization_cumulative()
        reduce_only_threshold = self.floor_pct * self.buffer_pct

        distance_to_floor_pct = (equity - self.floor_value) / self.starting_balance

        if distance_to_floor_pct <= (self.floor_pct * (1.0 - self.buffer_pct)):
            if self.state != DDState.REDUCE_ONLY:
                self.state = DDState.REDUCE_ONLY
                self._log_event(
                    now,
                    "reduce_only",
                    old_state,
                    DDState.REDUCE_ONLY,
                    equity,
                    f"Reduce-only mode: utilization {utilization*100:.1f}% >= {self.buffer_pct*100:.0f}%",
                )
                logger.warning(f"REDUCE-ONLY MODE: utilization={utilization*100:.1f}%")
        else:
            if self.state == DDState.REDUCE_ONLY:
                self.state = DDState.LOCKED if self.locked else DDState.NORMAL
                self._log_event(
                    now,
                    "resume_normal",
                    old_state,
                    self.state,
                    equity,
                    f"Resumed normal trading: utilization {utilization*100:.1f}%",
                )
                logger.info("Resumed normal trading mode")

    def _log_event(
        self,
        timestamp: datetime,
        event_type: str,
        old_state: DDState,
        new_state: DDState,
        equity: float,
        message: str,
    ) -> None:
        """Log a drawdown event."""
        event = DDEvent(
            timestamp=timestamp,
            event_type=event_type,
            old_state=old_state,
            new_state=new_state,
            equity=equity,
            floor_value=self.floor_value,
            message=message,
        )
        self.events.append(event)

    def on_scale(self, new_starting_balance: float, now: Optional[datetime] = None) -> None:
        """
        Handle account scaling event.

        Args:
            new_starting_balance: New starting balance after scaling
            now: Current timestamp
        """
        if now is None:
            now = datetime.now(timezone.utc)

        old_balance = self.starting_balance
        old_floor = self.floor_value
        old_state = self.state

        self.starting_balance = new_starting_balance

        if self.config.model == DrawdownModel.SMART:
            # Smart DD: Reset to locked 5% floor on new balance
            self.floor_pct = self.config.smart.new_locked_pct
            self.floor_value = new_starting_balance * (1.0 - self.floor_pct)
            self.locked = True
            self.lock_threshold = new_starting_balance * (1.0 + self.config.smart.lock_after_gain_pct)
        else:
            # Static DD: Keep same percentage on new balance
            self.floor_value = new_starting_balance * (1.0 - self.floor_pct)

        logger.info(
            f"Account SCALED: balance {old_balance:.2f} -> {new_starting_balance:.2f}, "
            f"floor {old_floor:.2f} -> {self.floor_value:.2f}"
        )

        self._log_event(
            now,
            "scale",
            old_state,
            DDState.LOCKED if self.locked else DDState.NORMAL,
            self.current_equity,
            f"Scaled to {new_starting_balance:.2f}, new floor {self.floor_value:.2f}",
        )

    def utilization_cumulative(self) -> float:
        """
        Get cumulative DD utilization as fraction (0.0 - 1.0).

        Returns:
            Utilization fraction
        """
        if self.floor_pct == 0:
            return 0.0

        # How much of the allowed DD room have we used?
        max_allowed_loss = self.starting_balance * self.floor_pct
        current_loss = max(0.0, self.starting_balance - self.current_equity)

        return current_loss / max_allowed_loss if max_allowed_loss > 0 else 0.0

    def distance_to_floor(self) -> float:
        """
        Get distance to floor in account currency.

        Returns:
            Distance (positive if above floor, negative if breached)
        """
        return self.current_equity - self.floor_value

    def distance_to_floor_pct(self) -> float:
        """
        Get distance to floor as percentage of starting balance.

        Returns:
            Distance percentage
        """
        return (self.distance_to_floor() / self.starting_balance) * 100.0

    def is_reduce_only(self) -> bool:
        """Check if in reduce-only mode."""
        return self.state == DDState.REDUCE_ONLY

    def is_breached(self) -> bool:
        """Check if drawdown has been breached."""
        return self.state == DDState.BREACHED

    def reason(self) -> str:
        """Get current state reason message."""
        if self.state == DDState.BREACHED:
            return f"DD breached: equity {self.current_equity:.2f} <= floor {self.floor_value:.2f}"
        elif self.state == DDState.REDUCE_ONLY:
            util = self.utilization_cumulative()
            return f"Reduce-only: DD utilization {util*100:.1f}% (threshold {self.buffer_pct*100:.0f}%)"
        elif self.state == DDState.LOCKED:
            return f"DD floor locked at {self.floor_pct*100:.1f}%"
        else:
            return "Normal trading mode"

    def get_summary(self) -> dict:
        """Get summary of current drawdown state."""
        return {
            "model": self.config.model.value,
            "state": self.state.value,
            "starting_balance": self.starting_balance,
            "current_equity": self.current_equity,
            "floor_value": self.floor_value,
            "floor_pct": self.floor_pct * 100.0,
            "distance_to_floor": self.distance_to_floor(),
            "distance_to_floor_pct": self.distance_to_floor_pct(),
            "utilization": self.utilization_cumulative() * 100.0,
            "locked": self.locked,
            "breached": self.is_breached(),
            "reduce_only": self.is_reduce_only(),
            "reason": self.reason(),
        }
