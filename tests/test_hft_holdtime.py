"""Tests for HFT prevention (minimum hold time)."""

import pytest
from datetime import datetime, timedelta, timezone

from src.utils.throttle import HoldTimeTracker


def test_min_hold_time_enforcement():
    """Test that positions can't be closed before min hold time."""
    tracker = HoldTimeTracker(min_hold_seconds=61)

    # Open position
    open_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tracker.record_open("pos_123", open_time)

    # Try to close after 30 seconds
    check_time = open_time + timedelta(seconds=30)
    assert not tracker.can_close("pos_123", check_time)

    # Try to close after 61 seconds
    check_time = open_time + timedelta(seconds=61)
    assert tracker.can_close("pos_123", check_time)


def test_hold_time_calculation():
    """Test hold time calculation."""
    tracker = HoldTimeTracker(min_hold_seconds=61)

    open_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tracker.record_open("pos_123", open_time)

    check_time = open_time + timedelta(seconds=45)
    hold_time = tracker.get_hold_time("pos_123", check_time)

    assert hold_time == 45.0


def test_unknown_position_allowed():
    """Test that unknown positions can be closed (safety)."""
    tracker = HoldTimeTracker(min_hold_seconds=61)

    # Try to close unknown position
    assert tracker.can_close("unknown_pos")


def test_record_close():
    """Test that closing removes position from tracking."""
    tracker = HoldTimeTracker(min_hold_seconds=61)

    tracker.record_open("pos_123")
    tracker.record_close("pos_123")

    # Should now be unknown (allowed to close)
    assert tracker.can_close("pos_123")
