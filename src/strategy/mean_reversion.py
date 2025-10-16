"""
Mean Reversion Strategy - Simple and Robust

Logic:
1. Price stretches too far from 20 EMA (bollinger bands)
2. RSI confirms oversold/overbought
3. Enter when both align, exit at mean
4. Works in ranging markets (60-70% of the time)

No complex ensemble, no overfitting, just pure mean reversion.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class MeanReversionTrader(Strategy):
    """
    Simple mean reversion strategy that works in ranging markets.

    Entry Rules:
    - Price > 2 std dev above 20 EMA AND RSI > 70 → SHORT
    - Price < 2 std dev below 20 EMA AND RSI < 30 → LONG

    Exit Rules:
    - Target: Price returns to 20 EMA
    - Stop: 2x the distance from entry to EMA
    """

    def __init__(self, name: str = "MeanReversion", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "ema_period": 20,
            "bb_std_dev": 2.0,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_period": 14,
            "risk_reward_ratio": 1.5,  # Conservative
            "session_filter": True,
            "ny_only": False,  # Mean reversion works better in all sessions
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Analyze for mean reversion opportunities."""
        if not self.enabled:
            return None

        if len(state.bars_h1) < 100:
            return None

        # Session filter (optional)
        if self.config["session_filter"]:
            session = self._get_session(state.timestamp)
            if self.config.get("ny_only", False) and session != "ny":
                return None

        # Get H1 data
        closes = np.array([bar["close"] for bar in state.bars_h1])
        highs = np.array([bar["high"] for bar in state.bars_h1])
        lows = np.array([bar["low"] for bar in state.bars_h1])

        # Calculate EMA and Bollinger Bands
        ema = self._calculate_ema(closes, self.config["ema_period"])
        std = self._calculate_std(closes, self.config["ema_period"])

        upper_band = ema + (std * self.config["bb_std_dev"])
        lower_band = ema - (std * self.config["bb_std_dev"])

        # Calculate RSI
        rsi = self._calculate_rsi(state.bars_h1, self.config["rsi_period"])

        # Current values
        current_price = closes[-1]
        current_ema = ema[-1]
        current_upper = upper_band[-1]
        current_lower = lower_band[-1]

        # Check for mean reversion setups
        direction = None
        reason = ""

        # LONG: Price stretched below, RSI oversold
        if current_price < current_lower and rsi < self.config["rsi_oversold"]:
            direction = "long"
            distance_from_mean = current_ema - current_price
            reason = f"Oversold: Price {distance_from_mean:.5f} below EMA, RSI={rsi:.1f}"

        # SHORT: Price stretched above, RSI overbought
        elif current_price > current_upper and rsi > self.config["rsi_overbought"]:
            direction = "short"
            distance_from_mean = current_price - current_ema
            reason = f"Overbought: Price {distance_from_mean:.5f} above EMA, RSI={rsi:.1f}"

        if not direction:
            return None

        # Calculate ATR for stop placement
        atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])

        # Entry and targets
        if direction == "long":
            entry_price = state.ask
            # Target: Return to EMA
            take_profit = current_ema
            # Stop: 2x distance from entry to EMA (or min 2 ATR)
            distance_to_mean = current_ema - entry_price
            stop_distance = max(distance_to_mean * 2, atr * 2)
            stop_loss = entry_price - stop_distance
            order_type = OrderType.BUY
        else:
            entry_price = state.bid
            # Target: Return to EMA
            take_profit = current_ema
            # Stop: 2x distance from entry to EMA (or min 2 ATR)
            distance_to_mean = entry_price - current_ema
            stop_distance = max(distance_to_mean * 2, atr * 2)
            stop_loss = entry_price + stop_distance
            order_type = OrderType.SELL

        # Validate
        if stop_loss <= 0 or take_profit <= 0:
            return None

        # Risk:Reward check
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if reward < 0.0001:  # Too close to mean
            return None

        rr_ratio = reward / risk if risk > 0 else 0

        if rr_ratio < 0.5:  # Need at least 0.5:1 (we're betting on high win rate)
            return None

        # Build signal
        confidence = min(abs(rsi - 50) / 50, 1.0)  # More extreme = higher confidence

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"MR {direction.upper()}: {reason}",
            confidence=confidence,
            metadata={
                "rsi": rsi,
                "ema": current_ema,
                "upper_band": current_upper,
                "lower_band": current_lower,
                "atr": atr,
                "rr_ratio": rr_ratio,
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

    def _calculate_std(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate rolling standard deviation."""
        std = np.zeros_like(data)

        for i in range(period - 1, len(data)):
            std[i] = np.std(data[i - period + 1:i + 1])

        return std

    def _calculate_rsi(self, bars: List[Dict], period: int) -> float:
        """Calculate RSI."""
        if len(bars) < period + 1:
            return 50.0

        closes = np.array([bar["close"] for bar in bars])
        deltas = np.diff(closes)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi

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
        atr[period - 1] = np.mean(tr[:period])

        for i in range(period, len(tr)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        return atr[-1] if len(atr) > 0 else 0.0

    def _get_session(self, timestamp) -> str:
        """Determine trading session."""
        hour = timestamp.hour

        if 8 <= hour < 16:
            return "london"
        elif 13 <= hour < 21:
            return "ny"
        elif 0 <= hour < 8:
            return "asia"
        else:
            return "off_hours"
