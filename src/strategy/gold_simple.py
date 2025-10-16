"""Simple Gold strategy that actually trades - NO BULLSHIT."""

import logging
from typing import Dict, List, Optional
import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class GoldSimpleStrategy(Strategy):
    """
    Dead simple Gold strategy - trades momentum moves.
    NO session filters, NO symbol restrictions, NO BS factors.
    """
    
    def __init__(self, name: str = "GoldSimple", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "ma_period": 20,           # 20-bar moving average
            "momentum_threshold": 0.5,  # 0.5% move triggers trade
            "risk_distance": 0.8,      # 0.8% stop loss
            "min_bars": 25,            # Need 25 bars minimum
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(name, default_config)
    
    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Generate signal if momentum is strong enough."""
        if not self.enabled:
            return None
        
        bars = state.bars_h1
        if len(bars) < self.config["min_bars"]:
            return None
        
        # Get current price and MA
        current_price = bars[-1]["close"]
        ma = self._calculate_ma([b["close"] for b in bars], self.config["ma_period"])
        
        if ma is None:
            return None
        
        # Calculate momentum
        momentum_pct = (current_price - ma) / ma * 100
        
        # Generate signal based on momentum
        signal_type = None
        
        # Strong bullish momentum
        if momentum_pct > self.config["momentum_threshold"]:
            signal_type = "buy"
            entry_price = state.ask
            stop_loss = current_price * (1 - self.config["risk_distance"] / 100)
            direction = OrderType.BUY
        
        # Strong bearish momentum  
        elif momentum_pct < -self.config["momentum_threshold"]:
            signal_type = "sell"
            entry_price = state.bid
            stop_loss = current_price * (1 + self.config["risk_distance"] / 100)
            direction = OrderType.SELL
        
        if signal_type is None:
            return None
        
        # Calculate take profit (2x risk)
        risk_amount = abs(entry_price - stop_loss)
        if signal_type == "buy":
            take_profit = entry_price + risk_amount * 2
        else:
            take_profit = entry_price - risk_amount * 2
        
        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"{signal_type.upper()}: momentum {momentum_pct:.1f}%, MA {ma:.2f}",
            confidence=0.7 if abs(momentum_pct) > 1.0 else 0.5,
            metadata={
                "signal_type": signal_type,
                "momentum_pct": momentum_pct,
                "ma_price": ma,
                "risk_distance": self.config["risk_distance"],
            },
        )
    
    def _calculate_ma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate simple moving average."""
        if len(prices) < period:
            return None
        
        recent_prices = prices[-period:]
        return sum(recent_prices) / len(recent_prices)
