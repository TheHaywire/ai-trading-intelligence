"""Rate limiting and throttling utilities."""

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, Optional


@dataclass
class RateLimitConfig:
    """Rate limiter configuration."""

    max_calls: int
    period_seconds: float


class RateLimiter:
    """
    Token bucket rate limiter for API/broker calls.

    Tracks call timestamps and enforces rate limits.
    """

    def __init__(self, max_calls: int, period_seconds: float):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls in the period
            period_seconds: Time period in seconds
        """
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.calls: Deque[float] = deque()

    def is_allowed(self, now: Optional[float] = None) -> bool:
        """
        Check if a call is currently allowed.

        Args:
            now: Current timestamp (uses time.time() if None)

        Returns:
            True if call is allowed
        """
        if now is None:
            now = time.time()

        # Remove expired timestamps
        cutoff = now - self.period_seconds
        while self.calls and self.calls[0] < cutoff:
            self.calls.popleft()

        return len(self.calls) < self.max_calls

    def acquire(self, now: Optional[float] = None, wait: bool = False) -> bool:
        """
        Attempt to acquire permission for a call.

        Args:
            now: Current timestamp
            wait: If True, block until allowed

        Returns:
            True if acquired
        """
        if now is None:
            now = time.time()

        if wait:
            while not self.is_allowed(now):
                time.sleep(0.1)
                now = time.time()

        if self.is_allowed(now):
            self.calls.append(now)
            return True

        return False

    def reset(self) -> None:
        """Reset the rate limiter."""
        self.calls.clear()

    def time_until_next_slot(self, now: Optional[float] = None) -> float:
        """
        Get time until next call slot is available.

        Args:
            now: Current timestamp

        Returns:
            Seconds until next slot (0 if currently available)
        """
        if now is None:
            now = time.time()

        if self.is_allowed(now):
            return 0.0

        # Next slot available when oldest call expires
        if self.calls:
            oldest = self.calls[0]
            return max(0.0, (oldest + self.period_seconds) - now)

        return 0.0


class TradeRateThrottle:
    """
    Throttles trade execution rate.

    Tracks trades per hour and enforces configurable limits.
    """

    def __init__(self, max_trades_per_hour: int):
        """
        Initialize trade throttle.

        Args:
            max_trades_per_hour: Maximum trades allowed per hour
        """
        self.max_trades_per_hour = max_trades_per_hour
        self.trade_times: Deque[datetime] = deque()

    def record_trade(self, trade_time: Optional[datetime] = None) -> None:
        """
        Record a trade execution.

        Args:
            trade_time: Time of trade (uses utcnow if None)
        """
        if trade_time is None:
            trade_time = datetime.now(timezone.utc)
        self.trade_times.append(trade_time)

    def get_trades_in_last_hour(self, now: Optional[datetime] = None) -> int:
        """
        Get number of trades in the last hour.

        Args:
            now: Current time (uses utcnow if None)

        Returns:
            Trade count
        """
        if now is None:
            now = datetime.now(timezone.utc)

        cutoff = now - timedelta(hours=1)

        # Remove old trades
        while self.trade_times and self.trade_times[0] < cutoff:
            self.trade_times.popleft()

        return len(self.trade_times)

    def is_allowed(self, now: Optional[datetime] = None) -> bool:
        """
        Check if a new trade is allowed.

        Args:
            now: Current time

        Returns:
            True if trade is allowed
        """
        return self.get_trades_in_last_hour(now) < self.max_trades_per_hour

    def utilization(self, now: Optional[datetime] = None) -> float:
        """
        Get throttle utilization as a fraction.

        Args:
            now: Current time

        Returns:
            Utilization (0.0 - 1.0)
        """
        trades = self.get_trades_in_last_hour(now)
        return trades / self.max_trades_per_hour if self.max_trades_per_hour > 0 else 0.0

    def reset(self) -> None:
        """Reset the throttle."""
        self.trade_times.clear()


from datetime import timezone


class HoldTimeTracker:
    """
    Tracks minimum hold time requirements for positions.

    Enforces HFT prevention rules.
    """

    def __init__(self, min_hold_seconds: int = 61):
        """
        Initialize hold time tracker.

        Args:
            min_hold_seconds: Minimum required hold time
        """
        self.min_hold_seconds = min_hold_seconds
        self.position_open_times: dict[str, datetime] = {}

    def record_open(self, position_id: str, open_time: Optional[datetime] = None) -> None:
        """
        Record position opening.

        Args:
            position_id: Unique position identifier
            open_time: Opening time (uses utcnow if None)
        """
        if open_time is None:
            open_time = datetime.now(timezone.utc)
        self.position_open_times[position_id] = open_time

    def can_close(self, position_id: str, now: Optional[datetime] = None) -> bool:
        """
        Check if position can be closed now.

        Args:
            position_id: Position identifier
            now: Current time

        Returns:
            True if minimum hold time has passed
        """
        if position_id not in self.position_open_times:
            return True  # Unknown position, allow close

        if now is None:
            now = datetime.now(timezone.utc)

        open_time = self.position_open_times[position_id]
        elapsed = (now - open_time).total_seconds()
        return elapsed >= self.min_hold_seconds

    def get_hold_time(self, position_id: str, now: Optional[datetime] = None) -> float:
        """
        Get current hold time for position.

        Args:
            position_id: Position identifier
            now: Current time

        Returns:
            Hold time in seconds
        """
        if position_id not in self.position_open_times:
            return 0.0

        if now is None:
            now = datetime.now(timezone.utc)

        open_time = self.position_open_times[position_id]
        return (now - open_time).total_seconds()

    def record_close(self, position_id: str) -> None:
        """
        Record position closure.

        Args:
            position_id: Position identifier
        """
        self.position_open_times.pop(position_id, None)

    def reset(self) -> None:
        """Reset the tracker."""
        self.position_open_times.clear()
