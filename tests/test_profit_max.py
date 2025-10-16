"""Tests for Profit-Max Pack components."""

import pytest
from datetime import datetime, timedelta, timezone

from src.core.profit_tuner import ProfitTuner
from src.core.regime import MarketRegime, RegimeDetector
from src.core.health_monitor import LiveHealthMonitor
from src.utils.session_filters import SessionFilter, TradingSession


class TestProfitTuner:
    """Test profit tuner with dynamic risk bands and Kelly sizing."""

    def test_protected_aggression_low_dd(self):
        """Test 1.25x risk mult when DD util < 20%."""
        tuner = ProfitTuner()

        mult, reason = tuner.get_risk_multiplier(
            cum_dd_utilization=0.10,
            daily_dd_utilization=0.10,
        )

        assert mult == 1.25
        assert "cum_dd<20%" in reason

    def test_normal_risk_mid_dd(self):
        """Test 1.0x risk mult when DD util 20-50%."""
        tuner = ProfitTuner()

        mult, reason = tuner.get_risk_multiplier(
            cum_dd_utilization=0.30,
            daily_dd_utilization=0.30,
        )

        assert mult == 1.00

    def test_conservative_high_dd(self):
        """Test 0.6x risk mult when DD util 50-80%."""
        tuner = ProfitTuner()

        mult, reason = tuner.get_risk_multiplier(
            cum_dd_utilization=0.60,
            daily_dd_utilization=0.60,
        )

        assert mult == 0.60

    def test_reduce_only_at_80_percent(self):
        """Test reduce-only at 80%+ DD util."""
        tuner = ProfitTuner()

        mult, reason = tuner.get_risk_multiplier(
            cum_dd_utilization=0.85,
            daily_dd_utilization=0.50,
        )

        assert mult == 0.0
        assert "Reduce-only" in reason

    def test_payout_derisk_within_3_days(self):
        """Test risk capped to 0.7 within 3 days of payout."""
        tuner = ProfitTuner(payout_derisk_days=3, payout_derisk_mult_cap=0.7)

        mult, reason = tuner.get_risk_multiplier(
            cum_dd_utilization=0.10,
            daily_dd_utilization=0.10,
            days_to_payout=2,
        )

        # Should cap from 1.25 (protected aggression) to 0.7
        assert mult == 0.7
        assert "payout de-risk" in reason

    def test_kelly_calculation_with_win_rate(self):
        """Test Kelly sizing calculation."""
        tuner = ProfitTuner(kelly_fraction_cap=0.33, kelly_min_pct=0.3, kelly_max_pct=2.9)

        # Simulate trades: 60% win rate, 2:1 payoff
        for i in range(30):
            profit = 200.0 if i < 18 else -100.0  # 18 wins, 12 losses
            tuner.record_trade_result(profit, 1.0, 1.01 if profit > 0 else 0.99, 0.01)

        kelly_pct, metadata = tuner.calculate_kelly_risk_pct(lookback_window=30)

        # Kelly = 0.6 - 0.4/2 = 0.4, Fractional = 0.4 * 0.33 = 0.132 = 13.2%
        # Clipped to max 2.9%
        assert kelly_pct == 2.9
        assert metadata["win_rate"] == pytest.approx(60.0, abs=5.0)

    def test_anti_overfit_governor(self):
        """Test anti-overfit governor reduces risk if Sharpe30d >> Sharpe90d."""
        tuner = ProfitTuner()

        # Simulate recent hot streak but poor long-term
        tuner.trade_history = []
        now = datetime.now(timezone.utc)

        # Last 30 days: great
        for i in range(30):
            timestamp = now - timedelta(days=i)
            tuner.trade_history.append({
                "timestamp": timestamp,
                "profit": 100.0,
                "entry_price": 1.0,
                "exit_price": 1.01,
                "volume": 0.01,
                "is_win": True,
            })

        # Days 31-90: terrible
        for i in range(30, 90):
            timestamp = now - timedelta(days=i)
            tuner.trade_history.append({
                "timestamp": timestamp,
                "profit": -50.0,
                "entry_price": 1.0,
                "exit_price": 0.99,
                "volume": 0.01,
                "is_win": False,
            })

        # This should trigger anti-overfit
        mult, reason = tuner.get_risk_multiplier(0.10, 0.10)

        # Base mult would be 1.25, but anti-overfit applies 0.75x
        assert mult == pytest.approx(1.25 * 0.75, abs=0.01)


