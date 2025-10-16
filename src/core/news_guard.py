"""News guard for blocking trades during major economic events."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Set

from src.core.config import NewsConfig
from src.utils.calendars import (
    NewsCalendar,
    NewsEvent,
    get_symbol_economies,
    is_within_news_window,
)

logger = logging.getLogger(__name__)


@dataclass
class NewsBlockCheck:
    """Result of a news blackout check."""

    blocked: bool
    reason: str
    blocking_events: List[NewsEvent]
    metadata: dict


class NewsGuard:
    """
    Guards against trading during major news events.

    Enforces blackout windows (±4 minutes by default) around high-impact
    economic events for affected symbols only.
    """

    def __init__(self, config: NewsConfig, calendar_path: str = "configs/news_events_seed.json"):
        """
        Initialize news guard.

        Args:
            config: News configuration
            calendar_path: Path to news events JSON file
        """
        self.config = config
        self.window_seconds = config.window_seconds
        self.add_on_enabled = config.add_on_enabled
        self.apply_only_impacted = config.apply_only_to_impacted_symbols

        # Load calendar
        self.calendar: Optional[NewsCalendar] = None
        try:
            self.calendar = NewsCalendar.load_from_json(calendar_path)
            logger.info(f"Loaded {len(self.calendar.events)} news events from {calendar_path}")
        except Exception as e:
            logger.error(f"Failed to load news calendar: {e}")

        logger.info(
            f"News guard initialized: window={config.window_seconds}s, "
            f"add_on={config.add_on_enabled}, apply_impacted_only={config.apply_only_to_impacted_symbols}"
        )

    def check_order(
        self,
        symbol: str,
        now: Optional[datetime] = None,
        is_opening: bool = True,
    ) -> NewsBlockCheck:
        """
        Check if an order should be blocked due to news.

        Args:
            symbol: Trading symbol
            now: Current timestamp (uses utcnow if None)
            is_opening: True if opening position, False if closing

        Returns:
            NewsBlockCheck result
        """
        # News guard disabled
        if not self.config.enforce_window:
            return NewsBlockCheck(
                blocked=False,
                reason="News guard disabled",
                blocking_events=[],
                metadata={},
            )

        # Add-on enabled (allows trading through news)
        if self.add_on_enabled:
            return NewsBlockCheck(
                blocked=False,
                reason="News trading add-on enabled",
                blocking_events=[],
                metadata={},
            )

        # No calendar loaded
        if self.calendar is None:
            logger.warning("News calendar not loaded - allowing trade")
            return NewsBlockCheck(
                blocked=False,
                reason="Calendar not loaded",
                blocking_events=[],
                metadata={},
            )

        if now is None:
            now = datetime.now(timezone.utc)

        # Get affected economies for this symbol
        economies = get_symbol_economies(symbol)

        if not economies and self.apply_only_impacted:
            # Symbol has no economy mapping and we only apply to impacted symbols
            return NewsBlockCheck(
                blocked=False,
                reason="Symbol not mapped to any economy",
                blocking_events=[],
                metadata={"symbol": symbol},
            )

        # Find upcoming events within the blackout window
        window_start = now - timedelta(seconds=self.window_seconds)
        window_end = now + timedelta(seconds=self.window_seconds)

        blocking_events = self.calendar.get_events_for_economies(
            economies,
            window_start,
            window_end,
        )

        if blocking_events:
            event_details = [
                f"{e.title} ({e.economies[0]}) at {e.timestamp_utc.strftime('%H:%M UTC')}"
                for e in blocking_events
            ]

            return NewsBlockCheck(
                blocked=True,
                reason=f"News blackout window active: {', '.join(event_details)}",
                blocking_events=blocking_events,
                metadata={
                    "symbol": symbol,
                    "economies": list(economies),
                    "window_seconds": self.window_seconds,
                    "events_count": len(blocking_events),
                },
            )

        # No blocking events
        return NewsBlockCheck(
            blocked=False,
            reason="No news events in blackout window",
            blocking_events=[],
            metadata={"symbol": symbol, "economies": list(economies)},
        )

    def get_upcoming_blocks(
        self,
        symbol: str,
        now: Optional[datetime] = None,
        horizon_hours: int = 24,
    ) -> List[NewsEvent]:
        """
        Get upcoming news events that would block trading for a symbol.

        Args:
            symbol: Trading symbol
            now: Current timestamp
            horizon_hours: Look-ahead window in hours

        Returns:
            List of upcoming NewsEvent objects
        """
        if self.calendar is None:
            return []

        if now is None:
            now = datetime.now(timezone.utc)

        economies = get_symbol_economies(symbol)
        if not economies:
            return []

        return self.calendar.get_upcoming_events(economies, now, horizon_hours)

    def is_symbol_affected(self, symbol: str, event: NewsEvent) -> bool:
        """
        Check if a symbol is affected by a news event.

        Args:
            symbol: Trading symbol
            event: News event

        Returns:
            True if symbol is affected
        """
        symbol_economies = get_symbol_economies(symbol)
        event_economies = set(event.economies)

        return bool(symbol_economies & event_economies)

    def get_next_clear_time(
        self,
        symbol: str,
        now: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Get the next time when trading is clear (no blackout).

        Args:
            symbol: Trading symbol
            now: Current timestamp

        Returns:
            Next clear timestamp or None if clear now
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Check current status
        check = self.check_order(symbol, now)
        if not check.blocked:
            return None

        # Find when the current blocking events end
        if check.blocking_events:
            # Get the latest event end time
            end_times = [
                e.timestamp_utc + timedelta(seconds=self.window_seconds)
                for e in check.blocking_events
            ]
            return max(end_times)

        return None

    def get_summary(self) -> dict:
        """Get news guard summary."""
        return {
            "enforce_window": self.config.enforce_window,
            "window_seconds": self.window_seconds,
            "add_on_enabled": self.add_on_enabled,
            "apply_only_impacted": self.apply_only_impacted,
            "events_loaded": len(self.calendar.events) if self.calendar else 0,
            "sources": self.config.source_list,
        }
