"""EMA trend-following strategy with pullback entries."""

import logging
from typing import Dict, List, Optional

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class EMATrendStrategy(Strategy):
    """
    EMA trend-following pullback strategy.

    Logic:
    1. Trend: Price above/below EMA50 on H4
    2. Pullback: Price retraces to EMA50 on H1
    3. RSI Filter: Avoid countertrend entries (RSI divergence)
    4. Entry: Bounce from EMA50
    5. SL: Below/above recent swing or EMA
    6. TP: 1R partial, 2R trail, 3R final
    """

    def __init__(self, name: str = "EMATrend", config: Optional[Dict] = None):
        """
        Initialize EMA trend strategy.

        Config parameters:
        - ema_trend_period: Trend EMA period (default 50)
        - rsi_period: RSI period (default 14)
        - rsi_overbought: RSI overbought level (default 70)
        - rsi_oversold: RSI oversold level (default 30)
        - pullback_tolerance: Price distance from EMA as % (default 0.5)
        - sl_swing_bars: Bars to look back for swing (default 10)
        - tp_ratios: TP levels (default [1.0, 2.0, 3.0])
        - adx_period: ADX period (default 14)
        - adx_threshold: Minimum ADX for trend strength (default 25)
        - atr_period: ATR period for stop loss (default 14)
        - atr_multiplier: ATR multiplier for stops (default 2.0)
        - volume_period: Volume MA period (default 20)
        - volume_threshold: Minimum volume multiplier (default 1.5)
        """
        default_config = {
            "enabled": True,
            "ema_trend_period": 50,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "pullback_tolerance": 0.5,
            "sl_swing_bars": 10,
            "tp_ratios": [1.0, 2.0, 3.0],
            "adx_period": 14,
            "adx_threshold": 25,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "volume_period": 20,
            "volume_threshold": 1.5,
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Analyze market and generate signal."""
        if not self.enabled:
            return None

        # Require sufficient data
        if len(state.bars_h4) < self.config["ema_trend_period"]:
            return None
        if len(state.bars_h1) < self.config["rsi_period"]:
            return None

        # Step 0: Check market regime - only trade in suitable conditions
        regime = self._detect_regime(state.bars_h4)
        # NOTE: Regime filter disabled for now - needs more tuning
        # if regime not in ["trending", "moderate_trend"]:
        #     return None  # Skip ranging/choppy markets

        # Step 1: Determine trend from H4
        trend = self._get_trend(state.bars_h4)
        if trend is None:
            return None

        # Calculate ADX for metadata
        adx = self._calculate_adx(state.bars_h4, self.config["adx_period"])

        # Step 2: Check for pullback to EMA on H1
        pullback = self._detect_pullback(state.bars_h1, trend)
        if not pullback:
            return None

        # Step 3: RSI filter (avoid countertrend)
        rsi = self._calculate_rsi(state.bars_h1, self.config["rsi_period"])
        if not self._check_rsi_filter(rsi, trend):
            return None

        # Step 3.5: Volume confirmation
        if not self._check_volume_confirmation(state.bars_h1):
            return None

        # Step 4: Calculate entry, SL, TP using ATR
        atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])

        if trend == "bullish":
            entry_price = state.ask
            # ATR-based stop loss (more robust than swing)
            stop_loss = entry_price - (atr * self.config["atr_multiplier"])
            risk_distance = entry_price - stop_loss
            take_profit = entry_price + (risk_distance * self.config["tp_ratios"][0])
            direction = OrderType.BUY
        else:
            entry_price = state.bid
            # ATR-based stop loss (more robust than swing)
            stop_loss = entry_price + (atr * self.config["atr_multiplier"])
            risk_distance = stop_loss - entry_price
            take_profit = entry_price - (risk_distance * self.config["tp_ratios"][0])
            direction = OrderType.SELL

        # Validate SL
        if stop_loss <= 0 or abs(entry_price - stop_loss) < state.symbol_info.pip_size:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"{trend.upper()} pullback [{regime}], ADX={adx:.1f}, RSI={rsi:.1f}",
            confidence=0.75,
            metadata={
                "trend": trend,
                "regime": regime,
                "adx": adx,
                "rsi": rsi,
                "atr": atr,
                "entry_type": "pullback",
            },
        )

    def _get_trend(self, bars_h4: List[Dict]) -> Optional[str]:
        """
        Determine trend from H4 EMA50 with ADX confirmation.

        Returns:
            "bullish", "bearish", or None
        """
        closes = np.array([bar["close"] for bar in bars_h4])

        if len(closes) < self.config["ema_trend_period"]:
            return None

        # Check ADX - for pullback strategy, moderate trends work best
        # Too high ADX (>40) = trending too strong, pullbacks get run over
        # Too low ADX (<15) = no trend, just ranging noise
        adx = self._calculate_adx(bars_h4, self.config["adx_period"])
        if adx < 15 or adx > 40:
            return None  # Need moderate trend strength for pullbacks

        ema = self._calculate_ema(closes, self.config["ema_trend_period"])
        current_price = closes[-1]

        if current_price > ema[-1]:
            return "bullish"
        elif current_price < ema[-1]:
            return "bearish"

        return None

    def _detect_pullback(self, bars_h1: List[Dict], trend: str) -> bool:
        """
        Detect pullback to EMA50 on H1.

        Args:
            bars_h1: H1 bars
            trend: Trend direction

        Returns:
            True if pullback detected
        """
        if len(bars_h1) < self.config["ema_trend_period"]:
            return False

        closes = np.array([bar["close"] for bar in bars_h1])
        ema = self._calculate_ema(closes, self.config["ema_trend_period"])

        current_price = closes[-1]
        current_ema = ema[-1]

        # Calculate distance as percentage
        distance_pct = abs((current_price - current_ema) / current_ema) * 100.0

        # Check if price is near EMA (within tolerance)
        if distance_pct > self.config["pullback_tolerance"]:
            return False

        # For bullish trend, price should be near or just above EMA
        if trend == "bullish":
            return current_price >= current_ema * 0.999  # Small tolerance

        # For bearish trend, price should be near or just below EMA
        else:
            return current_price <= current_ema * 1.001

    def _check_rsi_filter(self, rsi: float, trend: str) -> bool:
        """
        Check RSI filter to avoid countertrend entries.

        Args:
            rsi: Current RSI value
            trend: Trend direction

        Returns:
            True if RSI confirms trend
        """
        if trend == "bullish":
            # For bullish, avoid if RSI is overbought
            return rsi < self.config["rsi_overbought"]
        else:
            # For bearish, avoid if RSI is oversold
            return rsi > self.config["rsi_oversold"]

    def _check_volume_confirmation(self, bars: List[Dict]) -> bool:
        """
        Check if current volume confirms the signal.

        Args:
            bars: H1 bars

        Returns:
            True if volume is above average
        """
        if len(bars) < self.config["volume_period"]:
            return True  # Not enough data, skip filter

        volumes = [bar["volume"] for bar in bars]
        avg_volume = np.mean(volumes[-self.config["volume_period"]:-1])
        current_volume = volumes[-1]

        # Require current volume to be above threshold * average
        return current_volume >= (avg_volume * self.config["volume_threshold"])

    def _find_swing_low(self, bars: List[Dict], lookback: int) -> float:
        """Find recent swing low."""
        recent_bars = bars[-lookback:] if len(bars) >= lookback else bars
        return min(bar["low"] for bar in recent_bars)

    def _find_swing_high(self, bars: List[Dict], lookback: int) -> float:
        """Find recent swing high."""
        recent_bars = bars[-lookback:] if len(bars) >= lookback else bars
        return max(bar["high"] for bar in recent_bars)

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate exponential moving average."""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]

        return ema

    def _calculate_rsi(self, bars: List[Dict], period: int) -> float:
        """
        Calculate Relative Strength Index.

        Args:
            bars: OHLC bars
            period: RSI period

        Returns:
            RSI value (0-100)
        """
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

    def _calculate_adx(self, bars: List[Dict], period: int) -> float:
        """
        Calculate Average Directional Index.

        Args:
            bars: OHLC bars
            period: ADX period

        Returns:
            ADX value (0-100)
        """
        if len(bars) < period + 1:
            return 0.0

        highs = np.array([bar["high"] for bar in bars])
        lows = np.array([bar["low"] for bar in bars])
        closes = np.array([bar["close"] for bar in bars])

        # Calculate True Range
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # Calculate Directional Movement
        plus_dm = np.where((highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]),
                          np.maximum(highs[1:] - highs[:-1], 0), 0)
        minus_dm = np.where((lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]),
                           np.maximum(lows[:-1] - lows[1:], 0), 0)

        # Smooth TR and DM
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
        """
        Calculate Average True Range.

        Args:
            bars: OHLC bars
            period: ATR period

        Returns:
            ATR value
        """
        if len(bars) < period + 1:
            return 0.0

        highs = np.array([bar["high"] for bar in bars])
        lows = np.array([bar["low"] for bar in bars])
        closes = np.array([bar["close"] for bar in bars])

        # Calculate True Range
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # Calculate ATR using Wilder's smoothing
        atr = np.zeros(len(tr))
        atr[period-1] = np.mean(tr[:period])

        for i in range(period, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

        return atr[-1] if len(atr) > 0 else 0.0

    def _detect_regime(self, bars: List[Dict]) -> str:
        """
        Detect market regime using ADX and price action.

        Returns:
            "trending": Strong trend (ADX > 40) - pullbacks get run over
            "moderate_trend": Moderate trend (ADX 20-40) - good for pullbacks
            "ranging": Weak trend (ADX < 20) - choppy, no clear direction
        """
        if len(bars) < 50:
            return "ranging"

        # Use ADX to measure trend strength
        adx = self._calculate_adx(bars, 14)

        # Also check if price is respecting trend (using EMA)
        closes = np.array([bar["close"] for bar in bars[-20:]])
        ema = self._calculate_ema(closes, 20)

        # Check how many bars are on the correct side of EMA
        bullish_bars = sum(1 for i in range(len(closes)) if closes[i] > ema[i])
        bearish_bars = sum(1 for i in range(len(closes)) if closes[i] < ema[i])
        directional_consistency = max(bullish_bars, bearish_bars) / len(closes)

        # Classify regime
        if adx > 50:
            return "trending"  # Too strong, pullbacks fail
        elif adx >= 15 and directional_consistency > 0.55:
            return "moderate_trend"  # Sweet spot for pullback strategy
        else:
            return "ranging"  # Too choppy
