"""Session open breakout strategy with H4 trend filter."""

import logging
from typing import Dict, List, Optional

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class BreakoutSessionOpenStrategy(Strategy):
    """
    Session open breakout strategy.

    Logic:
    1. Identify pre-session box (first 30 min of London/NY)
    2. Entry: Breakout + retest confirmation
    3. Filter: H4 EMA trend alignment
    4. Partial at 1R, trail by ATR
    5. One re-entry allowed if stopped and structure holds
    6. Min hold 61s enforced by system

    Best for: Major indices, FX during session opens
    """

    def __init__(self, name: str = "BreakoutSessionOpen", config: Optional[Dict] = None):
        """
        Initialize breakout session strategy.

        Config parameters:
        - session_box_minutes: Pre-session box duration (default 30)
        - ema_trend_period: EMA period for trend filter (default 50)
        - atr_period: ATR period (default 14)
        - atr_trail_mult: ATR trailing multiplier (default 2.0)
        - retest_tolerance_pct: Retest tolerance % (default 0.2)
        - max_spread_points: Max spread (default 14)
        - sessions: List of sessions to trade (default ["london", "ny"])
        - allowed_symbols: Symbols to trade
        """
        default_config = {
            "enabled": True,
            "session_box_minutes": 30,
            "ema_trend_period": 50,
            "atr_period": 14,
            "atr_trail_mult": 2.0,
            "retest_tolerance_pct": 0.2,
            "max_spread_points": 14,
            "sessions": ["london", "ny"],
            "allowed_symbols": ["EURUSD", "GBPUSD", "US30", "US500", "NAS100"],
            "sl_atr_mult": 1.5,
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Analyze market and generate breakout signal."""
        if not self.enabled:
            return None

        # Symbol filter
        if state.symbol.upper() not in self.config["allowed_symbols"]:
            return None

        # Session filter
        current_hour_utc = state.timestamp.hour
        session = self._get_current_session(current_hour_utc)

        if session not in self.config["sessions"]:
            return None

        # Spread filter
        spread = state.ask - state.bid
        spread_points = spread / state.symbol_info.pip_size
        if spread_points > self.config["max_spread_points"]:
            return None

        # Require sufficient data
        if len(state.bars_h4) < self.config["ema_trend_period"]:
            return None
        if len(state.bars_h1) < 10:
            return None

        # Get H4 trend direction
        trend = self._get_h4_trend(state.bars_h4)
        if trend is None:
            return None

        # Get session box (from current session open)
        box_high, box_low = self._calculate_session_box(state.bars_h1, session)

        if box_high is None or box_low is None:
            return None

        # Check for breakout + retest
        current_price = state.bars_h1[-1]["close"]
        prev_price = state.bars_h1[-2]["close"] if len(state.bars_h1) > 1 else current_price

        breakout_type = None

        # Bullish breakout (must align with H4 trend)
        if trend == "bullish" and prev_price <= box_high and current_price > box_high:
            # Check for retest
            if self._is_retest_confirmed(state.bars_h1, box_high, "bullish"):
                breakout_type = "long"
                entry_price = state.ask
                atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])
                stop_loss = box_high - (atr * self.config["sl_atr_mult"])
                risk_distance = entry_price - stop_loss
                take_profit = entry_price + risk_distance  # 1R target
                direction = OrderType.BUY

        # Bearish breakout
        elif trend == "bearish" and prev_price >= box_low and current_price < box_low:
            if self._is_retest_confirmed(state.bars_h1, box_low, "bearish"):
                breakout_type = "short"
                entry_price = state.bid
                atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])
                stop_loss = box_low + (atr * self.config["sl_atr_mult"])
                risk_distance = stop_loss - entry_price
                take_profit = entry_price - risk_distance
                direction = OrderType.SELL

        if breakout_type is None:
            return None

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
            reason=f"{breakout_type.upper()} {session} breakout: H4 trend={trend}, box={box_low:.5f}-{box_high:.5f}",
            confidence=0.72,
            metadata={
                "breakout_type": breakout_type,
                "session": session,
                "box_high": box_high,
                "box_low": box_low,
                "h4_trend": trend,
                "spread_points": spread_points,
            },
        )

    def _get_h4_trend(self, bars_h4: List[Dict]) -> Optional[str]:
        """Determine H4 trend using EMA."""
        if len(bars_h4) < self.config["ema_trend_period"]:
            return None

        closes = np.array([bar["close"] for bar in bars_h4])
        ema = self._calculate_ema(closes, self.config["ema_trend_period"])

        current_price = closes[-1]

        if current_price > ema[-1]:
            return "bullish"
        elif current_price < ema[-1]:
            return "bearish"

        return None

    def _calculate_session_box(
        self,
        bars_h1: List[Dict],
        session: str,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Calculate session box (high/low of first N minutes).

        Returns:
            (box_high, box_low)
        """
        # Find session start (simplified - would need actual session detection)
        session_start_hour = {"london": 8, "ny": 14}.get(session, 0)

        # Get bars from session start
        box_bars = []
        for bar in reversed(bars_h1):
            bar_hour = bar.get("time", 0) % 86400 // 3600  # Hour of day
            if bar_hour == session_start_hour:
                box_bars.insert(0, bar)
            if len(box_bars) >= 1:  # First 30-60 min (1-2 H1 bars)
                break

        if not box_bars:
            return None, None

        box_high = max(bar["high"] for bar in box_bars)
        box_low = min(bar["low"] for bar in box_bars)

        return box_high, box_low

    def _is_retest_confirmed(
        self,
        bars: List[Dict],
        level: float,
        direction: str,
    ) -> bool:
        """
        Check if retest is confirmed.

        Args:
            bars: Price bars
            level: Level to retest
            direction: "bullish" or "bearish"

        Returns:
            True if retest confirmed
        """
        if len(bars) < 3:
            return False

        tolerance_pct = self.config["retest_tolerance_pct"] / 100.0

        # For bullish: check if price came back near level after breakout
        if direction == "bullish":
            for bar in bars[-3:]:
                if abs(bar["low"] - level) / level < tolerance_pct:
                    return True

        # For bearish: check if price came back near level
        elif direction == "bearish":
            for bar in bars[-3:]:
                if abs(bar["high"] - level) / level < tolerance_pct:
                    return True

        return False

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate exponential moving average."""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]

        return ema

    def _calculate_atr(self, bars: List[Dict], period: int) -> float:
        """Calculate Average True Range."""
        if len(bars) < period + 1:
            return 0.0

        true_ranges = []

        for i in range(1, len(bars)):
            high = bars[i]["high"]
            low = bars[i]["low"]
            prev_close = bars[i - 1]["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            true_ranges.append(tr)

        return np.mean(true_ranges[-period:])

    def _get_current_session(self, hour_utc: int) -> Optional[str]:
        """Determine current trading session."""
        # London: 8-16 UTC
        if 8 <= hour_utc < 16:
            return "london"
        # NY: 14-22 UTC
        elif 14 <= hour_utc < 22:
            return "ny"
        # Asia: 0-8 UTC
        elif 0 <= hour_utc < 8:
            return "asia"

        return None