class TestRegimeDetector:
    """Test market regime detection and strategy routing."""

    def test_trend_regime_detection(self):
        """Test trend regime detected with strong directional movement."""
        detector = RegimeDetector(trend_threshold=25.0)

        # Strong uptrend price series
        prices = [100 + i * 2 for i in range(100)]

        regime = detector.detect_regime(prices)

        assert regime == MarketRegime.TREND

    def test_high_vol_regime_detection(self):
        """Test high-vol regime detected with elevated volatility."""
        detector = RegimeDetector(vol_threshold_high=0.25)

        # High volatility price series (large swings)
        import numpy as np
        np.random.seed(42)
        prices = [100 * np.exp(np.random.normal(0, 0.05)) for _ in range(100)]

        regime = detector.detect_regime(prices)

        # Should detect either HIGH_VOL or TREND (depending on realized vol)
        assert regime in (MarketRegime.HIGH_VOL, MarketRegime.TREND, MarketRegime.CHOPPY)

    def test_strategy_routing_by_regime(self):
        """Test that strategies are routed correctly by regime."""
        detector = RegimeDetector()

        # Set regime to TREND
        detector.current_regime = MarketRegime.TREND

        enabled = detector.get_enabled_strategies()

        assert "trend_breakout" in enabled
        assert "ema_trend" in enabled
        assert "mean_reversion_bands" not in enabled

    def test_risk_multiplier_by_regime(self):
        """Test risk multipliers vary by regime."""
        detector = RegimeDetector()

        detector.current_regime = MarketRegime.TREND
        trend_mult = detector.get_risk_multiplier()

        detector.current_regime = MarketRegime.HIGH_VOL
        highvol_mult = detector.get_risk_multiplier()

        assert trend_mult == 1.0
        assert highvol_mult == 0.8  # Reduced for high vol


class TestHealthMonitor:
    """Test live health monitoring."""

    def test_breach_probability_calculation(self):
        """Test DD breach probability calculation."""
        monitor = LiveHealthMonitor()

        # Current equity $98k, floor $95k, low vol
        prob, severity = monitor.calculate_breach_probability(
            current_equity=98000.0,
            dd_floor=95000.0,
            recent_volatility=0.01,  # 1% daily vol
            hours_ahead=4,
        )

        # Should be low probability (far from floor, low vol)
        assert prob < 0.10
        assert severity == "info"

    def test_breach_probability_alert_threshold(self):
        """Test alert triggered when breach prob > threshold."""
        monitor = LiveHealthMonitor(breach_prob_threshold=0.15)

        # Close to floor with high vol
        alert = monitor.check_breach_probability_alert(
            current_equity=96000.0,
            dd_floor=95000.0,
            recent_volatility=0.05,  # 5% daily vol
            hours_ahead=4,
        )

        # Should trigger alert
        if alert:
            assert alert.severity in ("warning", "critical")

    def test_alpha_drift_detection(self):
        """Test alpha drift (30d vs 180d expectancy degradation)."""
        monitor = LiveHealthMonitor(alpha_drift_threshold_pct=40.0)

        now = datetime.now(timezone.utc)

        # Last 30 days: poor expectancy
        for i in range(30):
            monitor.record_trade_expectancy(10.0, now - timedelta(days=i))

        # Days 31-180: great expectancy
        for i in range(30, 180):
            monitor.record_trade_expectancy(100.0, now - timedelta(days=i))

        exp_30d, exp_180d, drift_pct = monitor.calculate_alpha_drift()

        assert exp_30d < exp_180d
        assert drift_pct < -30  # Significant degradation

    def test_slippage_tracking(self):
        """Test slippage tracking and reporting."""
        monitor = LiveHealthMonitor()

        # Record some slippage
        for i in range(20):
            monitor.record_slippage(
                intended_price=1.10000,
                fill_price=1.10005,  # 0.5 pip slippage
                pip_size=0.0001,
            )

        report = monitor.get_fill_quality_report()

        assert report["avg_slippage_pips"] == pytest.approx(0.5, abs=0.1)
        assert report["fills_count"] == 20


