"""Calendar and time window utilities for news events."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class NewsEvent:
    """Represents a scheduled news event."""

    id: str
    economies: List[str]
    title: str
    timestamp_utc: datetime
    impact: str

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "NewsEvent":
        """Create NewsEvent from dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp_utc"].replace("Z", "+00:00"))
        return cls(
            id=data["id"],
            economies=data["economies"],
            title=data["title"],
            timestamp_utc=timestamp,
            impact=data["impact"],
        )


class NewsCalendar:
    """Manages economic calendar events."""

    def __init__(self, events: List[NewsEvent]):
        self.events = sorted(events, key=lambda e: e.timestamp_utc)
        self._economy_index: Dict[str, List[NewsEvent]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Build index of events by economy."""
        for event in self.events:
            for economy in event.economies:
                if economy not in self._economy_index:
                    self._economy_index[economy] = []
                self._economy_index[economy].append(event)

    @classmethod
    def load_from_json(cls, path: str | Path) -> "NewsCalendar":
        """Load calendar from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        events = [NewsEvent.from_dict(item) for item in data]
        return cls(events)

    def get_events_for_economies(
        self,
        economies: Set[str],
        start_time: datetime,
        end_time: datetime,
    ) -> List[NewsEvent]:
        """
        Get events affecting specified economies within time range.

        Args:
            economies: Set of economy codes (USD, EUR, etc.)
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of NewsEvent objects
        """
        result = []
        for economy in economies:
            if economy in self._economy_index:
                for event in self._economy_index[economy]:
                    if start_time <= event.timestamp_utc <= end_time:
                        result.append(event)
        return sorted(result, key=lambda e: e.timestamp_utc)

    def get_upcoming_events(
        self,
        economies: Set[str],
        from_time: datetime,
        horizon_hours: int = 24,
    ) -> List[NewsEvent]:
        """Get upcoming events for specified economies."""
        end_time = from_time + timedelta(hours=horizon_hours)
        return self.get_events_for_economies(economies, from_time, end_time)


def get_symbol_economies(symbol: str) -> Set[str]:
    """
    Map trading symbol to affected economies.

    Args:
        symbol: Trading symbol (e.g., EURUSD, US30, XAUUSD)

    Returns:
        Set of economy codes
    """
    symbol = symbol.upper()

    # FX pairs - both currencies
    if len(symbol) == 6:
        base = symbol[:3]
        quote = symbol[3:]
        return {base, quote}

    # Indices
    if symbol.startswith("US") or symbol.startswith("SPX") or symbol.startswith("NAS"):
        return {"USD"}
    if symbol.startswith("UK") or symbol.startswith("FTSE"):
        return {"GBP"}
    if symbol.startswith("DE") or symbol.startswith("DAX") or symbol.startswith("EU"):
        return {"EUR"}
    if symbol.startswith("JP") or symbol.startswith("NIK"):
        return {"JPY"}
    if symbol.startswith("AU") or symbol.startswith("ASX"):
        return {"AUD"}

    # Commodities
    if symbol.startswith("XAU") or symbol.startswith("XAG"):  # Gold, Silver
        return {"USD"}
    if symbol.startswith("WTI") or symbol.startswith("BRENT"):  # Oil
        return {"USD"}

    # Crypto (typically USD-based)
    if any(symbol.startswith(crypto) for crypto in ["BTC", "ETH", "XRP", "LTC"]):
        return {"USD"}

    # Default: no economy mapping
    return set()


def is_within_news_window(
    check_time: datetime,
    event_time: datetime,
    window_seconds: int,
) -> bool:
    """
    Check if a time is within the blackout window of an event.

    Args:
        check_time: Time to check
        event_time: Event time
        window_seconds: Window size in seconds (±)

    Returns:
        True if check_time is within the window
    """
    diff = abs((check_time - event_time).total_seconds())
    return diff <= window_seconds


def get_next_trading_day(dt: datetime, skip_weekends: bool = True) -> datetime:
    """
    Get the next trading day.

    Args:
        dt: Current datetime
        skip_weekends: Whether to skip Saturday/Sunday

    Returns:
        Next trading day
    """
    next_day = dt + timedelta(days=1)
    if skip_weekends:
        while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
            next_day += timedelta(days=1)
    return next_day


def is_market_hours(dt: datetime, market: str = "forex") -> bool:
    """
    Check if datetime is within market hours.

    Args:
        dt: Datetime to check (should be UTC)
        market: Market type (forex, us_stocks, etc.)

    Returns:
        True if within market hours
    """
    if market == "forex":
        # Forex trades 24/5
        return dt.weekday() < 5

    elif market == "us_stocks":
        # US stocks: Mon-Fri, 9:30 AM - 4:00 PM ET (14:30-21:00 UTC)
        if dt.weekday() >= 5:
            return False
        hour_utc = dt.hour
        return 14 <= hour_utc < 21 or (hour_utc == 21 and dt.minute == 0)

    # Default: assume 24/5
    return dt.weekday() < 5
