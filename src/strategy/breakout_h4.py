"""
H4 Breakout Strategy with Confirmation

Logic:
1. Wait for 20-bar range consolidation on H4
2. Price breaks out with strong momentum
3. ADX confirms trend strength
4. Enter in direction of breakout
5. Trail stop using ATR

Why H4?
- Less noise than H1
- Clearer trends
- Lower transaction costs (fewer trades)
- Better follow-through
"""

import logging
from typing import Dict, List, Optional

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class BreakoutH4Trader(Strategy):
    """
    H4 timeframe breakout strategy with multiple confirmations.

    Entry Rules:
    - Price breaks 20-bar high/low
    - ADX > 20 (confirming trend)
    - Breakout candle > 1.5x average candle size
    - Price closes beyond breakout level

    Exit Rules:
    - Stop: 2 ATR from entry
    - Target: 3:1 risk/reward
    """

    def __init__(self, name: str = "BreakoutH4", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "lookback_period": 20,
            "adx_threshold": 20,
            "adx_period": 14,
            "breakout_size_multiplier": 1.5,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "risk_reward_ratio": 3.0,
            "session_filter": False,
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Analyze for H4 breakout opportunities."""
        if not self.enabled:
            return None

        # Need H4 data
        if len(state.bars_h4) < 100:
            return None

        bars = state.bars_h4
        lookback = self.config["lookback_period"]

        # Get recent range (exclude current bar)
        range_bars = bars[-(lookback + 1):-1]
        current_bar = bars[-1]
        prev_bar = bars[-2]

        # Calculate range high/low
        range_high = max(bar["high"] for bar in range_bars)
        range_low = min(bar["low"] for bar in range_bars)

        current_close = current_bar["close"]
        current_high = current_bar["high"]
        current_low = current_bar["low"]

        # Check for breakout
        bullish_breakout = current_close > range_high and prev_bar["close"] <= range_high
        bearish_breakout = current_close < range_low and prev_bar["close"] >= range_low

        if not bullish_breakout and not bearish_breakout:
            return None

        direction = "long" if bullish_breakout else "short"

        # Confirmation 1: ADX (trend strength)
        adx = self._calculate_adx(bars, self.config["adx_period"])
        if adx < self.config["adx_threshold"]:
            return None  # No trend, skip

        # Confirmation 2: Breakout candle size
        current_candle_size = current_high - current_low
        avg_candle_size = np.mean([bar["high"] - bar["low"] for bar in range_bars])

        if current_candle_size < avg_candle_size * self.config["breakout_size_multiplier"]:
            return None  # Weak breakout

        # Confirmation 3: Close beyond breakout level (not just wick)
        if direction == "long":
            if current_close < range_high:
                return None
        else:
            if current_close > range_low:
                return None

        # Calculate ATR for stops
        atr = self._calculate_atr(bars, self.config["atr_period"])

        # Entry and targets
        if direction == "long":
            entry_price = state.ask
            stop_loss = entry_price - (atr * self.config["atr_stop_multiplier"])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config["risk_reward_ratio"])
            order_type = OrderType.BUY
            reason = f"Bullish breakout above {range_high:.5f}, ADX={adx:.1f}"
        else:
            entry_price = state.bid
            stop_loss = entry_price + (atr * self.config["atr_stop_multiplier"])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config["risk_reward_ratio"])
            order_type = OrderType.SELL
            reason = f"Bearish breakout below {range_low:.5f}, ADX={adx:.1f}"

        # Validate
        if stop_loss <= 0 or take_profit <= 0:
            return None

        # Confidence based on ADX strength
        confidence = min(adx / 40, 1.0)  # Max confidence at ADX 40+

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"H4 {direction.upper()}: {reason}",
            confidence=confidence,
            metadata={
                "adx": adx,
                "range_high": range_high,
                "range_low": range_low,
                "atr": atr,
                "candle_size": current_candle_size,
                "avg_candle": avg_candle_size,
            }
        )

    def _calculate_adx(self, bars: List[Dict], period: int) -> float:
        """Calculate ADX."""
        if len(bars) < period + 1:
            return 0.0

        highs = np.array([bar["high"] for bar in bars])
        lows = np.array([bar["low"] for bar in bars])
        closes = np.array([bar["close"] for bar in bars])

        # True Range
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # Directional Movement
        plus_dm = np.where((highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]),
                          np.maximum(highs[1:] - highs[:-1], 0), 0)
        minus_dm = np.where((lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]),
                           np.maximum(lows[:-1] - lows[1:], 0), 0)

        # Smooth
        atr = np.zeros(len(tr))
        plus_di = np.zeros(len(plus_dm))
        minus_di = np.zeros(len(minus_dm))

        atr[period-1] = np.mean(tr[:period])
        plus_di[period-1] = np.mean(plus_dm[:period])
        minus_di[period-1] = np.mean(minus_dm[:period])

        for i in range(period, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
            plus_di[i] = (plus_di[i-1] * (period - 1) + plus_dm[i]) / period
            minus_di[i] = (minus_di[i-1] * (period - 1) + minus_dm[i]) / period

        # Calculate DI+ and DI-
        plus_di = 100 * plus_di / (atr + 1e-10)
        minus_di = 100 * minus_di / (atr + 1e-10)

        # Calculate DX and ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)

        adx = np.zeros(len(dx))
        adx[period-1] = np.mean(dx[:period])

        for i in range(period, len(dx)):
            adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period

        return adx[-1] if len(adx) > 0 else 0.0

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
