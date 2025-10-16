"""Gold-specific mean reversion strategy - FIXED VERSION."""

import logging
from typing import Dict, List, Optional

import numpy as np

from src.core.broker_mt5 import OrderType
from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


class GoldMeanReversionStrategy(Strategy):
    """
    Gold-specific mean reversion strategy with realistic parameters.
    """

    def __init__(self, name: str = "GoldMeanReversion", config: Optional[Dict] = None):
        default_config = {
            "enabled": True,
            "vwap_period": 20,
            "atr_period": 14,
            "band_multiplier": 2.5,  # Wider bands for gold
            "rsi_period": 14,  # Standard RSI, not 2
            "rsi_oversold": 30,  # Standard levels
            "rsi_overbought": 70,
            "max_spread_points": 50,  # Higher spread tolerance for gold
            "time_stop_hours": 4,
            "allowed_symbols": ["GOLD"],  # GOLD-specific
            "allowed_sessions": ["asia", "london", "ny"],  # Trade all sessions
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Optional[Signal]:
        """Analyze market and generate mean reversion signal."""
        if not self.enabled:
            return None

        # Symbol filter
        if state.symbol.upper() not in self.config["allowed_symbols"]:
            return None

        # ALL SESSIONS ALLOWED - remove session filter
        # Session filter removed for 24/7 trading

        # Spread filter (relaxed for gold)
        spread = state.ask - state.bid
        spread_points = spread / state.symbol_info.pip_size
        if spread_points > self.config["max_spread_points"]:
            logger.debug(f"Spread {spread_points:.1f} too wide, max {self.config['max_spread_points']}")
            return None

        # Require sufficient data
        if len(state.bars_h1) < max(self.config["vwap_period"], self.config["atr_period"]) + 10:
            return None

        # Calculate VWAP and bands
        vwap, upper_band, lower_band = self._calculate_vwap_bands(state.bars_h1)

        # Calculate RSI
        rsi = self._calculate_rsi(state.bars_h1, self.config["rsi_period"])

        # Current price
        current_price = state.bars_h1[-1]["close"]

        # Check for mean reversion setup
        signal_type = None

        # Long setup: Price below lower band + RSI oversold
        if current_price < lower_band and rsi < self.config["rsi_oversold"]:
            signal_type = "long"
            entry_price = state.ask
            stop_loss = lower_band - (upper_band - lower_band) * 0.5
            take_profit = vwap
            direction = OrderType.BUY

        # Short setup: Price above upper band + RSI overbought
        elif current_price > upper_band and rsi > self.config["rsi_overbought"]:
            signal_type = "short"
            entry_price = state.bid
            stop_loss = upper_band + (upper_band - lower_band) * 0.5
            take_profit = vwap
            direction = OrderType.SELL

        if signal_type is None:
            logger.debug(f"No signal: price ${current_price:.2f}, bands {lower_band:.2f}-{upper_band:.2f}, RSI {rsi:.1f}")
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
            reason=f"{signal_type.upper()} mean reversion: RSI={rsi:.1f}, price vs VWAP={((current_price-vwap)/vwap)*100:.2f}%",
            confidence=0.65,
            metadata={
                "signal_type": signal_type,
                "vwap": vwap,
                "upper_band": upper_band,
                "lower_band": lower_band,
                "rsi": rsi,
                "spread_points": spread_points,
                "time_stop_hours": self.config["time_stop_hours"],
            },
        )

    def _calculate_vwap_bands(self, bars: List[Dict]) -> tuple[float, float, float]:
        """Calculate VWAP with ATR bands."""
        period = self.config["vwap_period"]
        recent_bars = bars[-period:]

        typical_prices = [(b["high"] + b["low"] + b["close"]) / 3.0 for b in recent_bars]
        volumes = [b.get("volume", 1.0) for b in recent_bars]

        vwap = np.average(typical_prices, weights=volumes)

        atr = self._calculate_atr(bars, self.config["atr_period"])
        band_width = atr * self.config["band_multiplier"]

        upper_band = vwap + band_width
        lower_band = vwap - band_width

        return vwap, upper_band, lower_band

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
