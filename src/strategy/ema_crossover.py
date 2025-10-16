"""
EMA Crossover Strategy - The Classic

Dead simple trend following:
- Fast EMA crosses above slow EMA = BUY
- Fast EMA crosses below slow EMA = SELL

Optional filters:
- ADX (trend strength)
- ATR (volatility range)
- Session (NY only)
"""

import logging
from typing import Dict, List, Optional

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class EMACrossover(Strategy):
    """Classic EMA crossover with optional filters."""

    def __init__(self, name: str = "EMACross", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "fast_ema": 20,
            "slow_ema": 50,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "atr_target_multiplier": 3.0,
            # Optional filters (disabled by default)
            "use_adx_filter": False,
            "adx_threshold": 25,
            "adx_period": 14,
            "use_atr_filter": False,
            "atr_min_pct": 0.05,  # Min 0.05% ATR
            "atr_max_pct": 0.30,  # Max 0.30% ATR
            "use_session_filter": False,
            "ny_only": False,
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)
        self.last_cross_direction = None  # Track to avoid duplicate signals

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Analyze for EMA crossover."""
        if not self.enabled:
            return None

        if len(state.bars_h1) < 100:
            return None

        bars = state.bars_h1
        closes = np.array([bar["close"] for bar in bars])

        # Calculate EMAs
        ema_fast = self._calculate_ema(closes, self.config["fast_ema"])
        ema_slow = self._calculate_ema(closes, self.config["slow_ema"])

        # Check for crossover
        current_fast = ema_fast[-1]
        current_slow = ema_slow[-1]
        prev_fast = ema_fast[-2]
        prev_slow = ema_slow[-2]

        # Detect crossover
        bullish_cross = prev_fast <= prev_slow and current_fast > current_slow
        bearish_cross = prev_fast >= prev_slow and current_fast < current_slow

        if not bullish_cross and not bearish_cross:
            return None

        direction = "long" if bullish_cross else "short"

        # Avoid duplicate signals on same crossover
        if direction == self.last_cross_direction:
            return None

        # Optional Filter 1: ADX (trend strength)
        if self.config["use_adx_filter"]:
            adx = self._calculate_adx(bars, self.config["adx_period"])
            if adx < self.config["adx_threshold"]:
                return None  # Not trending enough

        # Optional Filter 2: ATR (volatility range)
        if self.config["use_atr_filter"]:
            atr = self._calculate_atr(bars, self.config["atr_period"])
            current_price = closes[-1]
            atr_pct = (atr / current_price) * 100

            if atr_pct < self.config["atr_min_pct"] or atr_pct > self.config["atr_max_pct"]:
                return None  # Volatility out of range

        # Optional Filter 3: Session
        if self.config["use_session_filter"]:
            session = self._get_session(state.timestamp)
            if self.config["ny_only"] and session != "ny":
                return None  # Not NY session

        # Calculate stops and targets
        atr = self._calculate_atr(bars, self.config["atr_period"])

        if direction == "long":
            entry_price = state.ask
            stop_loss = entry_price - (atr * self.config["atr_stop_multiplier"])
            take_profit = entry_price + (atr * self.config["atr_target_multiplier"])
            order_type = OrderType.BUY
        else:
            entry_price = state.bid
            stop_loss = entry_price + (atr * self.config["atr_stop_multiplier"])
            take_profit = entry_price - (atr * self.config["atr_target_multiplier"])
            order_type = OrderType.SELL

        # Validate
        if stop_loss <= 0 or take_profit <= 0:
            return None

        # Update last cross
        self.last_cross_direction = direction

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"EMA {self.config['fast_ema']}/{self.config['slow_ema']} {'bull' if bullish_cross else 'bear'} cross",
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
