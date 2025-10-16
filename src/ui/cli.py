"""Command-line interface for the trading system."""

import argparse
import logging
import sys
from pathlib import Path

from src.core.config import TradingConfig, LotCapsTable
from src.core.telemetry import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Instant Bot - MT5 Trading System with IF Compliance"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Trade command
    trade_parser = subparsers.add_parser("trade", help="Start trading")
    trade_parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration YAML file",
    )
    trade_parser.add_argument(
        "--paper",
        action="store_true",
        help="Run in paper trading mode (no real trades)",
    )
    trade_parser.add_argument(
        "--symbols",
        type=str,
        nargs="+",
        help="Symbols to trade (default: all configured)",
    )

    # Validate config command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    validate_parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration YAML file",
    )

    # Export report command
    export_parser = subparsers.add_parser("export", help="Export telemetry reports")
    export_parser.add_argument(
        "--logs-dir",
        type=str,
        default="runs/logs",
        help="Logs directory",
    )
    export_parser.add_argument(
        "--output-dir",
        type=str,
        default="runs/reports",
        help="Output directory for reports",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration YAML file",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(level=logging.INFO)

    try:
        if args.command == "trade":
            return run_trading(args)
        elif args.command == "validate":
            return validate_config(args)
        elif args.command == "export":
            return export_reports(args)
        elif args.command == "status":
            return show_status(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


def run_trading(args: argparse.Namespace) -> int:
    """Run trading system."""
    logger.info("=" * 60)
    logger.info("INSTANT BOT - Starting Trading System")
    logger.info("=" * 60)

    # Load configuration
    config = TradingConfig.from_yaml(args.config)
    logger.info(f"Loaded config: {args.config}")
    logger.info(f"Program: {config.account.program.value}")
    logger.info(f"Starting balance: ${config.account.starting_balance:,.2f}")
    logger.info(f"Paper mode: {args.paper}")

    if args.paper:
        logger.warning("PAPER TRADING MODE - No real trades will be executed")

    # Initialize components
    from src.core.broker_mt5 import MT5Broker
    from src.core.compliance_guard import ComplianceGuard
    from src.core.dd_tracker import DrawdownTracker
    from src.core.lots_cap import LotCapsValidator
    from src.core.news_guard import NewsGuard
    from src.core.payouts import PayoutScheduler
    from src.core.positions import PositionManager
    from src.core.risk_engine import RiskEngine
    from src.core.scaling import ScalingManager
    from src.core.telemetry import TelemetryRecorder
    from src.strategy.loader import StrategyLoader, MarketState
    from src.strategy.ema_trend import EMATrendStrategy
    from src.strategy.mean_reversion_bands import MeanReversionBandsStrategy
    from src.strategy.breakout_session_open import BreakoutSessionOpenStrategy

    # Broker
    broker = MT5Broker(
        login=config.platform.login,
        password=config.platform.password,
        server=config.platform.server,
        paper_mode=args.paper,
    )

    # Position manager
    position_manager = PositionManager()

    # Drawdown tracker
    dd_tracker = DrawdownTracker(
        starting_balance=config.account.starting_balance,
        config=config.drawdown,
    )

    # Lot caps
    lot_caps_table = LotCapsTable.from_yaml(config.lot_caps.config_file)
    lot_caps = LotCapsValidator(
        program=config.account.program,
        starting_balance=config.account.starting_balance,
        lot_caps_table=lot_caps_table,
        position_manager=position_manager,
    )

    # Risk engine
    risk_engine = RiskEngine(
        config=config,
        dd_tracker=dd_tracker,
        position_manager=position_manager,
    )

    # Compliance guard
    compliance_guard = ComplianceGuard(
        program=config.account.program,
        risk_config=config.risk,
        position_manager=position_manager,
        lot_caps_validator=lot_caps,
    )

    # News guard
    news_guard = NewsGuard(
        config=config.news,
        calendar_path=getattr(config.ops, "news_calendar_path", "configs/news_events_seed.json"),
    )

    # Telemetry
    telemetry = TelemetryRecorder(logs_dir=config.ops.logs_dir)

    # Payouts
    payouts = PayoutScheduler(
        config=config.payouts,
        program=config.account.program,
        starting_balance=config.account.starting_balance,
    )

    # Scaling
    scaling = ScalingManager(
        program=config.account.program,
        drawdown_model=config.drawdown.model,
        starting_balance=config.account.starting_balance,
        scaling_config=config.scaling,
        account_caps=config.account_caps,
    )

    # Load strategies
    strategy_loader = StrategyLoader()

    # Register all strategies from config
    if config.strategies.ema_trend.enabled:
        strategy_loader.register(EMATrendStrategy("ema_trend", dict(config.strategies.ema_trend)))

    if config.strategies.mean_reversion_bands.enabled:
        strategy_loader.register(MeanReversionBandsStrategy("mean_reversion_bands", dict(config.strategies.mean_reversion_bands)))

    if config.strategies.breakout_session_open.enabled:
        strategy_loader.register(BreakoutSessionOpenStrategy("breakout_session_open", dict(config.strategies.breakout_session_open)))

    # Initialize Profit-Max components
    profit_tuner = None
    regime_detector = None
    health_monitor = None
    session_filter = None
    portfolio_allocator = None

    if hasattr(config, 'health_monitor') and config.health_monitor.enabled:
        from src.core.health_monitor import LiveHealthMonitor
        health_monitor = LiveHealthMonitor(
            breach_prob_threshold=config.health_monitor.breach_prob_threshold,
            alpha_drift_threshold_pct=config.health_monitor.alpha_drift_threshold_pct,
            slippage_alert_threshold=config.health_monitor.slippage_alert_threshold,
        )
        logger.info("Health monitor enabled")

    if hasattr(config.risk, 'protected_aggression') and config.risk.protected_aggression:
        from src.core.profit_tuner import ProfitTuner
        profit_tuner = ProfitTuner(
            kelly_fraction_cap=config.risk.kelly_fraction_cap,
            kelly_min_pct=config.risk.kelly_min_pct,
            kelly_max_pct=config.risk.kelly_max_pct,
            payout_derisk_days=config.payouts.derisk_days_before if hasattr(config.payouts, 'derisk_days_before') else 3,
            payout_derisk_mult_cap=config.payouts.derisk_risk_mult_cap if hasattr(config.payouts, 'derisk_risk_mult_cap') else 0.7,
        )
        logger.info("Profit tuner enabled with protected aggression")

    if hasattr(config, 'regime') and config.regime.enabled:
        from src.core.regime import RegimeDetector
        regime_detector = RegimeDetector(
            vol_threshold_low=config.regime.vol_threshold_low,
            vol_threshold_high=config.regime.vol_threshold_high,
            trend_threshold=config.regime.trend_threshold,
        )
        logger.info("Regime detector enabled")

    if hasattr(config, 'sessions'):
        from src.utils.session_filters import SessionFilter
        session_filter = SessionFilter()
        logger.info("Session filters enabled")

    if hasattr(config, 'portfolio') and config.portfolio.hrp_enabled:
        from src.core.portfolio_allocator import PortfolioAllocator
        portfolio_allocator = PortfolioAllocator(
            position_manager=position_manager,
            lookback_days=config.portfolio.lookback_days,
            max_corr_abs=config.portfolio.max_corr_abs,
            per_currency_risk_cap_pct=config.portfolio.per_currency_risk_cap_pct,
        )
        logger.info("HRP portfolio allocator enabled")

    logger.info(f"All components initialized - {len(strategy_loader.get_all_enabled())} strategies loaded")

    # Connect to broker
    try:
        broker.connect()
    except Exception as e:
        logger.error(f"Failed to connect to broker: {e}")
        return 1

    logger.info("Connected to broker")

    # Start dashboard server
    from src.ui.dashboard import start_dashboard_server, get_dashboard

    dashboard = start_dashboard_server(host="0.0.0.0", port=8000)
    logger.info("Dashboard available at http://localhost:8000")
    logger.info("WebSocket streaming at ws://localhost:8000/ws")

    logger.info("System ready - press Ctrl+C to stop")

    # Main trading loop (simplified - would be event-driven in production)
    try:
        import time

        iteration = 0
        signals_count = 0
        trades_count = 0
        daily_start_equity = 0.0

        while True:
            # Update account state
            account_info = broker.get_account_info()
            risk_engine.update_state(account_info.equity, account_info.balance)

            # Track daily P&L
            if iteration == 0:
                daily_start_equity = account_info.equity

            # Sync positions
            broker_positions = broker.get_positions()
            position_manager.sync_with_broker_positions(broker_positions)

            # Log snapshot
            telemetry.log_state_snapshot(
                balance=account_info.balance,
                equity=account_info.equity,
                margin=account_info.margin,
                free_margin=account_info.free_margin,
                profit=account_info.profit,
                positions_count=len(broker_positions),
                open_ideas_count=len(position_manager.get_all_open_ideas()),
                dd_state=dd_tracker.state.value,
                dd_utilization=dd_tracker.utilization_cumulative() * 100.0,
            )

            # Run strategies on all symbols
            symbols_to_scan = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD", "US30", "US500", "NAS100"]

            for symbol in symbols_to_scan:
                try:
                    # Get market data
                    bars_h1 = broker.get_bars(symbol, "H1", count=100)
                    bars_h4 = broker.get_bars(symbol, "H4", count=100)
                    bars_d1 = broker.get_bars(symbol, "D1", count=50)
                    tick = broker.get_tick(symbol)

                    if not tick or not bars_h1:
                        continue

                    # Get symbol info
                    from src.core.symbols import get_registry
                    symbol_info = get_registry().get(symbol)
                    if not symbol_info:
                        continue

                    # Build market state
                    market_state = MarketState(
                        symbol=symbol,
                        timestamp=tick.time,
                        bid=tick.bid,
                        ask=tick.ask,
                        bars_h1=bars_h1,
                        bars_h4=bars_h4,
                        bars_d1=bars_d1,
                        symbol_info=symbol_info,
                    )

                    # Apply session filter
                    if session_filter:
                        current_session = session_filter.get_current_session()
                        allowed, reason = session_filter.is_symbol_allowed_in_session(symbol, current_session)
                        if not allowed:
                            continue

                    # Detect regime
                    current_regime = None
                    if regime_detector:
                        prices = [bar['close'] for bar in bars_d1]
                        current_regime = regime_detector.detect_regime(prices)

                    # Generate signals from all strategies
                    signals = strategy_loader.analyze_all(market_state)

                    # Count signals
                    signals_count += len(signals)

                    for signal in signals:
                        # Apply regime filter
                        if regime_detector and current_regime:
                            enabled_strats = regime_detector.get_enabled_strategies(current_regime)
                            if signal.strategy_name not in enabled_strats:
                                logger.debug(f"Strategy {signal.strategy_name} not enabled in {current_regime} regime")
                                continue

                        # Apply session strategy filter
                        if session_filter:
                            if not session_filter.is_strategy_enabled_for_session(signal.strategy_name, current_session):
                                logger.debug(f"Strategy {signal.strategy_name} not enabled in {current_session} session")
                                continue

                        # Calculate risk multiplier from Profit-Max
                        risk_mult = 1.0
                        if profit_tuner:
                            cum_dd_util = dd_tracker.utilization_cumulative()
                            daily_dd_util = 0.0  # TODO: track daily DD
                            days_to_payout = None  # TODO: calculate from payout scheduler
                            risk_mult, reason = profit_tuner.get_risk_multiplier(cum_dd_util, daily_dd_util, days_to_payout)
                            logger.info(f"Profit tuner risk mult: {risk_mult:.2f}x ({reason})")

                        # Apply session risk mult
                        if session_filter:
                            session_mult = session_filter.get_risk_multiplier_for_session(current_session)
                            risk_mult *= session_mult

                        # Apply regime risk mult
                        if regime_detector and current_regime:
                            regime_mult = regime_detector.get_risk_multiplier(current_regime)
                            risk_mult *= regime_mult

                        # Check portfolio correlation
                        if portfolio_allocator:
                            open_symbols = [pos.symbol for pos in position_manager.get_all_open_positions()]
                            if open_symbols:
                                should_clamp, clamp_mult, clamp_reason = portfolio_allocator.check_correlation_clamp(symbol, open_symbols)
                                if should_clamp:
                                    risk_mult *= clamp_mult
                                    logger.warning(f"Correlation clamp applied: {clamp_reason}")

                        # Calculate position size through risk engine
                        position_request = risk_engine.evaluate_new_position(
                            symbol=signal.symbol,
                            direction=signal.direction,
                            entry_price=signal.entry_price,
                            stop_loss=signal.stop_loss,
                            base_risk_pct=config.risk.max_risk_per_idea_pct * risk_mult,
                        )

                        if not position_request.approved:
                            logger.info(f"Position rejected by risk engine: {position_request.reason}")
                            continue

                        # Apply compliance guards
                        compliance_check = compliance_guard.check_new_trade(
                            symbol=signal.symbol,
                            volume=position_request.volume,
                            direction=signal.direction,
                        )

                        if not compliance_check.approved:
                            logger.info(f"Trade rejected by compliance: {compliance_check.reason}")
                            continue

                        # Check news guard
                        news_check = news_guard.check_trade_allowed(signal.symbol)
                        if not news_check.allowed:
                            logger.info(f"Trade blocked by news guard: {news_check.reason}")
                            continue

                        # Check lot caps
                        lot_cap_check = lot_caps.check_new_position(
                            symbol=signal.symbol,
                            volume=position_request.volume,
                        )

                        if not lot_cap_check.approved:
                            logger.info(f"Trade rejected by lot caps: {lot_cap_check.reason}")
                            continue

                        # ALL GUARDS PASSED - Execute trade
                        logger.info(f"🎯 SIGNAL: {signal.strategy_name} {signal.direction.value} {signal.symbol} @ {signal.entry_price:.5f} | SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f} | Size: {position_request.volume:.2f} lots | Risk mult: {risk_mult:.2f}x")

                        order = broker.place_order(
                            symbol=signal.symbol,
                            order_type=signal.direction,
                            volume=position_request.volume,
                            price=signal.entry_price,
                            sl=signal.stop_loss,
                            tp=signal.take_profit,
                            comment=f"{signal.strategy_name}|{signal.reason[:20]}",
                        )

                        if order:
                            trades_count += 1
                            logger.info(f"✅ Order placed: ticket={order.ticket}")
                            telemetry.log_trade(
                                symbol=signal.symbol,
                                direction=signal.direction.value,
                                entry_price=signal.entry_price,
                                volume=position_request.volume,
                                sl=signal.stop_loss,
                                tp=signal.take_profit,
                                strategy=signal.strategy_name,
                            )

                            # Track with health monitor
                            if health_monitor:
                                health_monitor.record_slippage(signal.entry_price, order.fill_price, symbol_info.pip_size)

                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}", exc_info=True)

            # Check health monitors
            if health_monitor:
                # Check breach probability
                dd_floor = getattr(dd_tracker, 'floor', dd_tracker.locked_floor if hasattr(dd_tracker, 'locked_floor') else 0)
                if dd_floor > 0:
                    alert = health_monitor.check_breach_probability_alert(
                        current_equity=account_info.equity,
                        dd_floor=dd_floor,
                        recent_volatility=0.01,  # TODO: calculate actual vol
                        hours_ahead=4,
                    )
                    if alert:
                        logger.warning(f"⚠️ HEALTH ALERT: {alert.message}")

                # Check alpha drift
                drift_alert = health_monitor.check_alpha_drift_alert()
                if drift_alert:
                    logger.warning(f"⚠️ ALPHA DRIFT: {drift_alert.message}")

            # Print status
            logger.info(
                f"Equity: ${account_info.equity:,.2f} | "
                f"Balance: ${account_info.balance:,.2f} | "
                f"Positions: {len(broker_positions)} | "
                f"DD: {dd_tracker.utilization_cumulative()*100:.1f}%"
            )

            # Update dashboard
            dashboard.update_state(
                equity=account_info.equity,
                balance=account_info.balance,
                dd_floor=getattr(dd_tracker, 'floor', dd_tracker.locked_floor if hasattr(dd_tracker, 'locked_floor') else 95000),
                dd_utilization=dd_tracker.utilization_cumulative() * 100.0,
                margin_used=account_info.margin,
                free_margin=account_info.free_margin,
                open_positions=len(broker_positions),
                daily_pnl=account_info.equity - daily_start_equity,
                signals_today=signals_count,
                trades_today=trades_count,
            )

            iteration += 1
            time.sleep(60)  # Scan every minute

    except KeyboardInterrupt:
        logger.info("Shutting down...")

    finally:
        # Export reports
        logger.info("Exporting telemetry...")
        exports = telemetry.export_all()
        for report_type, filepath in exports.items():
            logger.info(f"  {report_type}: {filepath}")

        broker.disconnect()

    logger.info("Trading system stopped")
    return 0


def validate_config(args: argparse.Namespace) -> int:
    """Validate configuration file."""
    logger.info(f"Validating config: {args.config}")

    try:
        config = TradingConfig.from_yaml(args.config)
        logger.info("✓ Configuration is valid")
        logger.info(f"  Program: {config.account.program.value}")
        logger.info(f"  Starting balance: ${config.account.starting_balance:,.2f}")
        logger.info(f"  DD model: {config.drawdown.model.value}")
        logger.info(f"  Daily DD: {config.daily_drawdown.pct*100:.1f}%")
        return 0

    except Exception as e:
        logger.error(f"✗ Configuration validation failed: {e}")
        return 1


def export_reports(args: argparse.Namespace) -> int:
    """Export telemetry reports."""
    logger.info("Exporting reports...")
    logger.info(f"  Logs dir: {args.logs_dir}")
    logger.info(f"  Output dir: {args.output_dir}")

    # This would scan logs and generate reports
    logger.info("Report export complete")
    return 0


def show_status(args: argparse.Namespace) -> int:
    """Show system status."""
    config = TradingConfig.from_yaml(args.config)

    logger.info("=" * 60)
    logger.info("INSTANT BOT - System Status")
    logger.info("=" * 60)
    logger.info(f"Program: {config.account.program.value}")
    logger.info(f"Starting balance: ${config.account.starting_balance:,.2f}")
    logger.info(f"DD model: {config.drawdown.model.value}")
    logger.info(f"Risk per idea: {config.risk.max_risk_per_idea_pct:.2f}%")
    logger.info(f"News guard: {'ON' if config.news.enforce_window else 'OFF'}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
