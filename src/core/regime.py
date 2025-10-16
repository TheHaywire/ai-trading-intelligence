"""Market regime detection and strategy routing."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime types."""

    TREND = "Trend"
    CHOPPY = "Choppy"
    HIGH_VOL = "HighVol"
    LOW_VOL = "LowVol"


@dataclass
class RegimeConfig:
    """Configuration for a market regime."""

    enable: List[str]  # Strategy names to enable
    risk_mult: float  # Risk multiplier for this regime
    widen_stops: float = 1.0  # Stop loss multiplier
    max_positions: Optional[int] = None  # Max concurrent positions


class RegimeDetector:
    """
    Detects market regime and routes strategies accordingly.

    Features:
    - Realized volatility
    - Trend strength (ADX, EMA slope)
    - Breadth proxy (cross-symbol correlation)
    - Macro calendar density

    Regimes:
    - Trend: Strong directional movement → breakout, EMA-trend
    - Choppy/Low-Vol: Range-bound → mean reversion
    - High-Vol: Elevated volatility → reduce risk, widen stops
    """

    def __init__(
        self,
        features_window_days: int = 90,
        vol_threshold_low: float = 0.10,
        vol_threshold_high: float = 0.25,
        trend_threshold: float = 25.0,
        regime_configs: Optional[Dict[str, RegimeConfig]] = None,
    ):
        """
        Initialize regime detector.

        Args:
            features_window_days: Lookback window for feature calculation
            vol_threshold_low: Annual vol threshold for low-vol regime
            vol_threshold_high: Annual vol threshold for high-vol regime
            trend_threshold: ADX threshold for trend regime
            regime_configs: Configuration for each regime
        """
        self.features_window_days = features_window_days
        self.vol_threshold_low = vol_threshold_low
        self.vol_threshold_high = vol_threshold_high
        self.trend_threshold = trend_threshold

        # Default regime configurations
        self.regime_configs = regime_configs or {
            MarketRegime.TREND: RegimeConfig(
                enable=["trend_breakout", "ema_trend"],
                risk_mult=1.0,
            ),
            MarketRegime.CHOPPY: RegimeConfig(
                enable=["mean_reversion_bands"],
                risk_mult=0.9,
            ),
            MarketRegime.HIGH_VOL: RegimeConfig(
                enable=["trend_breakout"],
                risk_mult=0.8,
                widen_stops=1.2,
            ),
            MarketRegime.LOW_VOL: RegimeConfig(
                enable=["mean_reversion_bands"],
                risk_mult=0.95,
            ),
        }

        self.current_regime = MarketRegime.CHOPPY
        self.regime_confidence = 0.5

        logger.info(f"Regime detector initialized: window={features_window_days}d")

    def detect_regime(
        self,
        price_history: List[float],
        news_density: Optional[float] = None,
    ) -> MarketRegime:
        """
        Detect current market regime.

        Args:
            price_history: Recent price history
            news_density: Optional news event density (events per week)

        Returns:
            Detected regime
        """
        if len(price_history) < 20:
            return MarketRegime.CHOPPY

        # Calculate features
        realized_vol = self._calculate_realized_volatility(price_history)
        trend_strength = self._calculate_trend_strength(price_history)

        # Regime detection logic
        regime = MarketRegime.CHOPPY
        confidence = 0.5

        # High volatility regime
        if realized_vol > self.vol_threshold_high:
            regime = MarketRegime.HIGH_VOL
            confidence = min(1.0, realized_vol / self.vol_threshold_high)

            # If also trending, prefer trend strategies with wider stops
            if trend_strength > self.trend_threshold:
                regime = MarketRegime.TREND
                # Modify config to widen stops
                self.regime_configs[MarketRegime.TREND].widen_stops = 1.3

        # Low volatility regime
        elif realized_vol < self.vol_threshold_low:
            regime = MarketRegime.LOW_VOL
            confidence = min(1.0, self.vol_threshold_low / realized_vol)

        # Trend regime
        elif trend_strength > self.trend_threshold:
            regime = MarketRegime.TREND
            confidence = min(1.0, trend_strength / self.trend_threshold)

        # Choppy/range-bound (default)
        else:
            regime = MarketRegime.CHOPPY
            confidence = 0.6

        # Adjust for high news density
        if news_density and news_density > 5:  # > 5 events per week
            # Reduce risk in high news environments
            for regime_config in self.regime_configs.values():
                regime_config.risk_mult *= 0.9

        self.current_regime = regime
        self.regime_confidence = confidence

        logger.info(
            f"Regime detected: {regime.value} (confidence={confidence:.2f}, "
            f"vol={realized_vol:.3f}, trend={trend_strength:.1f})"
        )

        return regime

    def get_enabled_strategies(self, regime: Optional[MarketRegime] = None) -> List[str]:
        """
        Get enabled strategies for a regime.

        Args:
            regime: Market regime (uses current if None)

        Returns:
            List of enabled strategy names
        """
        regime = regime or self.current_regime
        config = self.regime_configs.get(regime)

        if config:
            return config.enable
        return []

    def get_risk_multiplier(self, regime: Optional[MarketRegime] = None) -> float:
        """
        Get risk multiplier for a regime.

        Args:
            regime: Market regime (uses current if None)

        Returns:
            Risk multiplier
        """
        regime = regime or self.current_regime
        config = self.regime_configs.get(regime)

        if config:
            return config.risk_mult
        return 1.0

    def get_stop_multiplier(self, regime: Optional[MarketRegime] = None) -> float:
        """
        Get stop loss multiplier for a regime.

        Args:
            regime: Market regime (uses current if None)

        Returns:
            Stop multiplier
        """
        regime = regime or self.current_regime
        config = self.regime_configs.get(regime)

        if config:
            return config.widen_stops
        return 1.0

    def should_enable_strategy(self, strategy_name: str) -> bool:
        """
        Check if a strategy should be enabled in current regime.

        Args:
            strategy_name: Strategy name

        Returns:
            True if strategy should be enabled
        """
        enabled_strategies = self.get_enabled_strategies()
        return strategy_name in enabled_strategies

    def _calculate_realized_volatility(self, prices: List[float]) -> float:
        """
        Calculate annualized realized volatility.

        Args:
            prices: Price history

        Returns:
            Annualized volatility
        """
        if len(prices) < 2:
            return 0.0

        returns = np.diff(np.log(prices))
        vol_daily = np.std(returns)

        # Annualize (assume 252 trading days)
        vol_annual = vol_daily * np.sqrt(252)

        return vol_annual

    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """
        Calculate trend strength using ADX-like metric.

        Args:
            prices: Price history

        Returns:
            Trend strength (0-100)
        """
        if len(prices) < 14:
            return 0.0

        # Simple trend strength: EMA slope normalized
        prices_arr = np.array(prices)

        # Calculate EMA50
        ema_period = min(50, len(prices_arr))
        ema = self._calculate_ema(prices_arr, ema_period)

        # Calculate slope of EMA
        if len(ema) < 10:
            return 0.0

        recent_ema = ema[-10:]
        slope = (recent_ema[-1] - recent_ema[0]) / len(recent_ema)

        # Normalize slope by average price
        avg_price = np.mean(prices_arr[-20:])
        normalized_slope = (slope / avg_price) * 100.0

        # Convert to strength (0-100)
        strength = min(100.0, abs(normalized_slope) * 1000.0)

        return strength

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate exponential moving average."""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]

        return ema

    def get_summary(self) -> Dict:
        """Get regime detector summary."""
        return {
            "current_regime": self.current_regime.value,
            "confidence": self.regime_confidence,
            "enabled_strategies": self.get_enabled_strategies(),
            "risk_multiplier": self.get_risk_multiplier(),
            "stop_multiplier": self.get_stop_multiplier(),
            "vol_threshold_low": self.vol_threshold_low,
            "vol_threshold_high": self.vol_threshold_high,
            "trend_threshold": self.trend_threshold,
        }
