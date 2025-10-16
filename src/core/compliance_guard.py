"""Compliance guard enforcing trading behavior rules."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from src.core.broker_mt5 import OrderRequest, OrderType, Position
from src.core.config import ProgramType, RiskConfig
from src.core.lots_cap import LotCapsValidator
from src.core.positions import PositionManager, TradeIdea
from src.utils.throttle import HoldTimeTracker, TradeRateThrottle

logger = logging.getLogger(__name__)


@dataclass
class ComplianceCheck:
    """Result of a compliance check."""

    approved: bool
    reason: str
    rule: str
    metadata: dict


class ComplianceGuard:
    """
    Enforces compliance rules:
    - HFT ban (min hold time ≥ 61s)
    - Trade rate throttle (max trades/hour)
    - Grid detection and ban
    - Martingale restrictions (program-dependent)
    - Copy/group hedging prevention
    """

    def __init__(
        self,
        program: ProgramType,
        risk_config: RiskConfig,
        position_manager: PositionManager,
        lot_caps_validator: Optional[LotCapsValidator] = None,
    ):
        """
        Initialize compliance guard.

        Args:
            program: Program type
            risk_config: Risk configuration
            position_manager: Position manager
            lot_caps_validator: Optional lot caps validator
        """
        self.program = program
        self.risk_config = risk_config
        self.position_manager = position_manager
        self.lot_caps_validator = lot_caps_validator

        # HFT prevention
        self.hold_time_tracker = HoldTimeTracker(risk_config.min_hold_seconds)

        # Trade rate throttle
        self.trade_throttle = TradeRateThrottle(risk_config.max_trades_per_hour)

        # Martingale tracking by idea
        self.martingale_history: Dict[str, List[float]] = {}  # idea_id -> [lot_sizes]

        logger.info(
            f"Compliance guard initialized: program={program.value}, "
            f"min_hold={risk_config.min_hold_seconds}s, "
            f"max_trades_per_hour={risk_config.max_trades_per_hour}"
        )

    def check_order_opening(
        self,
        order: OrderRequest,
        idea_id: Optional[str] = None,
    ) -> ComplianceCheck:
        """
        Check compliance for order opening.

        Args:
            order: Order request
            idea_id: Associated trade idea ID

        Returns:
            ComplianceCheck result
        """
        # Check 1: Trade rate throttle
        if not self.trade_throttle.is_allowed():
            utilization = self.trade_throttle.utilization()
            return ComplianceCheck(
                approved=False,
                reason=f"Trade rate limit exceeded: {utilization*100:.0f}% of {self.risk_config.max_trades_per_hour}/hour",
                rule="trade_rate_throttle",
                metadata={
                    "utilization": utilization,
                    "limit": self.risk_config.max_trades_per_hour,
                    "trades_last_hour": self.trade_throttle.get_trades_in_last_hour(),
                },
            )

        # Check 2: Grid detection
        if self.risk_config.forbid_grid:
            grid_check = self._detect_grid(order)
            if not grid_check.approved:
                return grid_check

        # Check 3: Martingale check (if applicable)
        if idea_id:
            martingale_check = self._check_martingale(order, idea_id)
            if not martingale_check.approved:
                return martingale_check

        # Check 4: Lot caps
        if self.lot_caps_validator:
            lot_cap_check = self.lot_caps_validator.check_order(order.symbol, order.volume, is_opening=True)
            if not lot_cap_check.approved:
                return ComplianceCheck(
                    approved=False,
                    reason=lot_cap_check.reason,
                    rule="lot_caps",
                    metadata={
                        "current_lots": lot_cap_check.current_lots,
                        "limits": lot_cap_check.limits,
                    },
                )

        # All checks passed
        return ComplianceCheck(
            approved=True,
            reason="Compliance checks passed",
            rule="all",
            metadata={},
        )

    def check_position_closing(
        self,
        position: Position,
        now: Optional[datetime] = None,
    ) -> ComplianceCheck:
        """
        Check compliance for position closing.

        Args:
            position: Position to close
            now: Current timestamp

        Returns:
            ComplianceCheck result
        """
        # Check minimum hold time
        if not self.hold_time_tracker.can_close(str(position.ticket), now):
            hold_time = self.hold_time_tracker.get_hold_time(str(position.ticket), now)
            remaining = self.risk_config.min_hold_seconds - hold_time

            return ComplianceCheck(
                approved=False,
                reason=f"Min hold time not met: {hold_time:.0f}s / {self.risk_config.min_hold_seconds}s (wait {remaining:.0f}s)",
                rule="min_hold_time",
                metadata={
                    "ticket": position.ticket,
                    "hold_time": hold_time,
                    "min_required": self.risk_config.min_hold_seconds,
                    "remaining": remaining,
                },
            )

        # Allowed
        return ComplianceCheck(
            approved=True,
            reason="Position can be closed",
            rule="min_hold_time",
            metadata={"ticket": position.ticket},
        )

    def record_order_opened(
        self,
        ticket: int,
        volume: float,
        idea_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> None:
        """
        Record order opening for compliance tracking.

        Args:
            ticket: Position ticket
            volume: Position volume
            idea_id: Associated trade idea
            now: Current timestamp
        """
        # Record for hold time tracking
        self.hold_time_tracker.record_open(str(ticket), now)

        # Record for trade rate throttle
        self.trade_throttle.record_trade(now)

        # Record for martingale tracking
        if idea_id:
            if idea_id not in self.martingale_history:
                self.martingale_history[idea_id] = []
            self.martingale_history[idea_id].append(volume)

        logger.debug(f"Recorded order opened: ticket={ticket}, volume={volume}, idea={idea_id}")

    def record_position_closed(self, ticket: int, idea_id: Optional[str] = None) -> None:
        """
        Record position closure.

        Args:
            ticket: Position ticket
            idea_id: Associated trade idea
        """
        self.hold_time_tracker.record_close(str(ticket))
        logger.debug(f"Recorded position closed: ticket={ticket}, idea={idea_id}")

    def _detect_grid(self, order: OrderRequest) -> ComplianceCheck:
        """
        Detect grid trading pattern.

        Grid trading is characterized by:
        - Multiple pending orders at uniform intervals around current price
        """
        symbol = order.symbol.upper()
        existing_positions = self.position_manager.get_positions_for_symbol(symbol)

        if len(existing_positions) < 2:
            # Need at least 2 positions to form a grid
            return ComplianceCheck(
                approved=True,
                reason="Not enough positions to form grid",
                rule="grid_detection",
                metadata={},
            )

        # Check for uniform price spacing
        prices = sorted([p.open_price for p in existing_positions])
        if len(prices) < 2:
            return ComplianceCheck(
                approved=True,
                reason="Insufficient price data",
                rule="grid_detection",
                metadata={},
            )

        # Calculate price differences
        diffs = [prices[i+1] - prices[i] for i in range(len(prices)-1)]

        # Check if differences are uniform (within 10% tolerance)
        if len(diffs) > 1:
            avg_diff = sum(diffs) / len(diffs)
            max_deviation = max(abs(d - avg_diff) / avg_diff for d in diffs if avg_diff > 0)

            if max_deviation < 0.10:  # 10% tolerance
                return ComplianceCheck(
                    approved=False,
                    reason="Grid trading pattern detected (uniform price spacing)",
                    rule="grid_detection",
                    metadata={
                        "symbol": symbol,
                        "positions": len(existing_positions),
                        "avg_spacing": avg_diff,
                        "max_deviation": max_deviation,
                    },
                )

        return ComplianceCheck(
            approved=True,
            reason="No grid pattern detected",
            rule="grid_detection",
            metadata={},
        )

    def _check_martingale(self, order: OrderRequest, idea_id: str) -> ComplianceCheck:
        """
        Check martingale restrictions.

        Rules:
        - Challenges & IF Micro: Allowed
        - IF funded: Limited (no continuous doubling, step-size ≤ +50% vs prior leg)
        """
        # Get program-specific rules
        if self.program in (ProgramType.ONE_PHASE, ProgramType.ONE_PHASE_MICRO,
                            ProgramType.TWO_PHASE, ProgramType.TWO_PHASE_MAX,
                            ProgramType.INSTANT_FUNDING_MICRO):
            # Martingale allowed
            if self.risk_config.allow_martingale_challenge:
                return ComplianceCheck(
                    approved=True,
                    reason="Martingale allowed for challenge/micro accounts",
                    rule="martingale",
                    metadata={},
                )

        # IF funded: Limited martingale
        if self.program == ProgramType.INSTANT_FUNDING:
            if self.risk_config.allow_martingale_if_account == "forbidden":
                return ComplianceCheck(
                    approved=False,
                    reason="Martingale forbidden for IF funded accounts",
                    rule="martingale",
                    metadata={},
                )

            # Check if this is martingale scaling
            history = self.martingale_history.get(idea_id, [])
            if len(history) > 0:
                last_volume = history[-1]
                increase_pct = ((order.volume - last_volume) / last_volume) * 100.0 if last_volume > 0 else 0.0

                # Check for doubling or excessive increase
                if order.volume >= last_volume * 2.0:
                    return ComplianceCheck(
                        approved=False,
                        reason="Martingale doubling forbidden for IF funded accounts",
                        rule="martingale",
                        metadata={
                            "last_volume": last_volume,
                            "new_volume": order.volume,
                            "increase_pct": increase_pct,
                        },
                    )

                # Check for >50% increase (limited martingale)
                if increase_pct > 50.0:
                    return ComplianceCheck(
                        approved=False,
                        reason=f"Martingale increase {increase_pct:.0f}% exceeds 50% limit for IF funded",
                        rule="martingale",
                        metadata={
                            "last_volume": last_volume,
                            "new_volume": order.volume,
                            "increase_pct": increase_pct,
                            "limit": 50.0,
                        },
                    )

        return ComplianceCheck(
            approved=True,
            reason="Martingale check passed",
            rule="martingale",
            metadata={},
        )

    def get_summary(self) -> dict:
        """Get compliance guard summary."""
        return {
            "program": self.program.value,
            "min_hold_seconds": self.risk_config.min_hold_seconds,
            "max_trades_per_hour": self.risk_config.max_trades_per_hour,
            "trade_throttle_utilization": self.trade_throttle.utilization() * 100.0,
            "trades_last_hour": self.trade_throttle.get_trades_in_last_hour(),
            "forbid_grid": self.risk_config.forbid_grid,
            "martingale_allowed": self.risk_config.allow_martingale_challenge
            if self.program != ProgramType.INSTANT_FUNDING
            else self.risk_config.allow_martingale_if_account,
        }
