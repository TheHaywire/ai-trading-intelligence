"""Configuration models for the trading system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ProgramType(str, Enum):
    """Supported prop firm program types."""

    ONE_PHASE = "one_phase"
    ONE_PHASE_MICRO = "one_phase_micro"
    TWO_PHASE = "two_phase"
    TWO_PHASE_MAX = "two_phase_max"
    INSTANT_FUNDING = "instant_funding"
    INSTANT_FUNDING_MICRO = "instant_funding_micro"


class DrawdownModel(str, Enum):
    """Drawdown tracking models."""

    SMART = "smart"
    STATIC = "static"


class LeverageConfig(BaseModel):
    """Leverage limits by asset class."""

    fx: int = 100
    indices: int = 20
    commodities: int = 20
    crypto: int = 2


class SmartDDConfig(BaseModel):
    """Smart drawdown configuration (IF accounts)."""

    initial_pct: float = Field(0.10, description="Initial DD floor (10%)")
    lock_after_gain_pct: float = Field(0.05, description="Lock DD after +5% equity gain")
    locked_pct: float = Field(0.05, description="Locked DD floor (5%)")


class StaticDDConfig(BaseModel):
    """Static drawdown configuration (challenges)."""

    max_loss_pct: float = Field(0.06, description="Max loss % from starting balance (6-10%)")


class DrawdownConfig(BaseModel):
    """Drawdown configuration."""

    model: DrawdownModel = DrawdownModel.SMART
    smart: SmartDDConfig = Field(default_factory=SmartDDConfig)
    static: StaticDDConfig = Field(default_factory=StaticDDConfig)


class DailyDrawdownConfig(BaseModel):
    """Daily drawdown limits."""

    pct: float = Field(0.0, description="Daily DD %; 0 = dormant for IF accounts")
    compute_on: Literal["equity", "balance"] = "equity"
    halt_buffer_pct: float = Field(0.80, description="Halt at 80% utilization")


class RiskConfig(BaseModel):
    """Risk management parameters."""

    max_risk_per_idea_pct: float = Field(2.9, description="Max risk per idea (%)")
    max_positions_per_symbol: int = 3
    min_hold_seconds: int = 61
    max_trades_per_hour: int = 25
    forbid_grid: bool = True
    forbid_public_ea: bool = True
    allow_martingale_challenge: bool = True
    allow_martingale_if_account: Literal["limited", "forbidden"] = "limited"


class NewsConfig(BaseModel):
    """News blackout configuration."""

    enforce_window: bool = True
    window_seconds: int = 240
    source_list: list[str] = Field(default_factory=lambda: ["fxfactory", "fxstreet"])
    apply_only_to_impacted_symbols: bool = True
    add_on_enabled: bool = False
    weekend_holding_enabled: bool = False


class LotCapsConfig(BaseModel):
    """Lot caps configuration."""

    config_file: str = "configs/lot_caps.yaml"


class PayoutsConfig(BaseModel):
    """Payout scheduling configuration."""

    mode: Literal["scheduled", "on_demand"] = "scheduled"
    first_wait_days: int = 14
    subsequent_wait_days: int = 7
    min_amount_usd: float = 25.0
    min_profit_pct_of_start: float = 1.5
    best_day_cap_pct: float = 40.0


class SmartScalingConfig(BaseModel):
    """Smart DD scaling configuration."""

    trigger_gain_pct: float = 10.0
    new_locked_pct: float = 5.0


class StaticScalingConfig(BaseModel):
    """Static DD scaling configuration."""

    gain_pct: float = 10.0
    interval_days: int = 90
    scale_increment_pct: float = 25.0


class ScalingConfig(BaseModel):
    """Scaling configuration."""

    smart_dd: SmartScalingConfig = Field(default_factory=SmartScalingConfig)
    static_dd: StaticScalingConfig = Field(default_factory=StaticScalingConfig)


class AccountCapsConfig(BaseModel):
    """Global account caps."""

    max_starting_balances_total: float = 640000.0
    max_challenge_total: float = 400000.0
    max_instant_total: float = 240000.0
    max_instant_micro_total: float = 200000.0


class PlatformConfig(BaseModel):
    """MT5 platform configuration."""

    broker: Literal["MT5"] = "MT5"
    server: str
    login: str
    password: str
    symbol_map_file: str = "src/core/symbols.py"


class OpsConfig(BaseModel):
    """Operational settings."""

    timezone_display: str = "Asia/Kolkata"
    logs_dir: str = "runs/logs"
    reports_dir: str = "runs/reports"
    screenshot_dashboard: bool = True
    news_calendar_path: str = "configs/news_events_seed.json"


class StrategyConfig(BaseModel):
    """Base strategy configuration."""

    enabled: bool = True

    class Config:
        extra = "allow"


class StrategiesConfig(BaseModel):
    """All strategy configurations."""

    trend_breakout: StrategyConfig = Field(default_factory=StrategyConfig)
    ema_trend: StrategyConfig = Field(default_factory=StrategyConfig)
    mean_reversion_bands: StrategyConfig = Field(default_factory=StrategyConfig)
    breakout_session_open: StrategyConfig = Field(default_factory=StrategyConfig)

    class Config:
        extra = "allow"


class HealthMonitorConfig(BaseModel):
    """Health monitor configuration."""

    enabled: bool = True
    breach_prob_threshold: float = 0.15
    alpha_drift_threshold_pct: float = 40.0
    slippage_alert_threshold: float = 2.0
    expectancy_tracking: bool = True


class RegimeConfig(BaseModel):
    """Regime detection configuration."""

    enabled: bool = True
    features_window_days: int = 90
    vol_threshold_low: float = 0.10
    vol_threshold_high: float = 0.25
    trend_threshold: float = 25.0

    class Config:
        extra = "allow"


class PortfolioConfig(BaseModel):
    """Portfolio allocation configuration."""

    hrp_enabled: bool = True
    max_corr_abs: float = 0.8
    per_currency_risk_cap_pct: float = 6.0
    lookback_days: int = 90
    fallback_days: int = 30


class AccountConfig(BaseModel):
    """Account-level configuration."""

    program: ProgramType
    starting_balance: float
    currency: str = "USD"
    leverage: LeverageConfig = Field(default_factory=LeverageConfig)
    inactivity_days_close: int = 60


class TradingConfig(BaseModel):
    """Main trading system configuration."""

    account: AccountConfig
    drawdown: DrawdownConfig = Field(default_factory=DrawdownConfig)
    daily_drawdown: DailyDrawdownConfig = Field(default_factory=DailyDrawdownConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)
    lot_caps: LotCapsConfig = Field(default_factory=LotCapsConfig)
    payouts: PayoutsConfig = Field(default_factory=PayoutsConfig)
    scaling: ScalingConfig = Field(default_factory=ScalingConfig)
    account_caps: AccountCapsConfig = Field(default_factory=AccountCapsConfig)
    platform: PlatformConfig
    ops: OpsConfig = Field(default_factory=OpsConfig)
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)
    health_monitor: HealthMonitorConfig = Field(default_factory=HealthMonitorConfig)
    regime: RegimeConfig = Field(default_factory=RegimeConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)

    class Config:
        extra = "allow"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TradingConfig":
        """Load configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)


class LotCapsTable(BaseModel):
    """Lot caps by program and starting balance."""

    caps: Dict[str, Dict[int, Dict[str, float]]]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "LotCapsTable":
        """Load lot caps table from YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(caps=data)

    def get_caps(self, program: str, starting_balance: float) -> Optional[Dict[str, float]]:
        """Get lot caps for a program and starting balance."""
        if program not in self.caps:
            return None
        # Find the matching or closest lower starting balance
        program_caps = self.caps[program]
        valid_balances = sorted([bal for bal in program_caps.keys() if bal <= starting_balance])
        if not valid_balances:
            return None
        return program_caps[valid_balances[-1]]
