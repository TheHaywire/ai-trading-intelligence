"""Risk management engine with per-idea risk and daily DD checks."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from src.core.broker_mt5 import OrderRequest, OrderType, Position
from src.core.config import DailyDrawdownConfig, RiskConfig, TradingConfig
from src.core.dd_tracker import DrawdownTracker
from src.core.positions import PositionManager
from src.core.symbols import SymbolInfo
from src.utils.calc import calculate_lot_size_for_risk, calculate_risk_percent

logger = logging.getLogger(__name__)


@dataclass
class RiskCheck:
    """Result of a risk preflight check."""

    approved: bool
    reason: str
    metadata: dict


class DailyDDTracker:
    """
    Tracks daily drawdown limits.

    Resets at the start of each trading day.
    """

    def __init__(self, config: DailyDrawdownConfig, starting_balance: float):
        """
        Initialize daily DD tracker.

        Args:
            config: Daily DD configuration
            starting_balance: Account starting balance
        """
        self.config = config
        self.starting_balance = starting_balance
        self.daily_dd_pct = config.pct
        self.halt_buffer = config.halt_buffer_pct

        # Daily tracking
        self.current_day: Optional[str] = None
        self.day_start_equity: float = starting_balance
        self.day_peak_equity: float = starting_balance
        self.day_low_equity: float = starting_balance

        # Dormant if daily_dd_pct is 0
        self.active = self.daily_dd_pct > 0

    def update(self, equity: float, now: Optional[datetime] = None) -> None:
        """
        Update daily DD tracker.

        Args:
            equity: Current equity
            now: Current timestamp
        """
        if not self.active:
            return

        if now is None:
            now = datetime.now(timezone.utc)

        today = now.strftime("%Y-%m-%d")

        # Reset on new day
        if self.current_day != today:
            self.current_day = today
            self.day_start_equity = equity
            self.day_peak_equity = equity
            self.day_low_equity = equity
            logger.info(f"Daily DD reset for {today}, start equity: {equity:.2f}")

        # Track peak and low
        if equity > self.day_peak_equity:
            self.day_peak_equity = equity

        if equity < self.day_low_equity:
            self.day_low_equity = equity

    def utilization(self) -> float:
        """
        Get daily DD utilization.

        Returns:
            Utilization fraction (0.0 - 1.0)
        """
        if not self.active or self.daily_dd_pct == 0:
            return 0.0

        # Compute based on config
        if self.config.compute_on == "equity":
            reference = self.day_start_equity
            current = self.day_low_equity
        else:  # balance
            reference = self.starting_balance
            current = self.day_low_equity

        max_allowed_loss = reference * self.daily_dd_pct
        current_loss = max(0.0, reference - current)

        return current_loss / max_allowed_loss if max_allowed_loss > 0 else 0.0

    def is_reduce_only(self) -> bool:
        """Check if daily DD has triggered reduce-only mode."""
        return self.active and self.utilization() >= self.halt_buffer

    def is_breached(self) -> bool:
        """Check if daily DD limit has been breached."""
        return self.active and self.utilization() >= 1.0

    def get_summary(self) -> dict:
        """Get daily DD summary."""
        return {
            "active": self.active,
            "current_day": self.current_day,
            "day_start_equity": self.day_start_equity,
            "day_peak_equity": self.day_peak_equity,
            "day_low_equity": self.day_low_equity,
            "daily_dd_pct": self.daily_dd_pct * 100.0,
            "utilization": self.utilization() * 100.0,
            "reduce_only": self.is_reduce_only(),
            "breached": self.is_breached(),
        }


class RiskEngine:
    """
    Risk management engine enforcing:
    - Per-idea risk cap (default 2.9%)
    - Cumulative drawdown limits (via dd_tracker)
    - Daily drawdown limits (if enabled)
    - Position count limits per symbol
    """

    def __init__(
        self,
        config: TradingConfig,
        dd_tracker: DrawdownTracker,
        position_manager: PositionManager,
    ):
        """
        Initialize risk engine.

        Args:
            config: Trading configuration
            dd_tracker: Drawdown tracker instance
            position_manager: Position manager instance
        """
        self.config = config
        self.risk_config = config.risk
        self.dd_tracker = dd_tracker
        self.position_manager = position_manager

        # Daily DD tracker
        self.daily_dd = DailyDDTracker(
            config.daily_drawdown,
            config.account.starting_balance,
        )

    def update_state(self, equity: float, balance: float, now: Optional[datetime] = None) -> None:
        """
        Update risk engine state with current account info.

        Args:
            equity: Current equity
            balance: Current balance
            now: Current timestamp
        """
        self.dd_tracker.update(equity, balance, now)
        self.daily_dd.update(equity, now)

    def preflight_check(
        self,
        order: OrderRequest,
        symbol_info: SymbolInfo,
        current_balance: float,
    ) -> RiskCheck:
        """
        Perform comprehensive preflight risk check.

        Args:
            order: Order request
            symbol_info: Symbol metadata
            current_balance: Current account balance

        Returns:
            RiskCheck result
        """
        # Check 1: Cumulative DD state
        if self.dd_tracker.is_breached():
            return RiskCheck(
                approved=False,
                reason="Cumulative drawdown breached",
                metadata=self.dd_tracker.get_summary(),
            )

        if self.dd_tracker.is_reduce_only():
            return RiskCheck(
                approved=False,
                reason="Cumulative DD in reduce-only mode",
                metadata=self.dd_tracker.get_summary(),
            )

        # Check 2: Daily DD state
        if self.daily_dd.is_breached():
            return RiskCheck(
                approved=False,
                reason="Daily drawdown breached",
                metadata=self.daily_dd.get_summary(),
            )

        if self.daily_dd.is_reduce_only():
            return RiskCheck(
                approved=False,
                reason="Daily DD in reduce-only mode",
                metadata=self.daily_dd.get_summary(),
            )

        # Check 3: Per-idea risk
        risk_pct = self._calculate_order_risk_pct(order, symbol_info, current_balance)

        if risk_pct > self.risk_config.max_risk_per_idea_pct:
            return RiskCheck(
                approved=False,
                reason=f"Per-idea risk {risk_pct:.2f}% exceeds limit {self.risk_config.max_risk_per_idea_pct:.2f}%",
                metadata={"risk_pct": risk_pct, "limit": self.risk_config.max_risk_per_idea_pct},
            )

        # Check 4: Max positions per symbol
        current_positions = self.position_manager.count_positions_for_symbol(order.symbol)

        if current_positions >= self.risk_config.max_positions_per_symbol:
            return RiskCheck(
                approved=False,
                reason=f"Max positions for {order.symbol} reached ({current_positions}/{self.risk_config.max_positions_per_symbol})",
                metadata={"current": current_positions, "limit": self.risk_config.max_positions_per_symbol},
            )

        # Check 5: Stop loss required
        if order.stop_loss == 0.0:
            return RiskCheck(
                approved=False,
                reason="Stop loss is mandatory for all orders",
                metadata={},
            )

        # All checks passed
        return RiskCheck(
            approved=True,
            reason="Risk check passed",
            metadata={"risk_pct": risk_pct},
        )

    def _calculate_order_risk_pct(
        self,
        order: OrderRequest,
        symbol_info: SymbolInfo,
        balance: float,
    ) -> float:
        """
        Calculate risk percentage for an order.

        Args:
            order: Order request
            symbol_info: Symbol metadata
            balance: Account balance

        Returns:
            Risk percentage
        """
        if order.stop_loss == 0.0:
            return 0.0

        # Calculate stop distance in price
        stop_distance = abs(order.price - order.stop_loss)

        # Calculate stop distance in pips
        stop_distance_pips = stop_distance / symbol_info.pip_size

        # Pip value per lot
        pip_value_per_lot = symbol_info.contract_size * symbol_info.pip_size

        # Risk amount
        risk_amount = order.volume * stop_distance_pips * pip_value_per_lot

        # Risk percentage
        return calculate_risk_percent(risk_amount, balance)

    def calculate_position_size(
        self,
        symbol_info: SymbolInfo,
        entry_price: float,
        stop_loss: float,
        risk_pct: Optional[float] = None,
        balance: Optional[float] = None,
    ) -> float:
        """
        Calculate position size for a given risk percentage.

        Args:
            symbol_info: Symbol metadata
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_pct: Risk percentage (uses max_risk_per_idea_pct if None)
            balance: Account balance (uses starting_balance if None)

        Returns:
            Position size in lots
        """
        if risk_pct is None:
            risk_pct = self.risk_config.max_risk_per_idea_pct

        if balance is None:
            balance = self.config.account.starting_balance

        stop_distance = abs(entry_price - stop_loss)
        stop_distance_pips = stop_distance / symbol_info.pip_size
        pip_value_per_lot = symbol_info.contract_size * symbol_info.pip_size

        lots = calculate_lot_size_for_risk(
            balance=balance,
            risk_percent=risk_pct,
            stop_distance_pips=stop_distance_pips,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Normalize to broker constraints
        from src.utils.calc import normalize_lot_size

        return normalize_lot_size(
            lots,
            min_lot=symbol_info.min_lot,
            max_lot=symbol_info.max_lot,
            step=symbol_info.lot_step,
        )

    def is_reduce_only(self) -> bool:
        """Check if system is in reduce-only mode."""
        return self.dd_tracker.is_reduce_only() or self.daily_dd.is_reduce_only()

    def is_breached(self) -> bool:
        """Check if any limits have been breached."""
        return self.dd_tracker.is_breached() or self.daily_dd.is_breached()

    def get_summary(self) -> dict:
        """Get risk engine summary."""
        return {
            "cumulative_dd": self.dd_tracker.get_summary(),
            "daily_dd": self.daily_dd.get_summary(),
            "reduce_only": self.is_reduce_only(),
            "breached": self.is_breached(),
            "max_risk_per_idea_pct": self.risk_config.max_risk_per_idea_pct,
            "max_positions_per_symbol": self.risk_config.max_positions_per_symbol,
        }
