"""
MVP: Different Signal Generation Approaches for MT5 Trading

This file demonstrates 6 practical signal generation methods:
1. Technical Indicators (MA Crossover, RSI, MACD)
2. Price Action Patterns (Support/Resistance, Candlestick patterns)
3. Multi-Timeframe Confluence
4. Volume-Based Signals
5. Statistical Mean Reversion
6. Ensemble/Hybrid (Combining multiple signals)

Each strategy is self-contained and ready to use.
"""

import logging
from typing import Dict, List, Optional
from enum import Enum
import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


# =============================================================================
# 1. TECHNICAL INDICATORS STRATEGY
# =============================================================================

class TechnicalIndicatorsStrategy(Strategy):
    """
    Uses classic technical indicators: MA Crossover + RSI + MACD

    SIGNALS:
    - MA Crossover: Fast EMA crosses above/below Slow EMA
    - RSI Confirmation: RSI not overbought/oversold
    - MACD Confirmation: MACD line above/below signal line

    ENTRY: When all 3 indicators align
    """

    def __init__(self, name: str = "TechIndicators", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "fast_ema": 12,
            "slow_ema": 26,
            "rsi_period": 14,
            "rsi_upper": 70,
            "rsi_lower": 30,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Generate signal using technical indicators."""
        if not self.enabled:
            return None

        bars = state.bars_h1
        if len(bars) < max(self.config["slow_ema"], self.config["macd_slow"]) + 5:
            return None

        closes = np.array([bar["close"] for bar in bars])

        # 1. MA CROSSOVER
        fast_ema = self._ema(closes, self.config["fast_ema"])
        slow_ema = self._ema(closes, self.config["slow_ema"])

        # Check for crossover (current cross vs previous)
        current_cross = fast_ema[-1] > slow_ema[-1]
        previous_cross = fast_ema[-2] > slow_ema[-2]

        if current_cross == previous_cross:
            return None  # No crossover

        direction = "BUY" if current_cross else "SELL"

        # 2. RSI CONFIRMATION
        rsi = self._rsi(closes, self.config["rsi_period"])
        if direction == "BUY" and rsi > self.config["rsi_upper"]:
            return None  # Overbought
        if direction == "SELL" and rsi < self.config["rsi_lower"]:
            return None  # Oversold

        # 3. MACD CONFIRMATION
        macd_line, signal_line, _ = self._macd(closes,
                                                self.config["macd_fast"],
                                                self.config["macd_slow"],
                                                self.config["macd_signal"])

        macd_bullish = macd_line[-1] > signal_line[-1]
        if direction == "BUY" and not macd_bullish:
            return None
        if direction == "SELL" and macd_bullish:
            return None

        # ALL INDICATORS ALIGNED - Generate signal
        atr = self._atr(bars, self.config["atr_period"])

        if direction == "BUY":
            entry = state.ask
            sl = entry - (atr * self.config["atr_multiplier"])
            tp = entry + (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.BUY
        else:
            entry = state.bid
            sl = entry + (atr * self.config["atr_multiplier"])
            tp = entry - (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.SELL

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            volume=state.symbol_info.min_lot,
            reason=f"MA Cross + RSI={rsi:.1f} + MACD aligned",
            confidence=0.7,
            metadata={"rsi": rsi, "macd": macd_line[-1]}
        )

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA."""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema

    def _rsi(self, data: np.ndarray, period: int) -> float:
        """Calculate RSI."""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _macd(self, data: np.ndarray, fast: int, slow: int, signal: int):
        """Calculate MACD."""
        ema_fast = self._ema(data, fast)
        ema_slow = self._ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _atr(self, bars: List[Dict], period: int) -> float:
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
        return atr[-1]


# =============================================================================
# 2. PRICE ACTION PATTERNS STRATEGY
# =============================================================================

class PriceActionStrategy(Strategy):
    """
    Detects price action patterns: Support/Resistance + Candlestick patterns

    PATTERNS:
    - Support/Resistance levels (recent swing highs/lows)
    - Bullish patterns: Hammer, Bullish Engulfing
    - Bearish patterns: Shooting Star, Bearish Engulfing

    ENTRY: Price bounces off S/R with candlestick confirmation
    """

    def __init__(self, name: str = "PriceAction", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "lookback_bars": 20,  # Bars to find S/R levels
            "sr_tolerance": 0.0005,  # 0.05% tolerance for S/R
            "atr_period": 14,
            "atr_multiplier": 1.5,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Generate signal using price action patterns."""
        if not self.enabled:
            return None

        bars = state.bars_h1
        if len(bars) < self.config["lookback_bars"] + 3:
            return None

        # 1. FIND SUPPORT/RESISTANCE LEVELS
        support_levels = self._find_support_levels(bars)
        resistance_levels = self._find_resistance_levels(bars)

        current_bar = bars[-1]
        prev_bar = bars[-2]
        current_close = current_bar["close"]

        # 2. CHECK IF PRICE IS NEAR S/R
        near_support = self._is_near_level(current_close, support_levels,
                                           self.config["sr_tolerance"])
        near_resistance = self._is_near_level(current_close, resistance_levels,
                                              self.config["sr_tolerance"])

        if not near_support and not near_resistance:
            return None

        # 3. DETECT CANDLESTICK PATTERNS
        pattern = self._detect_candlestick_pattern(bars[-3:])

        if pattern is None:
            return None

        # 4. MATCH PATTERN WITH LEVEL
        if near_support and pattern == "BULLISH":
            direction = "BUY"
        elif near_resistance and pattern == "BEARISH":
            direction = "SELL"
        else:
            return None  # Pattern doesn't match level

        # 5. CALCULATE ENTRY, SL, TP
        atr = self._atr(bars, self.config["atr_period"])

        if direction == "BUY":
            entry = state.ask
            sl = min(support_levels) - (atr * 0.5)  # Below support
            tp = entry + (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.BUY
        else:
            entry = state.bid
            sl = max(resistance_levels) + (atr * 0.5)  # Above resistance
            tp = entry - (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.SELL

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            volume=state.symbol_info.min_lot,
            reason=f"{pattern} pattern at {'Support' if near_support else 'Resistance'}",
            confidence=0.75,
            metadata={"pattern": pattern, "level_type": "support" if near_support else "resistance"}
        )

    def _find_support_levels(self, bars: List[Dict]) -> List[float]:
        """Find recent support levels (swing lows)."""
        lookback = self.config["lookback_bars"]
        recent_bars = bars[-lookback:]
        lows = [bar["low"] for bar in recent_bars]

        # Find local minima
        support = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support.append(lows[i])

        return support if support else [min(lows)]

    def _find_resistance_levels(self, bars: List[Dict]) -> List[float]:
        """Find recent resistance levels (swing highs)."""
        lookback = self.config["lookback_bars"]
        recent_bars = bars[-lookback:]
        highs = [bar["high"] for bar in recent_bars]

        # Find local maxima
        resistance = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance.append(highs[i])

        return resistance if resistance else [max(highs)]

    def _is_near_level(self, price: float, levels: List[float], tolerance: float) -> bool:
        """Check if price is near any level."""
        for level in levels:
            if abs(price - level) / level < tolerance:
                return True
        return False

    def _detect_candlestick_pattern(self, bars: List[Dict]) -> Optional[str]:
        """
        Detect bullish/bearish candlestick patterns.

        Returns: "BULLISH", "BEARISH", or None
        """
        if len(bars) < 2:
            return None

        current = bars[-1]
        previous = bars[-2]

        c_open, c_high, c_low, c_close = current["open"], current["high"], current["low"], current["close"]
        p_open, p_high, p_low, p_close = previous["open"], previous["high"], previous["low"], previous["close"]

        c_body = abs(c_close - c_open)
        c_upper_wick = c_high - max(c_open, c_close)
        c_lower_wick = min(c_open, c_close) - c_low

        # BULLISH HAMMER: Small body at top, long lower wick
        if c_lower_wick > c_body * 2 and c_upper_wick < c_body * 0.5 and c_close > c_open:
            return "BULLISH"

        # BULLISH ENGULFING: Large bullish candle engulfs previous bearish
        if c_close > c_open and p_close < p_open:
            if c_open < p_close and c_close > p_open:
                return "BULLISH"

        # BEARISH SHOOTING STAR: Small body at bottom, long upper wick
        if c_upper_wick > c_body * 2 and c_lower_wick < c_body * 0.5 and c_close < c_open:
            return "BEARISH"

        # BEARISH ENGULFING: Large bearish candle engulfs previous bullish
        if c_close < c_open and p_close > p_open:
            if c_open > p_close and c_close < p_open:
                return "BEARISH"

        return None

    def _atr(self, bars: List[Dict], period: int) -> float:
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
        return atr[-1]


# =============================================================================
# 3. MULTI-TIMEFRAME CONFLUENCE STRATEGY
# =============================================================================

class MultiTimeframeStrategy(Strategy):
    """
    Analyzes multiple timeframes for confluence

    LOGIC:
    - H4: Determine overall trend (EMA50)
    - H1: Find pullback entry zones
    - M15: Precise entry timing (momentum shift)

    ENTRY: Only when all timeframes align
    """

    def __init__(self, name: str = "MultiTF", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "h4_ema": 50,
            "h1_ema": 20,
            "rsi_period": 14,
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Generate signal using multi-timeframe confluence."""
        if not self.enabled:
            return None

        # Need data from multiple timeframes
        if len(state.bars_h4) < self.config["h4_ema"]:
            return None
        if len(state.bars_h1) < self.config["h1_ema"]:
            return None

        # 1. H4 TREND
        h4_closes = np.array([bar["close"] for bar in state.bars_h4])
        h4_ema = self._ema(h4_closes, self.config["h4_ema"])
        h4_trend = "BULLISH" if h4_closes[-1] > h4_ema[-1] else "BEARISH"

        # 2. H1 PULLBACK
        h1_closes = np.array([bar["close"] for bar in state.bars_h1])
        h1_ema = self._ema(h1_closes, self.config["h1_ema"])

        # Check if price pulled back to H1 EMA
        distance_to_ema = abs(h1_closes[-1] - h1_ema[-1]) / h1_ema[-1]
        if distance_to_ema > 0.005:  # More than 0.5% away
            return None

        # Check if pullback is in direction of H4 trend
        h1_above_ema = h1_closes[-1] > h1_ema[-1]
        if h4_trend == "BULLISH" and not h1_above_ema:
            return None
        if h4_trend == "BEARISH" and h1_above_ema:
            return None

        # 3. M15 MOMENTUM (use H1 as proxy if M15 not available)
        rsi = self._rsi(h1_closes, self.config["rsi_period"])

        # For bullish, want RSI to be recovering (40-60 range)
        # For bearish, want RSI to be weakening (40-60 range)
        if not (40 < rsi < 60):
            return None

        # ALL TIMEFRAMES ALIGNED
        atr = self._atr(state.bars_h1, self.config["atr_period"])

        if h4_trend == "BULLISH":
            entry = state.ask
            sl = entry - (atr * self.config["atr_multiplier"])
            tp = entry + (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.BUY
        else:
            entry = state.bid
            sl = entry + (atr * self.config["atr_multiplier"])
            tp = entry - (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.SELL

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            volume=state.symbol_info.min_lot,
            reason=f"MTF Confluence: H4={h4_trend}, H1 pullback, RSI={rsi:.1f}",
            confidence=0.8,
            metadata={"h4_trend": h4_trend, "rsi": rsi}
        )

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA."""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema

    def _rsi(self, data: np.ndarray, period: int) -> float:
        """Calculate RSI."""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _atr(self, bars: List[Dict], period: int) -> float:
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
        return atr[-1]


# =============================================================================
# 4. VOLUME-BASED STRATEGY
# =============================================================================

class VolumeStrategy(Strategy):
    """
    Uses volume analysis for signals

    SIGNALS:
    - Volume Spike: Current volume >> average volume
    - Price Breakout: Price breaks recent high/low
    - Volume Confirmation: Volume confirms breakout direction

    ENTRY: Volume spike + price breakout
    """

    def __init__(self, name: str = "Volume", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "volume_period": 20,
            "volume_threshold": 2.0,  # 2x average volume
            "breakout_bars": 10,
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Generate signal using volume analysis."""
        if not self.enabled:
            return None

        bars = state.bars_h1
        if len(bars) < max(self.config["volume_period"], self.config["breakout_bars"]) + 5:
            return None

        # 1. VOLUME SPIKE DETECTION
        volumes = [bar["volume"] for bar in bars]
        avg_volume = np.mean(volumes[-self.config["volume_period"]:-1])
        current_volume = volumes[-1]

        if current_volume < (avg_volume * self.config["volume_threshold"]):
            return None  # No volume spike

        # 2. PRICE BREAKOUT DETECTION
        recent_bars = bars[-self.config["breakout_bars"]:-1]
        recent_high = max(bar["high"] for bar in recent_bars)
        recent_low = min(bar["low"] for bar in recent_bars)

        current_close = bars[-1]["close"]

        bullish_breakout = current_close > recent_high
        bearish_breakout = current_close < recent_low

        if not bullish_breakout and not bearish_breakout:
            return None  # No breakout

        # 3. VOLUME CONFIRMS BREAKOUT
        direction = "BUY" if bullish_breakout else "SELL"

        # Calculate entry, SL, TP
        atr = self._atr(bars, self.config["atr_period"])

        if direction == "BUY":
            entry = state.ask
            sl = recent_high - (atr * self.config["atr_multiplier"])
            tp = entry + (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.BUY
        else:
            entry = state.bid
            sl = recent_low + (atr * self.config["atr_multiplier"])
            tp = entry - (atr * self.config["atr_multiplier"] * 2)
            order_type = OrderType.SELL

        volume_ratio = current_volume / avg_volume

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            volume=state.symbol_info.min_lot,
            reason=f"Volume Breakout: {volume_ratio:.1f}x avg volume",
            confidence=0.7,
            metadata={"volume_ratio": volume_ratio, "breakout_type": direction}
        )

    def _atr(self, bars: List[Dict], period: int) -> float:
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
        return atr[-1]


# =============================================================================
# 5. STATISTICAL MEAN REVERSION STRATEGY
# =============================================================================

class MeanReversionStrategy(Strategy):
    """
    Statistical mean reversion using Bollinger Bands + Z-score

    LOGIC:
    - Calculate Bollinger Bands (20-period SMA ± 2 std dev)
    - Calculate Z-score (how many std devs from mean)
    - Enter when price is 2+ std devs away
    - Exit when price returns to mean

    ENTRY: Price touches outer band with high Z-score
    """

    def __init__(self, name: str = "MeanReversion", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "bb_period": 20,
            "bb_std": 2.0,
            "z_threshold": 2.0,
            "atr_period": 14,
            "atr_multiplier": 1.5,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Generate signal using mean reversion."""
        if not self.enabled:
            return None

        bars = state.bars_h1
        if len(bars) < self.config["bb_period"] + 10:
            return None

        closes = np.array([bar["close"] for bar in bars])

        # 1. CALCULATE BOLLINGER BANDS
        sma = np.mean(closes[-self.config["bb_period"]:])
        std = np.std(closes[-self.config["bb_period"]:])

        upper_band = sma + (self.config["bb_std"] * std)
        lower_band = sma - (self.config["bb_std"] * std)

        current_price = closes[-1]

        # 2. CALCULATE Z-SCORE
        z_score = (current_price - sma) / std

        # 3. CHECK FOR MEAN REVERSION OPPORTUNITY
        # Oversold: Price below lower band, high negative Z-score
        oversold = current_price < lower_band and z_score < -self.config["z_threshold"]

        # Overbought: Price above upper band, high positive Z-score
        overbought = current_price > upper_band and z_score > self.config["z_threshold"]

        if not oversold and not overbought:
            return None

        # 4. GENERATE SIGNAL (bet on reversion to mean)
        atr = self._atr(bars, self.config["atr_period"])

        if oversold:
            # Buy when oversold (expect reversion up)
            entry = state.ask
            sl = entry - (atr * self.config["atr_multiplier"])
            tp = sma  # Target: return to mean
            order_type = OrderType.BUY
            signal_type = "OVERSOLD"
        else:
            # Sell when overbought (expect reversion down)
            entry = state.bid
            sl = entry + (atr * self.config["atr_multiplier"])
            tp = sma  # Target: return to mean
            order_type = OrderType.SELL
            signal_type = "OVERBOUGHT"

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            volume=state.symbol_info.min_lot,
            reason=f"Mean Reversion {signal_type}: Z-score={z_score:.2f}",
            confidence=0.65,
            metadata={"z_score": z_score, "sma": sma, "signal_type": signal_type}
        )

    def _atr(self, bars: List[Dict], period: int) -> float:
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
        return atr[-1]


# =============================================================================
# 6. ENSEMBLE/HYBRID STRATEGY
# =============================================================================

class EnsembleStrategy(Strategy):
    """
    Combines multiple strategies using voting system

    LOGIC:
    - Run 5 different strategies in parallel
    - Each strategy "votes" BUY, SELL, or NEUTRAL
    - Enter trade only if majority agree (3+ votes)
    - Higher agreement = higher confidence

    This is the MOST POWERFUL approach: reduces false signals
    """

    def __init__(self, name: str = "Ensemble", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "min_votes": 3,  # Need 3+ strategies to agree
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

        # Initialize sub-strategies (without their own execution)
        self.strategies = [
            TechnicalIndicatorsStrategy(config={"enabled": True}),
            PriceActionStrategy(config={"enabled": True}),
            MultiTimeframeStrategy(config={"enabled": True}),
            VolumeStrategy(config={"enabled": True}),
            MeanReversionStrategy(config={"enabled": True}),
        ]

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Generate signal using ensemble voting."""
        if not self.enabled:
            return None

        # Collect votes from all strategies
        votes = {"BUY": 0, "SELL": 0, "NEUTRAL": 0}
        reasons = []

        for strategy in self.strategies:
            signal = strategy.analyze(state)

            if signal is None:
                votes["NEUTRAL"] += 1
            elif signal.direction == OrderType.BUY:
                votes["BUY"] += 1
                reasons.append(f"{strategy.name}:BUY")
            else:
                votes["SELL"] += 1
                reasons.append(f"{strategy.name}:SELL")

        # Check if we have majority consensus
        buy_votes = votes["BUY"]
        sell_votes = votes["SELL"]
        total_strategies = len(self.strategies)

        if buy_votes >= self.config["min_votes"]:
            direction = OrderType.BUY
            confidence = buy_votes / total_strategies
        elif sell_votes >= self.config["min_votes"]:
            direction = OrderType.SELL
            confidence = sell_votes / total_strategies
        else:
            return None  # No consensus

        # Calculate entry, SL, TP
        bars = state.bars_h1
        if len(bars) < self.config["atr_period"]:
            return None

        atr = self._atr(bars, self.config["atr_period"])

        if direction == OrderType.BUY:
            entry = state.ask
            sl = entry - (atr * self.config["atr_multiplier"])
            tp = entry + (atr * self.config["atr_multiplier"] * 2)
        else:
            entry = state.bid
            sl = entry + (atr * self.config["atr_multiplier"])
            tp = entry - (atr * self.config["atr_multiplier"] * 2)

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            volume=state.symbol_info.min_lot,
            reason=f"Ensemble: {', '.join(reasons)}",
            confidence=confidence,
            metadata={"votes": votes, "strategies_agreed": len(reasons)}
        )

    def _atr(self, bars: List[Dict], period: int) -> float:
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
        return atr[-1]
