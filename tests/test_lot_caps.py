"""Tests for lot caps enforcement."""

import pytest
from src.core.config import LotCapsTable, ProgramType
from src.core.lots_cap import LotCapsValidator
from src.core.positions import Position, PositionManager
from src.core.broker_mt5 import OrderType
from datetime import datetime, timezone


@pytest.fixture
def lot_caps_table():
    """Create test lot caps table."""
    caps_data = {
        "instant_funding": {
            10000: {"fx": 4, "commodities": 0.3, "indices": 2, "crypto": 1},
            20000: {"fx": 8, "commodities": 0.6, "indices": 4, "crypto": 2},
        }
    }
    return LotCapsTable(caps=caps_data)


@pytest.fixture
def position_manager():
    """Create position manager."""
    return PositionManager()


def test_caps_loaded_correctly(lot_caps_table, position_manager):
    """Test that caps are loaded for correct program/balance."""
    validator = LotCapsValidator(
        program=ProgramType.INSTANT_FUNDING,
        starting_balance=10000.0,
        lot_caps_table=lot_caps_table,
        position_manager=position_manager,
    )

    assert validator.caps["fx"] == 4
    assert validator.caps["commodities"] == 0.3


def test_order_within_caps_approved(lot_caps_table, position_manager):
    """Test that orders within caps are approved."""
    validator = LotCapsValidator(
        program=ProgramType.INSTANT_FUNDING,
        starting_balance=10000.0,
        lot_caps_table=lot_caps_table,
        position_manager=position_manager,
    )

    # Order for 2 lots FX (cap is 4)
    result = validator.check_order("EURUSD", volume=2.0, is_opening=True)

    assert result.approved


def test_order_exceeding_caps_rejected(lot_caps_table, position_manager):
    """Test that orders exceeding caps are rejected."""
    validator = LotCapsValidator(
        program=ProgramType.INSTANT_FUNDING,
        starting_balance=10000.0,
        lot_caps_table=lot_caps_table,
        position_manager=position_manager,
    )

    # Add existing 3 lots FX position
    position = Position(
        ticket=123,
        symbol="EURUSD",
        type=OrderType.BUY,
        volume=3.0,
        open_price=1.1000,
        open_time=datetime.now(timezone.utc),
        stop_loss=1.0950,
        take_profit=1.1100,
        profit=0.0,
        commission=0.0,
        swap=0.0,
    )

    idea_id = position_manager.create_idea("EURUSD", OrderType.BUY, "test", 100.0)
    position_manager.add_position(position, idea_id)

    # Try to add 2 more lots (total would be 5, cap is 4)
    result = validator.check_order("EURUSD", volume=2.0, is_opening=True)

    assert not result.approved
    assert "exceeded" in result.reason.lower()


def test_utilization_calculation(lot_caps_table, position_manager):
    """Test lot cap utilization calculation."""
    validator = LotCapsValidator(
        program=ProgramType.INSTANT_FUNDING,
        starting_balance=10000.0,
        lot_caps_table=lot_caps_table,
        position_manager=position_manager,
    )

    # Add 2 lots FX position (cap is 4)
    position = Position(
        ticket=123,
        symbol="EURUSD",
        type=OrderType.BUY,
        volume=2.0,
        open_price=1.1000,
        open_time=datetime.now(timezone.utc),
        stop_loss=1.0950,
        take_profit=1.1100,
        profit=0.0,
        commission=0.0,
        swap=0.0,
    )

    idea_id = position_manager.create_idea("EURUSD", OrderType.BUY, "test", 100.0)
    position_manager.add_position(position, idea_id)

    utilization = validator.get_utilization_by_class()

    # 2/4 = 50%
    assert abs(utilization["fx"] - 50.0) < 0.1
