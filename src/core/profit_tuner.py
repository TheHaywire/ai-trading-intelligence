"""Profit maximization with compliance-safe aggression."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RiskBand:
    """Risk multiplier band based on DD utilization."""

    cum_dd_util_lt: float
    daily_dd_util_lt: float
    mult: float


@dataclass
class PerformanceMetrics:
    """Rolling performance metrics for Kelly calculation."""

    wins: int
    losses: int
    avg_win: float
    avg_loss: float
    sharpe_30d: float
    sharpe_90d: float


class ProfitTuner:
    """
    Profit tuner with protected aggression and Kelly sizing.

    Maximizes expectancy while maintaining zero-breach behavior through:
    - Dynamic risk bands based on DD utilization
    - Payout-aware de-risking
    - Fractional Kelly sizing
    - Anti-overfit governor
    """

    def __init__(
        self,
        kelly_fraction_cap: float = 0.33,
        kelly_min_pct: float = 0.3,
        kelly_max_pct: float = 2.9,
        target_portfolio_vol_annual_pct: float = 18.0,
        payout_derisk_days: int = 3,
        payout_derisk_mult_cap: float = 0.7,
    ):
        """
        Initialize profit tuner.

        Args:
            kelly_fraction_cap: Kelly fraction to use (0.33 = 1/3 Kelly)
            kelly_min_pct: Minimum risk percentage
            kelly_max_pct: Maximum risk percentage (must stay under 3%)
            target_portfolio_vol_annual_pct: Target annual portfolio volatility
            payout_derisk_days: Days before payout to reduce risk
            payout_derisk_mult_cap: Max risk multiplier near payout
        """
        self.kelly_fraction_cap = kelly_fraction_cap
        self.kelly_min_pct = kelly_min_pct
        self.kelly_max_pct = kelly_max_pct
        self.target_portfolio_vol = target_portfolio_vol_annual_pct / 100.0
        self.payout_derisk_days = payout_derisk_days
        self.payout_derisk_mult_cap = payout_derisk_mult_cap

        # Risk bands (configurable)
        self.risk_bands = [
            RiskBand(cum_dd_util_lt=0.20, daily_dd_util_lt=0.20, mult=1.25),  # Protected aggression
            RiskBand(cum_dd_util_lt=0.50, daily_dd_util_lt=0.50, mult=1.00),  # Normal
            RiskBand(cum_dd_util_lt=0.80, daily_dd_util_lt=0.80, mult=0.60),  # Conservative
        ]

        # Performance tracking
        self.trade_history: List[Dict] = []

        logger.info(
            f"Profit tuner initialized: kelly_frac={kelly_fraction_cap}, "
            f"target_vol={target_portfolio_vol_annual_pct}%"
        )

    def get_risk_multiplier(
        self,
        cum_dd_utilization: float,
        daily_dd_utilization: float,
        days_to_payout: Optional[int] = None,
    ) -> Tuple[float, str]:
        """
        Calculate risk multiplier based on DD utilization and payout proximity.

        Args:
            cum_dd_utilization: Cumulative DD utilization (0-1)
            daily_dd_utilization: Daily DD utilization (0-1)
            days_to_payout: Days until next payout (None if no payout scheduled)

        Returns:
            (risk_multiplier, reason)
        """
        # Check for reduce-only (>= 80%)
        if cum_dd_utilization >= 0.80 or daily_dd_utilization >= 0.80:
            return 0.0, "Reduce-only mode (>= 80% DD utilization)"

        # Find applicable risk band
        risk_mult = 0.60  # Default conservative
        reason = "Default conservative"

        for band in self.risk_bands:
            if cum_dd_utilization < band.cum_dd_util_lt and daily_dd_utilization < band.daily_dd_util_lt:
                risk_mult = band.mult
                reason = f"Risk band: cum_dd<{band.cum_dd_util_lt*100:.0f}%, daily_dd<{band.daily_dd_util_lt*100:.0f}%"
                break

        # Payout-aware de-risking
        if days_to_payout is not None and days_to_payout <= self.payout_derisk_days:
            original_mult = risk_mult
            risk_mult = min(risk_mult, self.payout_derisk_mult_cap)
            if risk_mult < original_mult:
                reason += f" + payout de-risk ({days_to_payout}d to payout)"

        # Anti-overfit governor
        metrics = self.calculate_performance_metrics()
        if metrics and metrics.sharpe_30d > 3.5 and metrics.sharpe_90d < 1.0:
            risk_mult *= 0.75
            reason += " + anti-overfit governor (30d Sharpe >> 90d Sharpe)"

        return risk_mult, reason

    def calculate_kelly_risk_pct(
        self,
        lookback_window: int = 90,
    ) -> Tuple[float, Dict]:
        """
        Calculate fractional Kelly risk percentage.

        Formula: k = p - (1-p)/b
        Where p = win rate, b = payoff ratio

        Args:
            lookback_window: Days to look back for win/loss stats

        Returns:
            (kelly_risk_pct, metadata)
        """
        metrics = self.calculate_performance_metrics(lookback_window)

        if not metrics or (metrics.wins + metrics.losses) < 10:
            # Insufficient data, use default
            return self.kelly_min_pct, {"reason": "insufficient_data", "trades": 0}

        # Calculate win rate and payoff ratio
        total_trades = metrics.wins + metrics.losses
        win_rate = metrics.wins / total_trades if total_trades > 0 else 0.0

        payoff_ratio = abs(metrics.avg_win / metrics.avg_loss) if metrics.avg_loss != 0 else 1.0

        # Kelly formula
        if payoff_ratio > 0:
            kelly = win_rate - ((1 - win_rate) / payoff_ratio)
        else:
            kelly = 0.0

        # Apply fraction
        kelly_fractional = kelly * self.kelly_fraction_cap

        # Clip to min/max
        kelly_pct = np.clip(kelly_fractional * 100.0, self.kelly_min_pct, self.kelly_max_pct)

        metadata = {
            "kelly_raw": kelly * 100.0,
            "kelly_fractional": kelly_fractional * 100.0,
            "kelly_clipped": kelly_pct,
            "win_rate": win_rate * 100.0,
            "payoff_ratio": payoff_ratio,
            "trades": total_trades,
            "fraction_used": self.kelly_fraction_cap,
        }

        return kelly_pct, metadata

    def calculate_volatility_target_size(
        self,
        base_size: float,
        stop_distance_pct: float,
        current_portfolio_vol: float,
    ) -> float:
        """
        Adjust position size based on volatility targeting.

        Args:
            base_size: Base position size
            stop_distance_pct: Stop distance as % of entry
            current_portfolio_vol: Current portfolio volatility (annual)

        Returns:
            Adjusted position size
        """
        if current_portfolio_vol == 0:
            return base_size

        # Scale size to target portfolio volatility
        vol_ratio = self.target_portfolio_vol / current_portfolio_vol
        adjusted_size = base_size * vol_ratio

        # Don't increase more than 1.5x or decrease below 0.5x
        adjusted_size = np.clip(adjusted_size, base_size * 0.5, base_size * 1.5)

        return adjusted_size

    def record_trade_result(
        self,
        profit: float,
        entry_price: float,
        exit_price: float,
        volume: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record trade result for performance tracking.

        Args:
            profit: Trade profit/loss
            entry_price: Entry price
            exit_price: Exit price
            volume: Position size
            timestamp: Trade close time
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        trade = {
            "timestamp": timestamp,
            "profit": profit,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "volume": volume,
            "is_win": profit > 0,
        }

        self.trade_history.append(trade)

        # Keep only recent history (1 year)
        cutoff = timestamp - timedelta(days=365)
        self.trade_history = [t for t in self.trade_history if t["timestamp"] > cutoff]

    def calculate_performance_metrics(
        self,
        lookback_days: int = 90,
    ) -> Optional[PerformanceMetrics]:
        """
        Calculate performance metrics for Kelly sizing.

        Args:
            lookback_days: Days to look back

        Returns:
            PerformanceMetrics or None if insufficient data
        """
        if not self.trade_history:
            return None

        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        recent_trades = [t for t in self.trade_history if t["timestamp"] > cutoff]

        if len(recent_trades) < 10:
            return None

        wins = [t for t in recent_trades if t["is_win"]]
        losses = [t for t in recent_trades if not t["is_win"]]

        avg_win = np.mean([t["profit"] for t in wins]) if wins else 0.0
        avg_loss = abs(np.mean([t["profit"] for t in losses])) if losses else 0.0

        # Calculate Sharpe ratios
        sharpe_30d = self._calculate_sharpe(30)
        sharpe_90d = self._calculate_sharpe(90)

        return PerformanceMetrics(
            wins=len(wins),
            losses=len(losses),
            avg_win=avg_win,
            avg_loss=avg_loss,
            sharpe_30d=sharpe_30d,
            sharpe_90d=sharpe_90d,
        )

    def _calculate_sharpe(self, lookback_days: int) -> float:
        """Calculate Sharpe ratio for lookback period."""
        if not self.trade_history:
            return 0.0

        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        recent_trades = [t for t in self.trade_history if t["timestamp"] > cutoff]

        if len(recent_trades) < 10:
            return 0.0

        returns = [t["profit"] for t in recent_trades]
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe (assuming ~250 trading days/year)
        sharpe = (mean_return / std_return) * np.sqrt(250)
        return sharpe

    def should_allow_pyramiding(self, days_to_payout: Optional[int] = None) -> bool:
        """
        Check if pyramiding (adding to positions) is allowed.

        Args:
            days_to_payout: Days until next payout

        Returns:
            True if pyramiding allowed
        """
        if days_to_payout is not None and days_to_payout <= self.payout_derisk_days:
            return False
        return True

    def get_summary(self) -> Dict:
        """Get profit tuner summary."""
        metrics = self.calculate_performance_metrics()

        kelly_pct, kelly_meta = self.calculate_kelly_risk_pct()

        return {
            "kelly_risk_pct": kelly_pct,
            "kelly_metadata": kelly_meta,
            "target_portfolio_vol": self.target_portfolio_vol * 100.0,
            "trade_history_count": len(self.trade_history),
            "performance_metrics": {
                "wins": metrics.wins if metrics else 0,
                "losses": metrics.losses if metrics else 0,
                "avg_win": metrics.avg_win if metrics else 0.0,
                "avg_loss": metrics.avg_loss if metrics else 0.0,
                "sharpe_30d": metrics.sharpe_30d if metrics else 0.0,
                "sharpe_90d": metrics.sharpe_90d if metrics else 0.0,
            } if metrics else {},
        }
