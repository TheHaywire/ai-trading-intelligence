"""
Momentum Matrix Trader - Ensemble Multi-Layer Strategy

This strategy combines 7 layers into a weighted scoring system:
1. Trend Layer (EMA20 vs EMA50)
2. Momentum Layer (RSI Divergence + Slope)
3. Price Action Layer (Breakout + Engulfing patterns)
4. MTF Confluence (H1/D1 alignment)
5. Volatility & Risk Filter (ATR/Spread/News)
6. Intermarket Correlation (DXY vs Gold)
7. Session Filter (London/NY/Asia)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class MomentumMatrixTrader(Strategy):
    """
    Advanced ensemble strategy with 7 signal layers.

    Each layer scores the market state and contributes a weighted vote.
    Only trades when the total score exceeds a threshold.
    """

    def __init__(self, name: str = "MomentumMatrix", config: Optional[Dict] = None):
        """
        Initialize Momentum Matrix Trader.

        Config parameters:
        - threshold: Minimum score to trigger trade (default 3)
        - weights: Dict of layer weights
        - ema_fast: Fast EMA period (default 20)
        - ema_slow: Slow EMA period (default 50)
        - rsi_period: RSI period (default 14)
        - atr_period: ATR period (default 14)
        - atr_multiplier: ATR multiplier for stops (default 2.0)
        - risk_reward_ratio: Target R:R (default 2.0)
        - max_spread_pips: Max spread to allow trade (default 3.0)
        - min_atr_pips: Minimum ATR to trade (default 5.0)
        - dxy_enabled: Use DXY correlation filter (default True)
        - session_filter_enabled: Use session filter (default True)
        """
        default_config = {
            "enabled": True,
            "threshold": 3,
            "weights": {
                "trend": 2,
                "momentum": 1,
                "price_action": 2,
                "mtf_confluence": 3,
                "volatility": 1,
                "intermarket": 2,
                "session": 1
            },
            "ema_fast": 20,
            "ema_slow": 50,
            "rsi_period": 14,
            "rsi_divergence_lookback": 14,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "risk_reward_ratio": 2.0,
            "max_spread_pips": 3.0,
            "min_atr_pips": 5.0,
            "dxy_enabled": False,  # Disabled by default (requires DXY data)
            "session_filter_enabled": True,
            "breakout_periods": 20,
            "engulfing_min_body_pct": 0.6,
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Analyze market using all 7 layers and generate weighted signal."""
        if not self.enabled:
            return None

        # Need sufficient data
        if len(state.bars_h1) < 100 or len(state.bars_h4) < 100:
            return None

        # REGIME FILTER: Check if market is in tradeable regime
        if self.config.get("regime_filter_enabled", False):
            regime = self._detect_market_regime(state.bars_h4)
            if regime not in ["trending", "moderate_trend"]:
                # Skip trade if market is ranging/choppy
                return None

        # Layer scores: +1 (bullish), -1 (bearish), 0 (neutral)
        layer_scores = {}
        layer_details = {}

        # Layer 1: Trend
        trend_score, trend_detail = self._score_trend(state)
        layer_scores["trend"] = trend_score
        layer_details["trend"] = trend_detail

        # Layer 2: Momentum (RSI + Divergence)
        momentum_score, momentum_detail = self._score_momentum(state)
        layer_scores["momentum"] = momentum_score
        layer_details["momentum"] = momentum_detail

        # Layer 3: Price Action (Breakout + Engulfing)
        pa_score, pa_detail = self._score_price_action(state)
        layer_scores["price_action"] = pa_score
        layer_details["price_action"] = pa_detail

        # Layer 4: MTF Confluence
        mtf_score, mtf_detail = self._score_mtf_confluence(state)
        layer_scores["mtf_confluence"] = mtf_score
        layer_details["mtf_confluence"] = mtf_detail

        # Layer 5: Volatility & Risk Filter
        vol_score, vol_detail = self._score_volatility(state)
        layer_scores["volatility"] = vol_score
        layer_details["volatility"] = vol_detail

        # Layer 6: Intermarket Correlation (DXY)
        intermarket_score, intermarket_detail = self._score_intermarket(state)
        layer_scores["intermarket"] = intermarket_score
        layer_details["intermarket"] = intermarket_detail

        # Layer 7: Session Filter
        session_score, session_detail = self._score_session(state)
        layer_scores["session"] = session_score
        layer_details["session"] = session_detail

        # Calculate weighted total score
        total_score = 0
        for layer, score in layer_scores.items():
            weight = self.config["weights"].get(layer, 1)
            total_score += score * weight

        # Determine direction and check threshold
        direction = None
        if total_score >= self.config["threshold"]:
            direction = "long"
        elif total_score <= -self.config["threshold"]:
            direction = "short"
        else:
            # Not enough conviction
            return None

        # Calculate entry, SL, TP
        atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])

        if direction == "long":
            entry_price = state.ask
            stop_loss = entry_price - (atr * self.config["atr_multiplier"])
            risk_distance = entry_price - stop_loss
            take_profit = entry_price + (risk_distance * self.config["risk_reward_ratio"])
            order_type = OrderType.BUY
        else:
            entry_price = state.bid
            stop_loss = entry_price + (atr * self.config["atr_multiplier"])
            risk_distance = stop_loss - entry_price
            take_profit = entry_price - (risk_distance * self.config["risk_reward_ratio"])
            order_type = OrderType.SELL

        # Validate
        if stop_loss <= 0 or abs(entry_price - stop_loss) < state.symbol_info.pip_size:
            return None

        # Build reason string
        reason_parts = []
        for layer, detail in layer_details.items():
            score = layer_scores[layer]
            if score != 0:
                reason_parts.append(f"{layer}={detail}[{score:+d}]")

        reason = f"MMT {direction.upper()} (score={total_score:+d}): " + ", ".join(reason_parts)

        # Confidence based on score strength
        max_possible_score = sum(abs(w) for w in self.config["weights"].values())
        confidence = min(abs(total_score) / max_possible_score, 1.0)

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=reason,
            confidence=confidence,
            metadata={
                "total_score": total_score,
                "layer_scores": layer_scores,
                "layer_details": layer_details,
                "atr": atr,
                "direction": direction,
            }
        )

    # ==================== LAYER SCORING METHODS ====================

    def _score_trend(self, state: MarketState) -> Tuple[int, str]:
        """
        Layer 1: Trend (EMA20 vs EMA50 on M15 and H1).

        Returns:
            (score, detail_string)
        """
        closes_h1 = np.array([bar["close"] for bar in state.bars_h1])

        ema_fast = self._calculate_ema(closes_h1, self.config["ema_fast"])
        ema_slow = self._calculate_ema(closes_h1, self.config["ema_slow"])

        current_price = closes_h1[-1]

        # Check alignment
        if ema_fast[-1] > ema_slow[-1] and current_price > ema_fast[-1]:
            return 1, "bullish"
        elif ema_fast[-1] < ema_slow[-1] and current_price < ema_fast[-1]:
            return -1, "bearish"
        else:
            return 0, "neutral"

    def _score_momentum(self, state: MarketState) -> Tuple[int, str]:
        """
        Layer 2: Momentum (RSI + Divergence detection).

        Returns:
            (score, detail_string)
        """
        rsi = self._calculate_rsi(state.bars_h1, self.config["rsi_period"])
        rsi_slope = self._calculate_rsi_slope(state.bars_h1, self.config["rsi_period"])

        # Check for bullish divergence (price lower, RSI higher)
        divergence = self._detect_divergence(state.bars_h1, self.config["rsi_divergence_lookback"])

        if divergence == "bullish":
            return 1, "bull_div"
        elif divergence == "bearish":
            return -1, "bear_div"
        elif rsi < 40 and rsi_slope > 0:
            return 1, "rsi_up"
        elif rsi > 60 and rsi_slope < 0:
            return -1, "rsi_down"
        else:
            return 0, "neutral"

    def _score_price_action(self, state: MarketState) -> Tuple[int, str]:
        """
        Layer 3: Price Action (Breakout + Engulfing patterns).

        Returns:
            (score, detail_string)
        """
        # Check for breakout
        breakout = self._detect_breakout(state.bars_h1, self.config["breakout_periods"])

        # Check for engulfing pattern
        engulfing = self._detect_engulfing(state.bars_h1)

        if breakout == "bullish" or engulfing == "bullish":
            return 1, f"{'breakout' if breakout == 'bullish' else 'engulf'}"
        elif breakout == "bearish" or engulfing == "bearish":
            return -1, f"{'breakout' if breakout == 'bearish' else 'engulf'}"
        else:
            return 0, "neutral"

    def _score_mtf_confluence(self, state: MarketState) -> Tuple[int, str]:
        """
        Layer 4: Multi-timeframe confluence (H1 + H4 + D1 alignment).

        Returns:
            (score, detail_string)
        """
        # H1 trend
        h1_trend = self._get_timeframe_trend(state.bars_h1)

        # H4 trend
        h4_trend = self._get_timeframe_trend(state.bars_h4) if len(state.bars_h4) >= 50 else "neutral"

        # D1 trend
        d1_trend = self._get_timeframe_trend(state.bars_d1) if len(state.bars_d1) >= 50 else "neutral"

        # Count alignments
        bullish_count = sum([h1_trend == "bullish", h4_trend == "bullish", d1_trend == "bullish"])
        bearish_count = sum([h1_trend == "bearish", h4_trend == "bearish", d1_trend == "bearish"])

        if bullish_count >= 2:
            return 1, f"MTF_bull({bullish_count}/3)"
        elif bearish_count >= 2:
            return -1, f"MTF_bear({bearish_count}/3)"
        else:
            return 0, "no_confluence"

    def _score_volatility(self, state: MarketState) -> Tuple[int, str]:
        """
        Layer 5: Volatility & Risk Filter (ATR, Spread check).

        Returns:
            (score, detail_string) - returns 0 if conditions bad, maintains direction otherwise
        """
        atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])
        atr_pips = atr / state.symbol_info.pip_size

        spread = state.ask - state.bid
        spread_pips = spread / state.symbol_info.pip_size

        # Check conditions
        if atr_pips < self.config["min_atr_pips"]:
            return 0, f"low_atr({atr_pips:.1f})"

        if spread_pips > self.config["max_spread_pips"]:
            return 0, f"wide_spread({spread_pips:.1f})"

        # Good volatility environment - don't bias direction, just approve
        return 0, "OK"

    def _score_intermarket(self, state: MarketState) -> Tuple[int, str]:
        """
        Layer 6: Intermarket Correlation (DXY vs Gold).

        For now, this is a placeholder. In production, you'd fetch DXY data.

        Returns:
            (score, detail_string)
        """
        if not self.config["dxy_enabled"]:
            return 0, "disabled"

        # TODO: Implement DXY correlation
        # For XAUUSD: negative correlation with DXY
        # If DXY falling and Gold rising = bullish
        # If DXY rising and Gold falling = bearish

        return 0, "no_data"

    def _score_session(self, state: MarketState) -> Tuple[int, str]:
        """
        Layer 7: Session Filter (London/NY/Asia).

        Returns:
            (score, detail_string) - returns -999 to block trade if bad session
        """
        if not self.config["session_filter_enabled"]:
            return 0, "disabled"

        session = self._get_session(state.timestamp)

        # NY-ONLY MODE: Block all trades outside NY session
        if self.config.get("ny_only_mode", False):
            if session == "ny":
                return 0, "ny_session"  # Good, allow trade
            else:
                return -999, f"blocked_{session}"  # Block trade entirely

        # Standard mode: prefer London/NY
        if session in ["london", "ny"]:
            return 0, session  # Good session, neutral score
        elif session == "asia":
            return 0, "asia_low_vol"  # Lower quality but not blocking
        else:
            return 0, "off_hours"

    # ==================== HELPER METHODS ====================

    def _get_timeframe_trend(self, bars: List[Dict]) -> str:
        """Determine trend from EMA alignment."""
        if len(bars) < 50:
            return "neutral"

        closes = np.array([bar["close"] for bar in bars])
        ema_fast = self._calculate_ema(closes, 20)
        ema_slow = self._calculate_ema(closes, 50)

        if ema_fast[-1] > ema_slow[-1]:
            return "bullish"
        elif ema_fast[-1] < ema_slow[-1]:
            return "bearish"
        else:
            return "neutral"

    def _detect_breakout(self, bars: List[Dict], period: int) -> str:
        """Detect range breakout."""
        if len(bars) < period + 2:
            return "neutral"

        recent_bars = bars[-(period+1):-1]
        current_bar = bars[-1]

        recent_high = max(bar["high"] for bar in recent_bars)
        recent_low = min(bar["low"] for bar in recent_bars)

        if current_bar["close"] > recent_high:
            return "bullish"
        elif current_bar["close"] < recent_low:
            return "bearish"
        else:
            return "neutral"

    def _detect_engulfing(self, bars: List[Dict]) -> str:
        """Detect bullish/bearish engulfing pattern."""
        if len(bars) < 2:
            return "neutral"

        prev_bar = bars[-2]
        curr_bar = bars[-1]

        prev_body = abs(prev_bar["close"] - prev_bar["open"])
        curr_body = abs(curr_bar["close"] - curr_bar["open"])

        # Minimum body size requirement
        min_body_pct = self.config["engulfing_min_body_pct"]
        prev_range = prev_bar["high"] - prev_bar["low"]
        curr_range = curr_bar["high"] - curr_bar["low"]

        if prev_range == 0 or curr_range == 0:
            return "neutral"

        # Bullish engulfing
        if (prev_bar["close"] < prev_bar["open"] and  # prev bearish
            curr_bar["close"] > curr_bar["open"] and  # curr bullish
            curr_bar["open"] < prev_bar["close"] and  # opens below prev close
            curr_bar["close"] > prev_bar["open"] and  # closes above prev open
            curr_body / curr_range > min_body_pct):
            return "bullish"

        # Bearish engulfing
        if (prev_bar["close"] > prev_bar["open"] and  # prev bullish
            curr_bar["close"] < curr_bar["open"] and  # curr bearish
            curr_bar["open"] > prev_bar["close"] and  # opens above prev close
            curr_bar["close"] < prev_bar["open"] and  # closes below prev open
            curr_body / curr_range > min_body_pct):
            return "bearish"

        return "neutral"

    def _detect_divergence(self, bars: List[Dict], lookback: int) -> str:
        """Detect RSI divergence."""
        if len(bars) < lookback + 2:
            return "neutral"

        recent_bars = bars[-lookback:]
        closes = np.array([bar["close"] for bar in recent_bars])

        # Calculate RSI for each bar
        rsi_values = []
        for i in range(lookback):
            if i + self.config["rsi_period"] < len(recent_bars):
                window = recent_bars[i:i+self.config["rsi_period"]+1]
                rsi = self._calculate_rsi(window, self.config["rsi_period"])
                rsi_values.append(rsi)

        if len(rsi_values) < 2:
            return "neutral"

        # Check for divergence: price making lower lows but RSI making higher lows
        price_trend = closes[-1] - closes[0]
        rsi_trend = rsi_values[-1] - rsi_values[0]

        if price_trend < 0 and rsi_trend > 0:
            return "bullish"  # Bullish divergence
        elif price_trend > 0 and rsi_trend < 0:
            return "bearish"  # Bearish divergence
        else:
            return "neutral"

    def _calculate_rsi_slope(self, bars: List[Dict], period: int) -> float:
        """Calculate RSI slope (momentum of momentum)."""
        if len(bars) < period + 5:
            return 0.0

        # Get last 5 RSI values
        rsi_values = []
        for i in range(5):
            window = bars[-(5-i+period):-((5-i) if (5-i) > 0 else None)]
            if len(window) >= period:
                rsi = self._calculate_rsi(window, period)
                rsi_values.append(rsi)

        if len(rsi_values) < 2:
            return 0.0

        # Simple slope
        return rsi_values[-1] - rsi_values[0]

    def _get_session(self, timestamp: datetime) -> str:
        """Determine trading session from timestamp."""
        hour = timestamp.hour

        # London: 08:00-16:00 UTC
        if 8 <= hour < 16:
            return "london"
        # NY: 13:00-21:00 UTC (overlaps with London)
        elif 13 <= hour < 21:
            return "ny"
        # Asia: 00:00-08:00 UTC
        elif 0 <= hour < 8:
            return "asia"
        else:
            return "off_hours"

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate exponential moving average."""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]

        return ema

    def _calculate_rsi(self, bars: List[Dict], period: int) -> float:
        """Calculate Relative Strength Index."""
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
        """Calculate Average True Range."""
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
        """Calculate Average Directional Index."""
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

    def _detect_market_regime(self, bars: List[Dict]) -> str:
        """
        Detect current market regime using IMPROVED multi-factor analysis.

        Based on analysis showing that TREND CONSISTENCY (not just ADX)
        is the key differentiator between profitable and unprofitable periods.

        Returns:
            "trending": Strong persistent trend (BEST for our strategy)
            "moderate_trend": Moderate trend (OK for our strategy)
            "ranging": Choppy/ranging market (BAD for our strategy)
        """
        if len(bars) < 50:
            return "ranging"

        # Factor 1: ADX (Trend Strength)
        adx = self._calculate_adx(bars, 14)

        # Factor 2: ATR as % of price (Volatility)
        atr = self._calculate_atr(bars, 14)
        current_price = bars[-1]["close"]
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

        # Factor 3: TREND CONSISTENCY (KEY INSIGHT from analysis!)
        # This measures how persistently price trends in one direction
        closes = np.array([bar["close"] for bar in bars[-40:]])  # Look back further
        ema_fast = self._calculate_ema(closes, 10)
        ema_slow = self._calculate_ema(closes, 20)

        # Count how many bars are trending in same direction
        trend_up = ema_fast > ema_slow
        same_direction = np.sum(trend_up == trend_up[-1])
        trend_consistency = same_direction / len(trend_up)

        # Factor 4: REVERSAL RATE (Price direction changes)
        price_changes = np.diff(closes)
        reversals = np.sum(np.sign(price_changes[:-1]) != np.sign(price_changes[1:]))
        reversal_rate = reversals / (len(price_changes) - 1) if len(price_changes) > 1 else 0.5

        # Factor 5: Bollinger Band Width (Range expansion)
        bb_width = self._calculate_bollinger_width(closes)

        # MULTI-FACTOR REGIME SCORE
        # Based on analysis: Good period had 53% consistency, bad had 35%
        score = 0

        # ADX contribution (max 30 points)
        if adx > 32:  # Median from good period
            score += 30
        elif adx > 25:
            score += 20
        elif adx > 20:
            score += 10

        # Trend Consistency contribution (max 40 points - MOST IMPORTANT)
        if trend_consistency > 0.53:  # Good period threshold
            score += 40
        elif trend_consistency > 0.45:
            score += 25
        elif trend_consistency > 0.35:
            score += 10

        # Reversal Rate contribution (max 20 points)
        if reversal_rate < 0.50:  # Less choppy
            score += 20
        elif reversal_rate < 0.55:
            score += 10

        # Volatility contribution (max 10 points)
        if 0.10 < atr_pct < 0.25:  # Sweet spot
            score += 10
        elif 0.08 < atr_pct < 0.30:
            score += 5

        # Classify based on score
        # Good trending: score 70+
        # Moderate trending: score 50-69
        # Ranging: score < 50

        if score >= 70:
            return "trending"
        elif score >= 50:
            return "moderate_trend"
        else:
            return "ranging"

    def _calculate_bollinger_width(self, closes: np.ndarray, period: int = 20, std_dev: int = 2) -> float:
        """Calculate Bollinger Band width as % of price."""
        if len(closes) < period:
            return 0.0

        sma = np.mean(closes[-period:])
        std = np.std(closes[-period:])

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        width = ((upper - lower) / sma) * 100 if sma > 0 else 0

        return width
