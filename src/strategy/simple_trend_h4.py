"""
Dead Simple Trend Following - H4 Timeframe

The simplest profitable setup:
1. 20 EMA > 50 EMA = uptrend, go LONG on pullback to 20 EMA
2. 20 EMA < 50 EMA = downtrend, go SHORT on pullback to 20 EMA
3. Stop: 2 ATR
4. Target: 3 ATR

That's it. No bullshit, no complexity, just follow the trend.
"""

import logging
from typing import Dict, List, Optional

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class SimpleTrendH4(Strategy):
    """
    Simple trend following on H4.
    Buy pullbacks in uptrends, sell rallies in downtrends.
    """

    def __init__(self, name: str = "SimpleTrend", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "fast_ema": 20,
            "slow_ema": 50,
            "atr_period": 14,
            "atr_stop": 2.0,
            "atr_target": 3.0,
            "pullback_threshold": 0.3,  # Price within 30% of fast EMA
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Simple trend analysis."""
        if not self.enabled:
            return None

        # Use H4 bars if available, otherwise use H1 bars
        bars = state.bars_h4 if state.bars_h4 and len(state.bars_h4) >= 100 else state.bars_h1

        if len(bars) < 100:
            return None
        closes = np.array([bar["close"] for bar in bars])

        # EMAs
        ema_fast = self._calculate_ema(closes, self.config["fast_ema"])
        ema_slow = self._calculate_ema(closes, self.config["slow_ema"])

        current_price = closes[-1]
        current_fast = ema_fast[-1]
        current_slow = ema_slow[-1]

        # Trend determination
        uptrend = current_fast > current_slow
        downtrend = current_fast < current_slow

        if not uptrend and not downtrend:
            return None

        # ATR for stops
        atr = self._calculate_atr(bars, self.config["atr_period"])

        # Check for pullback to fast EMA
        distance_to_fast = abs(current_price - current_fast)
        pullback_zone = atr * self.config["pullback_threshold"]

        if distance_to_fast > pullback_zone:
            return None  # Too far from EMA

        # Generate signal
        if uptrend and current_price <= current_fast:
            # Pullback to EMA in uptrend - BUY
            entry_price = state.ask
            stop_loss = entry_price - (atr * self.config["atr_stop"])
            take_profit = entry_price + (atr * self.config["atr_target"])
            order_type = OrderType.BUY
            direction = "long"
            reason = f"Uptrend pullback to EMA20 ({current_fast:.5f})"

        elif downtrend and current_price >= current_fast:
            # Rally to EMA in downtrend - SELL
            entry_price = state.bid
            stop_loss = entry_price + (atr * self.config["atr_stop"])
            take_profit = entry_price - (atr * self.config["atr_target"])
            order_type = OrderType.SELL
            direction = "short"
            reason = f"Downtrend rally to EMA20 ({current_fast:.5f})"

        else:
            return None

        # Validate
        if stop_loss <= 0 or take_profit <= 0:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"TREND {direction.upper()}: {reason}",
            confidence=0.7,
            metadata={
                "ema_fast": current_fast,
                "ema_slow": current_slow,
                "atr": atr,
            }
        )

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA."""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]

        return ema

    def _calculate_atr(self, bars: List[Dict], period: int) -> float:
        """Calculate ATR."""
        if len(bars) < period + 1:
            return 0.0

        highs = np.array([bar["high"] for bar in bars])
        lows = np.array([bar["low"] for bar in bars])
        closes = np.array([bar["close"] for bar in bars])

        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        atr = np.zeros(len(tr))
        atr[period-1] = np.mean(tr[:period])

        for i in range(period, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

        return atr[-1] if len(atr) > 0 else 0.0
