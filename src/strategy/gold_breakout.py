"""Gold-specific breakout strategy - FIXED VERSION."""

import logging
from typing import Dict, List, Optional

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class GoldBreakoutStrategy(Strategy):
    """
    Gold-specific breakout strategy with realistic session detection.
    """

    def __init__(self, name: str = "GoldBreakout", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "session_box_minutes": 60,  # 1 hour session detection
            "ema_trend_period": 50,
            "atr_period": 14,
            "atr_trail_mult": 2.0,
            "retest_tolerance_pct": 0.2,
            "max_spread_points": 50,  # Higher tolerance for gold
            "sessions": ["asia", "london", "ny"],  # Trade all sessions
            "allowed_symbols": ["GOLD"],
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

        # Simplified session check - allow all sessions for now
        current_hour_utc = state.timestamp.hour
        session = self._get_current_session(current_hour_utc)

        if session not in self.config["sessions"]:
            session = "any"  # Default

        # Spread filter
        spread = state.ask - state.bid
        spread_points = spread / state.symbol_info.pip_size
        if spread_points > self.config["max_spread_points"]:
            logger.debug(f"Spread {spread_points:.1f} too wide")
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

        # Simplified breakout detection (no session box)
        signal_type = None
        current_price = state.bars_h1[-1]["close"]
        prev_price = state.bars_h1[-2]["close"] if len(state.bars_h1) > 1 else current_price

        # Look for momentum breakouts
        price_change = (current_price - prev_price) / prev_price * 100

        # Bullish breakout (must align with H4 trend)
        if trend == "bullish" and price_change > 0.3:  # 0.3% movement
            # Calculate ATR-based levels
            atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])
            recent_low = min([b["low"] for b in state.bars_h1[-10:]])
            
            signal_type = "long"
            entry_price = state.ask
            stop_loss = recent_low - atr  # Below recent low
            risk_distance = entry_price - stop_loss
            take_profit = entry_price + risk_distance
            direction = OrderType.BUY

        # Bearish breakout
        elif trend == "bearish" and price_change < -0.3:
            atr = self._calculate_atr(state.bars_h1, self.config["atr_period"])
            recent_high = max([b["high"] for b in state.bars_h1[-10:]])
            
            signal_type = "short"
            entry_price = state.bid
            stop_loss = recent_high + atr
            risk_distance = stop_loss - entry_price
            take_profit = entry_price - risk_distance
            direction = OrderType.SELL

        if signal_type is None:
            logger.debug(f"No signal: trend {trend}, price_change {price_change:.2f}%")
            return None

        # Validate SL
        if stop_loss <= 0 or abs(entry_price - stop_loss) < state.symbol_info.pip_size:
            logger.debug(f"Invalid SL: {entry_price:.2f} -> {stop_loss:.2f}")
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"{signal_type.upper()} breakout: H4 trend={trend}, change={price_change:.2f}%",
            confidence=0.72,
            metadata={
                "signal_type": signal_type,
                "session": session,
                "h4_trend": trend,
                "price_change_pct": price_change,
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
        for i in range(1, min(len(bars), period + 10)):
            high = bars[i]["high"]
            low = bars[i]["low"]
            prev_close = bars[i - 1]["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            true_ranges.append(tr)

        return np.mean(true_ranges[-period:]) if len(true_ranges) >= period else np.mean(true_ranges)

    def _get_current_session(self, hour_utc: int) -> str:
        """Determine current trading session."""
        if 0 <= hour_utc < 8:
            return "asia"
        elif 8 <= hour_utc < 16:
            return "london"
        elif 14 <= hour_utc < 22:
            return "ny"
        else:
            return "after_hours"