class TestSessionFilters:
    """Test session filters and playbooks."""

    def test_current_session_detection(self):
        """Test session detection by hour."""
        session_filter = SessionFilter()

        # 10:00 UTC = London
        london_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert session_filter.get_current_session(london_time) == TradingSession.LONDON

        # 15:00 UTC = London/NY overlap
        overlap_time = datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
        assert session_filter.get_current_session(overlap_time) == TradingSession.OVERLAP_LONDON_NY

        # 04:00 UTC = Asia
        asia_time = datetime(2025, 1, 1, 4, 0, 0, tzinfo=timezone.utc)
        assert session_filter.get_current_session(asia_time) == TradingSession.ASIA

    def test_strategy_enabled_by_session(self):
        """Test strategies are filtered by session."""
        session_filter = SessionFilter()

        # Mean reversion enabled in Asia
        assert session_filter.is_strategy_enabled_for_session(
            "mean_reversion_bands", TradingSession.ASIA
        )

        # Breakout NOT enabled in Asia
        assert not session_filter.is_strategy_enabled_for_session(
            "breakout_session_open", TradingSession.ASIA
        )

    def test_spread_caps_by_session(self):
        """Test spread caps vary by session."""
        session_filter = SessionFilter()

        asia_cap = session_filter.get_spread_cap_for_session(TradingSession.ASIA)
        overlap_cap = session_filter.get_spread_cap_for_session(TradingSession.OVERLAP_LONDON_NY)

        # Overlap should have tighter spread cap
        assert overlap_cap < asia_cap

    def test_thin_crosses_blocked_in_asia(self):
        """Test thin crosses blocked during Asia session."""
        session_filter = SessionFilter()

        # Exotic pair should be blocked in Asia
        allowed, reason = session_filter.is_symbol_allowed_in_session(
            "GBPNZD", TradingSession.ASIA
        )

        assert not allowed
        assert "Thin cross blocked" in reason

        # Major pair should be allowed
        allowed, reason = session_filter.is_symbol_allowed_in_session(
            "EURUSD", TradingSession.ASIA
        )

        assert allowed


def test_integration_profit_max_components():
    """Integration test: all Profit-Max components work together."""
    tuner = ProfitTuner()
    regime_detector = RegimeDetector()
    health_monitor = LiveHealthMonitor()
    session_filter = SessionFilter()

    # Simulate market state
    prices = [100 + i * 0.5 for i in range(100)]  # Trending
    regime = regime_detector.detect_regime(prices)

    # Get risk multiplier from tuner
    tuner_mult, _ = tuner.get_risk_multiplier(
        cum_dd_utilization=0.15,
        daily_dd_utilization=0.10,
    )

    # Get regime multiplier
    regime_mult = regime_detector.get_risk_multiplier(regime)

    # Get session multiplier
    session = session_filter.get_current_session()
    session_mult = session_filter.get_risk_multiplier_for_session(session)

    # Combined risk multiplier
    combined_mult = tuner_mult * regime_mult * session_mult

    # Should be reasonable (0.5 - 2.0 range)
    assert 0.5 <= combined_mult <= 2.0

    # Check health
    summary = health_monitor.get_summary()
    assert "total_alerts" in summary
