"""Tests for news blackout window logic."""

import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.config import NewsConfig
from src.core.news_guard import NewsGuard


@pytest.fixture
def temp_news_calendar():
    """Create temporary news calendar JSON."""
    with TemporaryDirectory() as tmpdir:
        calendar_path = Path(tmpdir) / "news_test.json"

        events = [
            {
                "id": "usd_nfp_test",
                "economies": ["USD"],
                "title": "NFP",
                "timestamp_utc": "2025-11-07T13:30:00Z",
                "impact": "high",
            },
            {
                "id": "eur_ecb_test",
                "economies": ["EUR"],
                "title": "ECB Rate",
                "timestamp_utc": "2025-11-07T12:45:00Z",
                "impact": "high",
            },
        ]

        with open(calendar_path, "w") as f:
            json.dump(events, f)

        yield str(calendar_path)


def test_block_within_window(temp_news_calendar):
    """Test that trades are blocked within ±240s window."""
    config = NewsConfig(
        enforce_window=True,
        window_seconds=240,
        apply_only_to_impacted_symbols=True,
    )

    guard = NewsGuard(config, calendar_path=temp_news_calendar)

    # NFP at 13:30:00 UTC
    event_time = datetime(2025, 11, 7, 13, 30, 0, tzinfo=timezone.utc)

    # 2 minutes before event (within 4min window)
    check_time = event_time - timedelta(seconds=120)
    result = guard.check_order("EURUSD", now=check_time, is_opening=True)

    assert result.blocked
    assert len(result.blocking_events) > 0


def test_no_block_outside_window(temp_news_calendar):
    """Test that trades are allowed outside the blackout window."""
    config = NewsConfig(
        enforce_window=True,
        window_seconds=240,
        apply_only_to_impacted_symbols=True,
    )

    guard = NewsGuard(config, calendar_path=temp_news_calendar)

    event_time = datetime(2025, 11, 7, 13, 30, 0, tzinfo=timezone.utc)

    # 10 minutes before event (outside 4min window)
    check_time = event_time - timedelta(seconds=600)
    result = guard.check_order("EURUSD", now=check_time, is_opening=True)

    assert not result.blocked


def test_only_impacted_symbols_blocked(temp_news_calendar):
    """Test that only impacted symbols are blocked."""
    config = NewsConfig(
        enforce_window=True,
        window_seconds=240,
        apply_only_to_impacted_symbols=True,
    )

    guard = NewsGuard(config, calendar_path=temp_news_calendar)

    # USD NFP event at 13:30
    event_time = datetime(2025, 11, 7, 13, 30, 0, tzinfo=timezone.utc)

    # EUR symbol should NOT be blocked by USD news
    result_eur = guard.check_order("EURJPY", now=event_time, is_opening=True)
    assert not result_eur.blocked  # EURJPY not affected by USD-only news

    # USD symbol SHOULD be blocked
    result_usd = guard.check_order("EURUSD", now=event_time, is_opening=True)
    assert result_usd.blocked  # EURUSD affected by USD news


def test_add_on_bypasses_block(temp_news_calendar):
    """Test that news trading add-on bypasses the block."""
    config = NewsConfig(
        enforce_window=True,
        window_seconds=240,
        add_on_enabled=True,  # Add-on enabled
    )

    guard = NewsGuard(config, calendar_path=temp_news_calendar)

    event_time = datetime(2025, 11, 7, 13, 30, 0, tzinfo=timezone.utc)
    result = guard.check_order("EURUSD", now=event_time, is_opening=True)

    assert not result.blocked  # Add-on allows trading


def test_guard_disabled(temp_news_calendar):
    """Test that disabling guard allows all trades."""
    config = NewsConfig(
        enforce_window=False,  # Disabled
        window_seconds=240,
    )

    guard = NewsGuard(config, calendar_path=temp_news_calendar)

    event_time = datetime(2025, 11, 7, 13, 30, 0, tzinfo=timezone.utc)
    result = guard.check_order("EURUSD", now=event_time, is_opening=True)

    assert not result.blocked


def test_upcoming_blocks(temp_news_calendar):
    """Test getting upcoming blocking events."""
    config = NewsConfig(enforce_window=True, window_seconds=240)
    guard = NewsGuard(config, calendar_path=temp_news_calendar)

    # Query from 1 hour before NFP
    query_time = datetime(2025, 11, 7, 12, 30, 0, tzinfo=timezone.utc)
    upcoming = guard.get_upcoming_blocks("EURUSD", now=query_time, horizon_hours=2)

    assert len(upcoming) > 0  # Should find USD events
