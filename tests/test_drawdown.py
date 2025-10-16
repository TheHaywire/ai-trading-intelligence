"""Tests for drawdown tracking (smart and static DD)."""

import pytest
from datetime import datetime, timezone

from src.core.config import DrawdownConfig, DrawdownModel, SmartDDConfig, StaticDDConfig
from src.core.dd_tracker import DDState, DrawdownTracker


class TestSmartDD:
    """Test Smart DD (IF accounts) behavior."""

    def test_initial_floor_10_percent(self):
        """Test initial 10% DD floor."""
        config = DrawdownConfig(
            model=DrawdownModel.SMART,
            smart=SmartDDConfig(initial_pct=0.10, lock_after_gain_pct=0.05, locked_pct=0.05),
        )
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        assert tracker.floor_pct == 0.10
        assert tracker.floor_value == 90000.0
        assert not tracker.locked

    def test_lock_at_5_percent_gain(self):
        """Test DD locks to 5% after +5% equity gain."""
        config = DrawdownConfig(
            model=DrawdownModel.SMART,
            smart=SmartDDConfig(initial_pct=0.10, lock_after_gain_pct=0.05, locked_pct=0.05),
        )
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        # Equity reaches +5%
        tracker.update(equity=105000.0, balance=105000.0)

        assert tracker.locked
        assert tracker.floor_pct == 0.05
        assert tracker.floor_value == 95000.0  # 5% of starting balance

    def test_floor_never_trails_above(self):
        """Test that locked floor never trails above initial locked level."""
        config = DrawdownConfig(model=DrawdownModel.SMART)
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        # Lock at +5%
        tracker.update(equity=105000.0, balance=105000.0)
        floor_after_lock = tracker.floor_value

        # Even if equity goes higher, floor stays the same
        tracker.update(equity=120000.0, balance=120000.0)

        assert tracker.floor_value == floor_after_lock  # Should not trail

    def test_scaling_resets_floor_to_5_percent(self):
        """Test scaling resets floor to 5% of NEW balance."""
        config = DrawdownConfig(model=DrawdownModel.SMART)
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        # Scale to $200k
        tracker.on_scale(new_starting_balance=200000.0)

        assert tracker.starting_balance == 200000.0
        assert tracker.floor_pct == 0.05
        assert tracker.floor_value == 190000.0  # 5% of 200k

    def test_reduce_only_at_80_percent_utilization(self):
        """Test reduce-only mode triggers at 80% DD utilization."""
        config = DrawdownConfig(model=DrawdownModel.SMART)
        tracker = DrawdownTracker(starting_balance=100000.0, config=config, buffer_pct=0.80)

        # Lock floor at 5%
        tracker.update(equity=105000.0, balance=105000.0)

        # DD floor is at $95k. 80% utilization = $96k equity
        # max loss = $5000, 80% = $4000 loss, so equity = $96,000
        tracker.update(equity=96000.0, balance=96000.0)

        assert tracker.is_reduce_only()

    def test_breach_detection(self):
        """Test DD breach is detected correctly."""
        config = DrawdownConfig(model=DrawdownModel.SMART)
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        # Locked floor at $95k
        tracker.update(equity=105000.0, balance=105000.0)

        # Breach floor
        tracker.update(equity=94999.0, balance=94999.0)

        assert tracker.is_breached()
        assert tracker.state == DDState.BREACHED


class TestStaticDD:
    """Test Static DD (challenge accounts) behavior."""

    def test_fixed_floor(self):
        """Test static DD has fixed floor."""
        config = DrawdownConfig(
            model=DrawdownModel.STATIC,
            static=StaticDDConfig(max_loss_pct=0.06),
        )
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        assert tracker.floor_pct == 0.06
        assert tracker.floor_value == 94000.0
        assert tracker.locked  # Always "locked" for static

    def test_floor_never_changes(self):
        """Test static DD floor never changes."""
        config = DrawdownConfig(model=DrawdownModel.STATIC, static=StaticDDConfig(max_loss_pct=0.10))
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        initial_floor = tracker.floor_value

        # Equity goes up
        tracker.update(equity=120000.0, balance=120000.0)

        assert tracker.floor_value == initial_floor

    def test_breach_at_floor(self):
        """Test static DD breach detection."""
        config = DrawdownConfig(model=DrawdownModel.STATIC, static=StaticDDConfig(max_loss_pct=0.08))
        tracker = DrawdownTracker(starting_balance=100000.0, config=config)

        # Floor is at $92k
        tracker.update(equity=91999.0, balance=91999.0)

        assert tracker.is_breached()


def test_utilization_calculation():
    """Test DD utilization calculation."""
    config = DrawdownConfig(model=DrawdownModel.SMART)
    tracker = DrawdownTracker(starting_balance=100000.0, config=config)

    # Lock at 5%
    tracker.update(equity=105000.0, balance=105000.0)

    # Drop to $97.5k (half of 5% allowance used)
    tracker.update(equity=97500.0, balance=97500.0)

    utilization = tracker.utilization_cumulative()
    assert abs(utilization - 0.5) < 0.01  # 50% of DD allowance used
