"""Position and trade idea management."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from uuid import uuid4

from src.core.broker_mt5 import OrderType, Position

logger = logging.getLogger(__name__)


@dataclass
class TradeIdea:
    """
    Represents a logical trade idea that may consist of multiple positions.

    Positions are grouped by idea_id for risk management purposes.
    """

    idea_id: str
    symbol: str
    direction: OrderType
    entry_time: datetime
    strategy: str
    risk_amount: float
    positions: List[Position] = field(default_factory=list)
    closed: bool = False
    close_time: Optional[datetime] = None
    realized_pnl: float = 0.0
    comment: str = ""

    @property
    def total_volume(self) -> float:
        """Get total position volume for this idea."""
        return sum(p.volume for p in self.positions if not self.closed)

    @property
    def unrealized_pnl(self) -> float:
        """Get total unrealized PnL."""
        return sum(p.net_profit for p in self.positions if not self.closed)

    @property
    def avg_entry_price(self) -> float:
        """Get volume-weighted average entry price."""
        if not self.positions:
            return 0.0
        total_volume = sum(p.volume for p in self.positions)
        if total_volume == 0:
            return 0.0
        weighted_sum = sum(p.open_price * p.volume for p in self.positions)
        return weighted_sum / total_volume

    @property
    def is_long(self) -> bool:
        """Check if this is a long idea."""
        return self.direction in (OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP)

    def add_position(self, position: Position) -> None:
        """Add a position to this trade idea."""
        self.positions.append(position)
        logger.debug(f"Added position {position.ticket} to idea {self.idea_id}")

    def close_idea(self, realized_pnl: float, now: Optional[datetime] = None) -> None:
        """Mark the trade idea as closed."""
        if now is None:
            now = datetime.now(timezone.utc)
        self.closed = True
        self.close_time = now
        self.realized_pnl = realized_pnl
        logger.info(f"Closed idea {self.idea_id}: PnL={realized_pnl:.2f}")


class PositionManager:
    """
    Manages positions and groups them into trade ideas.

    Tracks:
    - Open positions by ticket
    - Trade ideas by idea_id
    - Position counts per symbol
    - Total exposure by symbol and asset class
    """

    def __init__(self) -> None:
        self.positions: Dict[int, Position] = {}  # ticket -> Position
        self.ideas: Dict[str, TradeIdea] = {}  # idea_id -> TradeIdea
        self.position_to_idea: Dict[int, str] = {}  # ticket -> idea_id

    def create_idea(
        self,
        symbol: str,
        direction: OrderType,
        strategy: str,
        risk_amount: float,
        comment: str = "",
    ) -> str:
        """
        Create a new trade idea.

        Args:
            symbol: Trading symbol
            direction: Trade direction
            strategy: Strategy name
            risk_amount: Risk amount in account currency
            comment: Optional comment

        Returns:
            idea_id
        """
        idea_id = str(uuid4())
        idea = TradeIdea(
            idea_id=idea_id,
            symbol=symbol,
            direction=direction,
            entry_time=datetime.now(timezone.utc),
            strategy=strategy,
            risk_amount=risk_amount,
            comment=comment,
        )
        self.ideas[idea_id] = idea
        logger.info(f"Created idea {idea_id}: {symbol} {direction.value} via {strategy}")
        return idea_id

    def add_position(self, position: Position, idea_id: str) -> None:
        """
        Add a position and link it to a trade idea.

        Args:
            position: Position object
            idea_id: Trade idea ID
        """
        self.positions[position.ticket] = position
        self.position_to_idea[position.ticket] = idea_id

        if idea_id in self.ideas:
            self.ideas[idea_id].add_position(position)

        logger.debug(f"Added position {position.ticket} to manager, linked to idea {idea_id}")

    def remove_position(self, ticket: int) -> Optional[Position]:
        """
        Remove a position (when closed).

        Args:
            ticket: Position ticket

        Returns:
            Removed Position or None
        """
        position = self.positions.pop(ticket, None)
        idea_id = self.position_to_idea.pop(ticket, None)

        if position and idea_id and idea_id in self.ideas:
            idea = self.ideas[idea_id]
            idea.positions = [p for p in idea.positions if p.ticket != ticket]

            # If idea has no more open positions, mark as closed
            if not idea.positions and not idea.closed:
                total_pnl = sum(p.net_profit for p in self.positions.values() if self.position_to_idea.get(p.ticket) == idea_id)
                idea.close_idea(total_pnl)

        return position

    def get_position(self, ticket: int) -> Optional[Position]:
        """Get position by ticket."""
        return self.positions.get(ticket)

    def get_idea(self, idea_id: str) -> Optional[TradeIdea]:
        """Get trade idea by ID."""
        return self.ideas.get(idea_id)

    def get_idea_for_position(self, ticket: int) -> Optional[TradeIdea]:
        """Get the trade idea associated with a position."""
        idea_id = self.position_to_idea.get(ticket)
        return self.ideas.get(idea_id) if idea_id else None

    def get_positions_for_symbol(self, symbol: str) -> List[Position]:
        """Get all open positions for a symbol."""
        return [p for p in self.positions.values() if p.symbol.upper() == symbol.upper()]

    def get_ideas_for_symbol(self, symbol: str) -> List[TradeIdea]:
        """Get all trade ideas for a symbol."""
        return [idea for idea in self.ideas.values() if idea.symbol.upper() == symbol.upper() and not idea.closed]

    def count_positions_for_symbol(self, symbol: str) -> int:
        """Count open positions for a symbol."""
        return len(self.get_positions_for_symbol(symbol))

    def get_total_volume_for_symbol(self, symbol: str) -> float:
        """Get total volume across all positions for a symbol."""
        return sum(p.volume for p in self.get_positions_for_symbol(symbol))

    def get_total_exposure_by_class(self, asset_class: str) -> float:
        """
        Get total notional exposure for an asset class.

        Args:
            asset_class: Asset class name (fx, indices, commodities, crypto)

        Returns:
            Total exposure (sum of volumes)
        """
        # This is simplified - in production you'd track notional value
        from src.core.symbols import get_registry

        registry = get_registry()
        total = 0.0

        for position in self.positions.values():
            symbol_info = registry.get(position.symbol)
            if symbol_info and symbol_info.asset_class.value == asset_class:
                total += position.volume

        return total

    def get_all_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())

    def get_all_open_ideas(self) -> List[TradeIdea]:
        """Get all open trade ideas."""
        return [idea for idea in self.ideas.values() if not idea.closed]

    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized PnL across all positions."""
        return sum(p.net_profit for p in self.positions.values())

    def sync_with_broker_positions(self, broker_positions: List[Position]) -> None:
        """
        Synchronize internal state with broker positions.

        Args:
            broker_positions: List of positions from broker
        """
        broker_tickets = {p.ticket for p in broker_positions}
        internal_tickets = set(self.positions.keys())

        # Remove positions that broker doesn't have (closed externally)
        closed_tickets = internal_tickets - broker_tickets
        for ticket in closed_tickets:
            logger.info(f"Position {ticket} closed externally")
            self.remove_position(ticket)

        # Update existing positions
        for broker_pos in broker_positions:
            if broker_pos.ticket in self.positions:
                self.positions[broker_pos.ticket] = broker_pos
            else:
                # New position opened externally
                logger.warning(f"Unknown position {broker_pos.ticket} found - creating orphan idea")
                idea_id = self.create_idea(
                    symbol=broker_pos.symbol,
                    direction=broker_pos.type,
                    strategy="external",
                    risk_amount=0.0,
                    comment="Opened externally",
                )
                self.add_position(broker_pos, idea_id)

    def get_summary(self) -> dict:
        """Get summary of position manager state."""
        return {
            "total_positions": len(self.positions),
            "total_ideas": len(self.ideas),
            "open_ideas": len([i for i in self.ideas.values() if not i.closed]),
            "total_unrealized_pnl": self.get_total_unrealized_pnl(),
            "symbols_traded": len(set(p.symbol for p in self.positions.values())),
        }
