"""Trading session filters and playbooks."""

import logging
from dataclasses import dataclass
from datetime import datetime, time, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TradingSession(str, Enum):
    """Trading session types."""

    ASIA = "asia"
    LONDON = "london"
    NY = "ny"
    OVERLAP_LONDON_NY = "overlap_london_ny"


@dataclass
class SessionConfig:
    """Configuration for a trading session."""

    start_hour_utc: int
    end_hour_utc: int
    enable_strategies: List[str]
    spread_cap_points: float
    risk_mult: float = 1.0
    allow_mean_reversion: bool = True
    allow_breakouts: bool = True
    thin_crosses_blocked: bool = False


class SessionFilter:
    """
    Session-based trading filters and playbooks.

    Session characteristics:
    - Asia: Low volatility, mean-reversion bias, block thin crosses
    - London: High volatility, trend/breakout primary, execution alpha
    - NY: Continuation/reversal, post-news focus, strict slippage
    - London/NY Overlap: Highest liquidity, best execution
    """

    def __init__(self, session_configs: Optional[Dict[str, SessionConfig]] = None):
        """
        Initialize session filter.

        Args:
            session_configs: Configuration for each session
        """
        # Default session configurations
        self.session_configs = session_configs or {
            TradingSession.ASIA: SessionConfig(
                start_hour_utc=0,
                end_hour_utc=8,
                enable_strategies=["mean_reversion_bands"],
                spread_cap_points=18.0,
                risk_mult=0.9,
                allow_breakouts=False,
                thin_crosses_blocked=True,
            ),
            TradingSession.LONDON: SessionConfig(
                start_hour_utc=8,
                end_hour_utc=16,
                enable_strategies=["trend_breakout", "breakout_session_open", "ema_trend"],
                spread_cap_points=14.0,
                risk_mult=1.0,
                allow_mean_reversion=True,
                allow_breakouts=True,
            ),
            TradingSession.NY: SessionConfig(
                start_hour_utc=14,
                end_hour_utc=22,
                enable_strategies=["trend_breakout", "ema_trend"],
                spread_cap_points=16.0,
                risk_mult=1.0,
                allow_breakouts=True,
            ),
            TradingSession.OVERLAP_LONDON_NY: SessionConfig(
                start_hour_utc=14,
                end_hour_utc=16,
                enable_strategies=["trend_breakout", "breakout_session_open", "ema_trend"],
                spread_cap_points=12.0,  # Tightest spreads
                risk_mult=1.05,  # Slight boost for best liquidity
                allow_mean_reversion=True,
                allow_breakouts=True,
            ),
        }

        logger.info("Session filter initialized with playbooks")

    def get_current_session(self, now: Optional[datetime] = None) -> TradingSession:
        """
        Get current trading session.

        Args:
            now: Current time (UTC)

        Returns:
            Current session
        """
        if now is None:
            now = datetime.now(timezone.utc)

        hour_utc = now.hour

        # Check for overlap first (highest priority)
        if 14 <= hour_utc < 16:
            return TradingSession.OVERLAP_LONDON_NY

        # London session
        if 8 <= hour_utc < 16:
            return TradingSession.LONDON

        # NY session
        if 14 <= hour_utc < 22:
            return TradingSession.NY

        # Asia session
        return TradingSession.ASIA

    def is_strategy_enabled_for_session(
        self,
        strategy_name: str,
        session: Optional[TradingSession] = None,
    ) -> bool:
        """
        Check if strategy is enabled for current session.

        Args:
            strategy_name: Strategy name
            session: Trading session (uses current if None)

        Returns:
            True if strategy is enabled
        """
        if session is None:
            session = self.get_current_session()

        config = self.session_configs.get(session)
        if config is None:
            return True  # No restriction

        return strategy_name in config.enable_strategies

    def get_spread_cap_for_session(
        self,
        session: Optional[TradingSession] = None,
    ) -> float:
        """
        Get spread cap for current session.

        Args:
            session: Trading session (uses current if None)

        Returns:
            Spread cap in points
        """
        if session is None:
            session = self.get_current_session()

        config = self.session_configs.get(session)
        if config is None:
            return 20.0  # Default

        return config.spread_cap_points

    def get_risk_multiplier_for_session(
        self,
        session: Optional[TradingSession] = None,
    ) -> float:
        """
        Get risk multiplier for current session.

        Args:
            session: Trading session (uses current if None)

        Returns:
            Risk multiplier
        """
        if session is None:
            session = self.get_current_session()

        config = self.session_configs.get(session)
        if config is None:
            return 1.0

        return config.risk_mult

    def is_symbol_allowed_in_session(
        self,
        symbol: str,
        session: Optional[TradingSession] = None,
    ) -> tuple[bool, str]:
        """
        Check if symbol is allowed in current session.

        Args:
            symbol: Trading symbol
            session: Trading session (uses current if None)

        Returns:
            (allowed, reason)
        """
        if session is None:
            session = self.get_current_session()

        config = self.session_configs.get(session)
        if config is None:
            return True, "No session restrictions"

        # Check for thin crosses in Asia
        if config.thin_crosses_blocked:
            if self._is_thin_cross(symbol):
                return False, f"Thin cross blocked during {session.value}"

        return True, "Symbol allowed"

    def _is_thin_cross(self, symbol: str) -> bool:
        """
        Check if symbol is a thin cross (exotic FX pair).

        Args:
            symbol: Symbol to check

        Returns:
            True if thin cross
        """
        symbol = symbol.upper()

        # Major pairs (not thin)
        majors = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
        if symbol in majors:
            return False

        # Minor pairs (not thin)
        minors = ["EURGBP", "EURJPY", "GBPJPY", "EURCHF", "AUDJPY", "CADJPY"]
        if symbol in minors:
            return False

        # Everything else is considered thin
        if len(symbol) == 6:  # FX pair
            return True

        return False

    def get_session_playbook(
        self,
        session: Optional[TradingSession] = None,
    ) -> Dict:
        """
        Get complete playbook for a session.

        Args:
            session: Trading session (uses current if None)

        Returns:
            Session playbook configuration
        """
        if session is None:
            session = self.get_current_session()

        config = self.session_configs.get(session)
        if config is None:
            return {}

        return {
            "session": session.value,
            "start_hour_utc": config.start_hour_utc,
            "end_hour_utc": config.end_hour_utc,
            "enabled_strategies": config.enable_strategies,
            "spread_cap_points": config.spread_cap_points,
            "risk_multiplier": config.risk_mult,
            "allow_mean_reversion": config.allow_mean_reversion,
            "allow_breakouts": config.allow_breakouts,
            "thin_crosses_blocked": config.thin_crosses_blocked,
        }

    def get_optimal_execution_window(self, now: Optional[datetime] = None) -> tuple[bool, str]:
        """
        Check if current time is in optimal execution window.

        Args:
            now: Current time (UTC)

        Returns:
            (is_optimal, reason)
        """
        session = self.get_current_session(now)

        # Overlap is always optimal
        if session == TradingSession.OVERLAP_LONDON_NY:
            return True, "London/NY overlap - best liquidity"

        # London and NY are good
        if session in (TradingSession.LONDON, TradingSession.NY):
            return True, f"{session.value} session - good liquidity"

        # Asia is suboptimal
        return False, "Asia session - lower liquidity"

    def get_summary(self) -> Dict:
        """Get session filter summary."""
        current_session = self.get_current_session()
        playbook = self.get_session_playbook(current_session)

        return {
            "current_session": current_session.value,
            "current_playbook": playbook,
            "all_sessions": list(self.session_configs.keys()),
        }
