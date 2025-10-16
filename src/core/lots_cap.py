"""Lot caps validator for cumulative position limits."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.core.config import LotCapsTable, ProgramType
from src.core.positions import Position, PositionManager
from src.core.symbols import AssetClass, SymbolInfo, get_registry

logger = logging.getLogger(__name__)


@dataclass
class LotCapCheck:
    """Result of a lot cap validation."""

    approved: bool
    reason: str
    current_lots: Dict[str, float]
    limits: Dict[str, float]
    metadata: dict


class LotCapsValidator:
    """
    Validates cumulative lot limits by asset class.

    Enforces per-program cumulative caps across symbol classes (FX, indices, commodities, crypto).
    """

    def __init__(
        self,
        program: ProgramType,
        starting_balance: float,
        lot_caps_table: LotCapsTable,
        position_manager: PositionManager,
    ):
        """
        Initialize lot caps validator.

        Args:
            program: Program type
            starting_balance: Account starting balance
            lot_caps_table: Lot caps configuration table
            position_manager: Position manager
        """
        self.program = program
        self.starting_balance = starting_balance
        self.lot_caps_table = lot_caps_table
        self.position_manager = position_manager
        self.symbol_registry = get_registry()

        # Get caps for this program and balance
        self.caps = self._load_caps()

        logger.info(
            f"Lot caps validator initialized: program={program.value}, "
            f"balance={starting_balance:.0f}, caps={self.caps}"
        )

    def _load_caps(self) -> Dict[str, float]:
        """Load lot caps for the current program and balance."""
        caps = self.lot_caps_table.get_caps(self.program.value, self.starting_balance)

        if caps is None:
            logger.warning(
                f"No lot caps found for {self.program.value} with balance {self.starting_balance:.0f}, "
                "using unlimited"
            )
            return {
                "fx": float("inf"),
                "indices": float("inf"),
                "commodities": float("inf"),
                "crypto": float("inf"),
            }

        return caps

    def check_order(self, symbol: str, volume: float, is_opening: bool = True) -> LotCapCheck:
        """
        Check if an order would breach lot caps.

        Args:
            symbol: Trading symbol
            volume: Order volume in lots
            is_opening: True if opening new position, False if closing

        Returns:
            LotCapCheck result
        """
        symbol_info = self.symbol_registry.get(symbol)

        if symbol_info is None:
            return LotCapCheck(
                approved=False,
                reason=f"Unknown symbol: {symbol}",
                current_lots={},
                limits={},
                metadata={},
            )

        asset_class = symbol_info.asset_class.value

        # Get current cumulative lots by class
        current_lots = self._get_current_lots_by_class()

        # Check if this order would breach
        if is_opening:
            projected_lots = current_lots.get(asset_class, 0.0) + volume
            limit = self.caps.get(asset_class, float("inf"))

            if projected_lots > limit:
                return LotCapCheck(
                    approved=False,
                    reason=f"Lot cap exceeded for {asset_class}: {projected_lots:.2f} > {limit:.2f}",
                    current_lots=current_lots,
                    limits=self.caps,
                    metadata={
                        "symbol": symbol,
                        "asset_class": asset_class,
                        "order_volume": volume,
                        "current": current_lots.get(asset_class, 0.0),
                        "projected": projected_lots,
                        "limit": limit,
                    },
                )

        # Approved
        return LotCapCheck(
            approved=True,
            reason="Lot cap check passed",
            current_lots=current_lots,
            limits=self.caps,
            metadata={
                "symbol": symbol,
                "asset_class": asset_class,
                "order_volume": volume,
            },
        )

    def _get_current_lots_by_class(self) -> Dict[str, float]:
        """
        Get current cumulative lots by asset class.

        Returns:
            Dictionary mapping asset class to total lots
        """
        lots_by_class: Dict[str, float] = {
            "fx": 0.0,
            "indices": 0.0,
            "commodities": 0.0,
            "crypto": 0.0,
        }

        positions = self.position_manager.get_all_open_positions()

        for position in positions:
            symbol_info = self.symbol_registry.get(position.symbol)
            if symbol_info:
                asset_class = symbol_info.asset_class.value
                lots_by_class[asset_class] = lots_by_class.get(asset_class, 0.0) + position.volume

        return lots_by_class

    def get_utilization_by_class(self) -> Dict[str, float]:
        """
        Get lot cap utilization by asset class.

        Returns:
            Dictionary mapping asset class to utilization percentage
        """
        current_lots = self._get_current_lots_by_class()
        utilization = {}

        for asset_class, limit in self.caps.items():
            current = current_lots.get(asset_class, 0.0)
            if limit > 0 and limit != float("inf"):
                utilization[asset_class] = (current / limit) * 100.0
            else:
                utilization[asset_class] = 0.0

        return utilization

    def get_remaining_capacity(self, asset_class: str) -> float:
        """
        Get remaining lot capacity for an asset class.

        Args:
            asset_class: Asset class name

        Returns:
            Remaining lots available
        """
        current_lots = self._get_current_lots_by_class()
        current = current_lots.get(asset_class, 0.0)
        limit = self.caps.get(asset_class, float("inf"))

        if limit == float("inf"):
            return float("inf")

        return max(0.0, limit - current)

    def get_summary(self) -> dict:
        """Get lot caps summary."""
        current_lots = self._get_current_lots_by_class()
        utilization = self.get_utilization_by_class()

        return {
            "program": self.program.value,
            "starting_balance": self.starting_balance,
            "limits": self.caps,
            "current_lots": current_lots,
            "utilization": utilization,
            "remaining": {
                asset_class: self.get_remaining_capacity(asset_class)
                for asset_class in self.caps.keys()
            },
        }
