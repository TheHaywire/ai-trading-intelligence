"""Strategy loader and base interface."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.core.broker_mt5 import OrderRequest, OrderType
from src.core.symbols import SymbolInfo

logger = logging.getLogger(__name__)


@dataclass
class MarketState:
    """Current market state for a symbol."""

    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    bars_h1: List[Dict]  # OHLCV bars for H1
    bars_h4: List[Dict]  # OHLCV bars for H4
    bars_d1: List[Dict]  # OHLCV bars for D1
    symbol_info: SymbolInfo


@dataclass
class Signal:
    """Trading signal from strategy."""

    strategy_name: str
    symbol: str
    direction: OrderType
    entry_price: float
    stop_loss: float
    take_profit: float
    volume: float
    reason: str
    confidence: float  # 0.0 - 1.0
    metadata: Dict


class Strategy(ABC):
    """Base class for trading strategies."""

    def __init__(self, name: str, config: Dict):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            config: Strategy configuration dictionary
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)

        logger.info(f"Strategy '{name}' initialized: enabled={self.enabled}")

    @abstractmethod
    def analyze(self, state: MarketState) -> Optional[Signal]:
        """
        Analyze market state and generate signal.

        Args:
            state: Current market state

        Returns:
            Signal or None if no setup
        """
        pass

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_amount: float,
        symbol_info: SymbolInfo,
    ) -> float:
        """
        Calculate position size based on risk.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_amount: Risk amount in account currency
            symbol_info: Symbol metadata

        Returns:
            Position size in lots
        """
        stop_distance = abs(entry_price - stop_loss)
        stop_distance_pips = stop_distance / symbol_info.pip_size
        pip_value_per_lot = symbol_info.contract_size * symbol_info.pip_size

        if stop_distance_pips == 0 or pip_value_per_lot == 0:
            return symbol_info.min_lot

        lots = risk_amount / (stop_distance_pips * pip_value_per_lot)

        # Normalize
        from src.utils.calc import normalize_lot_size

        return normalize_lot_size(
            lots,
            min_lot=symbol_info.min_lot,
            max_lot=symbol_info.max_lot,
            step=symbol_info.lot_step,
        )


class StrategyLoader:
    """Loads and manages trading strategies."""

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        """Register a strategy."""
        self.strategies[strategy.name] = strategy
        logger.info(f"Registered strategy: {strategy.name}")

    def get(self, name: str) -> Optional[Strategy]:
        """Get a strategy by name."""
        return self.strategies.get(name)

    def get_all_enabled(self) -> List[Strategy]:
        """Get all enabled strategies."""
        return [s for s in self.strategies.values() if s.enabled]

    def analyze_all(self, state: MarketState) -> List[Signal]:
        """
        Run all enabled strategies on market state.

        Args:
            state: Market state

        Returns:
            List of signals from all strategies
        """
        signals = []

        for strategy in self.get_all_enabled():
            try:
                signal = strategy.analyze(state)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error in strategy {strategy.name}: {e}", exc_info=True)

        return signals
