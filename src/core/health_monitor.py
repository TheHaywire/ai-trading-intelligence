"""Live health monitoring with breach probability and alpha drift detection."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HealthAlert:
    """Health monitoring alert."""

    severity: str  # "info", "warning", "critical"
    alert_type: str
    message: str
    timestamp: datetime
    metadata: Dict


class LiveHealthMonitor:
    """
    Real-time health monitoring for trading system.

    Monitors:
    - Breach probability nowcast (DD risk in next N hours)
    - Alpha drift (30d vs 180d expectancy degradation)
    - Fill quality (slippage distribution)
    - Payout horizon (days to next payout, suggested de-risk)
    """

    def __init__(
        self,
        breach_prob_threshold: float = 0.15,
        alpha_drift_threshold_pct: float = 40.0,
        slippage_alert_threshold: float = 2.0,
    ):
        """
        Initialize health monitor.

        Args:
            breach_prob_threshold: Alert if breach probability > threshold
            alpha_drift_threshold_pct: Alert if 30d expectancy falls > X% vs 180d
            slippage_alert_threshold: Alert if avg slippage > X pips
        """
        self.breach_prob_threshold = breach_prob_threshold
        self.alpha_drift_threshold_pct = alpha_drift_threshold_pct
        self.slippage_alert_threshold = slippage_alert_threshold

        self.alerts: List[HealthAlert] = []
        self.slippage_history: List[float] = []
        self.expectancy_history: List[tuple[datetime, float]] = []

        logger.info("Health monitor initialized")

    def calculate_breach_probability(
        self,
        current_equity: float,
        dd_floor: float,
        recent_volatility: float,
        hours_ahead: int = 4,
    ) -> tuple[float, str]:
        """
        Calculate probability of breaching DD floor in next N hours.

        Uses Monte Carlo-style estimation based on recent volatility.

        Args:
            current_equity: Current account equity
            dd_floor: DD floor value
            recent_volatility: Recent realized volatility (daily)
            hours_ahead: Forecast horizon in hours

        Returns:
            (probability, severity)
        """
        if current_equity <= dd_floor:
            return 1.0, "critical"

        # Distance to floor as % of equity
        distance_pct = ((current_equity - dd_floor) / current_equity) * 100.0

        # Hourly volatility
        vol_hourly = recent_volatility / np.sqrt(24)

        # Standard deviations to floor
        sigma_to_floor = distance_pct / (vol_hourly * np.sqrt(hours_ahead))

        # Approximate probability using normal CDF
        # P(breach) ≈ Φ(-sigma_to_floor)
        from scipy.stats import norm

        breach_prob = norm.cdf(-sigma_to_floor)

        # Determine severity
        if breach_prob > 0.20:
            severity = "critical"
        elif breach_prob > 0.10:
            severity = "warning"
        else:
            severity = "info"

        return breach_prob, severity

    def check_breach_probability_alert(
        self,
        current_equity: float,
        dd_floor: float,
        recent_volatility: float,
        hours_ahead: int = 4,
    ) -> Optional[HealthAlert]:
        """
        Check for breach probability alert.

        Args:
            current_equity: Current equity
            dd_floor: DD floor
            recent_volatility: Recent vol
            hours_ahead: Forecast horizon

        Returns:
            HealthAlert if threshold exceeded
        """
        prob, severity = self.calculate_breach_probability(
            current_equity, dd_floor, recent_volatility, hours_ahead
        )

        if prob > self.breach_prob_threshold:
            alert = HealthAlert(
                severity=severity,
                alert_type="breach_probability",
                message=f"DD breach probability {prob*100:.1f}% in next {hours_ahead}h (threshold {self.breach_prob_threshold*100:.0f}%)",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "probability": prob,
                    "hours_ahead": hours_ahead,
                    "current_equity": current_equity,
                    "dd_floor": dd_floor,
                    "distance_pct": ((current_equity - dd_floor) / current_equity) * 100.0,
                },
            )

            self.alerts.append(alert)
            logger.warning(f"ALERT: {alert.message}")
            return alert

        return None

    def calculate_alpha_drift(
        self,
        window_short_days: int = 30,
        window_long_days: int = 180,
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate alpha drift (expectancy degradation).

        Args:
            window_short_days: Short window
            window_long_days: Long window

        Returns:
            (expectancy_30d, expectancy_180d, drift_pct)
        """
        if len(self.expectancy_history) < 10:
            return None, None, None

        now = datetime.now(timezone.utc)
        cutoff_short = now - timedelta(days=window_short_days)
        cutoff_long = now - timedelta(days=window_long_days)

        # Get expectancies for each window
        short_window = [e for t, e in self.expectancy_history if t > cutoff_short]
        long_window = [e for t, e in self.expectancy_history if t > cutoff_long]

        if not short_window or not long_window:
            return None, None, None

        exp_30d = np.mean(short_window)
        exp_180d = np.mean(long_window)

        # Calculate drift percentage
        if exp_180d != 0:
            drift_pct = ((exp_30d - exp_180d) / abs(exp_180d)) * 100.0
        else:
            drift_pct = 0.0

        return exp_30d, exp_180d, drift_pct

    def check_alpha_drift_alert(self) -> Optional[HealthAlert]:
        """
        Check for alpha drift alert.

        Returns:
            HealthAlert if drift exceeds threshold
        """
        exp_30d, exp_180d, drift_pct = self.calculate_alpha_drift()

        if exp_30d is None or exp_180d is None or drift_pct is None:
            return None

        # Alert if 30d expectancy falls > threshold% vs 180d
        if drift_pct < -self.alpha_drift_threshold_pct:
            alert = HealthAlert(
                severity="warning",
                alert_type="alpha_drift",
                message=f"Alpha drift detected: 30d expectancy {drift_pct:.1f}% vs 180d baseline (threshold -{self.alpha_drift_threshold_pct:.0f}%)",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "expectancy_30d": exp_30d,
                    "expectancy_180d": exp_180d,
                    "drift_pct": drift_pct,
                    "suggested_action": "Reduce risk_mult to 0.8",
                },
            )

            self.alerts.append(alert)
            logger.warning(f"ALERT: {alert.message}")
            return alert

        return None

    def record_slippage(self, intended_price: float, fill_price: float, pip_size: float) -> None:
        """
        Record order slippage.

        Args:
            intended_price: Intended execution price
            fill_price: Actual fill price
            pip_size: Pip size for symbol
        """
        slippage_pips = abs(fill_price - intended_price) / pip_size
        self.slippage_history.append(slippage_pips)

        # Keep only recent history
        if len(self.slippage_history) > 1000:
            self.slippage_history = self.slippage_history[-1000:]

    def get_fill_quality_report(self) -> Dict:
        """
        Get fill quality report based on slippage distribution.

        Returns:
            Fill quality metrics
        """
        if not self.slippage_history:
            return {
                "avg_slippage_pips": 0.0,
                "p50_slippage_pips": 0.0,
                "p95_slippage_pips": 0.0,
                "fills_count": 0,
            }

        slippage_arr = np.array(self.slippage_history)

        return {
            "avg_slippage_pips": float(np.mean(slippage_arr)),
            "p50_slippage_pips": float(np.percentile(slippage_arr, 50)),
            "p95_slippage_pips": float(np.percentile(slippage_arr, 95)),
            "fills_count": len(self.slippage_history),
        }

    def check_slippage_alert(self) -> Optional[HealthAlert]:
        """
        Check for excessive slippage alert.

        Returns:
            HealthAlert if slippage exceeds threshold
        """
        if len(self.slippage_history) < 10:
            return None

        avg_slippage = np.mean(self.slippage_history[-50:])  # Recent 50 fills

        if avg_slippage > self.slippage_alert_threshold:
            alert = HealthAlert(
                severity="warning",
                alert_type="slippage",
                message=f"Excessive slippage: {avg_slippage:.2f} pips (threshold {self.slippage_alert_threshold:.1f})",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "avg_slippage_pips": avg_slippage,
                    "threshold_pips": self.slippage_alert_threshold,
                    "suggested_action": "Widen slippage tolerance or use limit orders",
                },
            )

            self.alerts.append(alert)
            logger.warning(f"ALERT: {alert.message}")
            return alert

        return None

    def get_payout_horizon_card(
        self,
        next_payout_date: Optional[datetime],
        current_profit_pct: float,
        min_profit_pct: float,
    ) -> Dict:
        """
        Get payout horizon information card.

        Args:
            next_payout_date: Next eligible payout date
            current_profit_pct: Current profit percentage
            min_profit_pct: Minimum required profit percentage

        Returns:
            Payout horizon card
        """
        if next_payout_date is None:
            return {
                "eligible": False,
                "days_to_payout": None,
                "suggested_derisk_level": 0.0,
                "message": "No payout scheduled",
            }

        now = datetime.now(timezone.utc)
        days_to_payout = (next_payout_date - now).days

        # Suggest de-risk level based on proximity
        if days_to_payout <= 3:
            suggested_derisk = 0.7
        elif days_to_payout <= 7:
            suggested_derisk = 0.85
        else:
            suggested_derisk = 1.0

        # Check eligibility
        eligible = current_profit_pct >= min_profit_pct

        return {
            "eligible": eligible,
            "days_to_payout": days_to_payout,
            "next_payout_date": next_payout_date.isoformat(),
            "current_profit_pct": current_profit_pct,
            "min_required_pct": min_profit_pct,
            "suggested_derisk_level": suggested_derisk,
            "message": f"{'Eligible' if eligible else 'Not eligible'} for payout in {days_to_payout} days",
        }

    def record_trade_expectancy(self, expectancy: float, timestamp: Optional[datetime] = None) -> None:
        """
        Record trade expectancy for alpha drift tracking.

        Args:
            expectancy: Trade expectancy (expected value)
            timestamp: Timestamp (uses now if None)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        self.expectancy_history.append((timestamp, expectancy))

        # Keep only 1 year
        cutoff = timestamp - timedelta(days=365)
        self.expectancy_history = [(t, e) for t, e in self.expectancy_history if t > cutoff]

    def get_recent_alerts(self, hours: int = 24) -> List[HealthAlert]:
        """
        Get alerts from the last N hours.

        Args:
            hours: Lookback hours

        Returns:
            List of recent alerts
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [a for a in self.alerts if a.timestamp > cutoff]

    def get_summary(self) -> Dict:
        """Get health monitor summary."""
        fill_quality = self.get_fill_quality_report()
        exp_30d, exp_180d, drift_pct = self.calculate_alpha_drift()

        recent_alerts = self.get_recent_alerts(hours=24)
        alerts_by_severity = {
            "critical": len([a for a in recent_alerts if a.severity == "critical"]),
            "warning": len([a for a in recent_alerts if a.severity == "warning"]),
            "info": len([a for a in recent_alerts if a.severity == "info"]),
        }

        return {
            "total_alerts": len(self.alerts),
            "recent_alerts_24h": len(recent_alerts),
            "alerts_by_severity": alerts_by_severity,
            "fill_quality": fill_quality,
            "alpha_drift": {
                "expectancy_30d": exp_30d,
                "expectancy_180d": exp_180d,
                "drift_pct": drift_pct,
            } if exp_30d else None,
        }
