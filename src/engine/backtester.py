"""Backtesting engine for strategy validation."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import MetaTrader5 as mt5
import numpy as np

from src.strategy.loader import MarketState, Signal, Strategy

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Backtest trade record."""

    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    direction: str
    entry_price: float
    exit_price: Optional[float]
    volume: float
    stop_loss: float
    take_profit: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = "open"
    strategy_name: str = ""


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    expectancy: float
    avg_trade_duration_hours: float
    final_equity: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": f"{self.win_rate:.1%}",
            "total_pnl": f"${self.total_pnl:,.2f}",
            "total_pnl_pct": f"{self.total_pnl_pct:+.2%}",
            "avg_win": f"${self.avg_win:,.2f}",
            "avg_loss": f"${self.avg_loss:,.2f}",
            "profit_factor": f"{self.profit_factor:.2f}",
            "max_drawdown": f"${self.max_drawdown:,.2f}",
            "max_drawdown_pct": f"{self.max_drawdown_pct:.2%}",
            "sharpe_ratio": f"{self.sharpe_ratio:.2f}",
            "expectancy": f"${self.expectancy:.2f}",
            "avg_trade_duration_hours": f"{self.avg_trade_duration_hours:.1f}h",
            "final_equity": f"${self.final_equity:,.2f}",
        }


class Backtester:
    """
    Backtest trading strategies with historical data.

    Features:
    - Historical bar replay
    - Realistic trade simulation (spread, slippage)
    - Full P&L calculation with position sizing
    - Performance metrics (Sharpe, drawdown, win rate)
    - Trade log export
    """

    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 100000.0,
        risk_per_trade_pct: float = 2.0,
        spread_pips: float = 2.0,
        slippage_pips: float = 1.0,
        commission_per_lot: float = 7.0,
    ):
        """
        Initialize backtester.

        Args:
            strategy: Strategy to backtest
            initial_capital: Starting capital
            risk_per_trade_pct: Risk % per trade
            spread_pips: Average spread in pips
            slippage_pips: Average slippage in pips
            commission_per_lot: Commission per lot (round trip)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.spread_pips = spread_pips
        self.slippage_pips = slippage_pips
        self.commission_per_lot = commission_per_lot

        self.equity = initial_capital
        self.balance = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.open_trades: List[Trade] = []

    def fetch_historical_bars(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> Optional[List[Dict]]:
        """
        Fetch historical bars from MT5.

        Args:
            symbol: Symbol name
            timeframe: Timeframe (H1, H4, D1)
            start_date: Start date
            end_date: End date

        Returns:
            List of OHLCV dicts or None
        """
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }

        tf = timeframe_map.get(timeframe)
        if tf is None:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None

        if not mt5.initialize():
            logger.error("MT5 initialize failed")
            return None

        rates = mt5.copy_rates_range(symbol, tf, start_date, end_date)

        if rates is None or len(rates) == 0:
            logger.error(f"No data for {symbol} {timeframe} from {start_date} to {end_date}")
            return None

        bars = [
            {
                "time": datetime.fromtimestamp(bar["time"]),
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
                "volume": int(bar["tick_volume"]),
            }
            for bar in rates
        ]

        logger.info(f"Fetched {len(bars)} bars for {symbol} {timeframe}")
        return bars

    def calculate_position_size(
        self, symbol: str, entry_price: float, stop_loss: float, pip_value: float = 10.0
    ) -> float:
        """
        Calculate position size based on risk %.

        Args:
            symbol: Symbol name
            entry_price: Entry price
            stop_loss: Stop loss price
            pip_value: Value of 1 pip per lot (default $10 for FX)

        Returns:
            Position size in lots
        """
        risk_amount = self.equity * (self.risk_per_trade_pct / 100.0)
        price_diff = abs(entry_price - stop_loss)

        # Calculate pips based on symbol type
        if "GOLD" in symbol.upper() or "XAU" in symbol.upper():
            # Gold: 1 pip = $0.10 movement
            pips = price_diff / 0.1
        elif "JPY" in symbol:
            # JPY pairs: 1 pip = 0.01
            pips = price_diff / 0.01
        else:
            # Forex: 1 pip = 0.0001
            pips = price_diff / 0.0001

        # Lot size
        lot_size = risk_amount / (pips * pip_value)

        # Round to 2 decimals
        return round(lot_size, 2)

    def simulate_fill(self, signal: Signal, current_bar: Dict) -> Tuple[float, float]:
        """
        Simulate realistic order fill with spread and slippage.

        Args:
            signal: Trading signal
            current_bar: Current price bar

        Returns:
            (fill_price, actual_sl)
        """
        # Determine pip size for spread/slippage
        if "GOLD" in signal.symbol.upper() or "XAU" in signal.symbol.upper():
            pip_size = 0.1
        elif "JPY" in signal.symbol:
            pip_size = 0.01
        else:
            pip_size = 0.0001

        # Add spread
        if signal.direction == "long":
            fill_price = signal.entry_price + (self.spread_pips * pip_size)
        else:
            fill_price = signal.entry_price - (self.spread_pips * pip_size)

        # Add slippage
        slippage = self.slippage_pips * pip_size
        if signal.direction == "long":
            fill_price += slippage
        else:
            fill_price -= slippage

        # Adjust SL for spread
        actual_sl = signal.stop_loss

        return fill_price, actual_sl

    def check_exit(self, trade: Trade, bar: Dict) -> Tuple[bool, float, str]:
        """
        Check if trade should exit (TP/SL hit).

        Args:
            trade: Open trade
            bar: Current price bar

        Returns:
            (should_exit, exit_price, exit_reason)
        """
        from src.core.broker_mt5 import OrderType

        # Determine if long/short
        is_long = trade.direction in (OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP, "long", "buy")

        # Check stop loss
        if is_long and bar["low"] <= trade.stop_loss:
            return True, trade.stop_loss, "stop_loss"
        elif not is_long and bar["high"] >= trade.stop_loss:
            return True, trade.stop_loss, "stop_loss"

        # Check take profit
        if is_long and bar["high"] >= trade.take_profit:
            return True, trade.take_profit, "take_profit"
        elif not is_long and bar["low"] <= trade.take_profit:
            return True, trade.take_profit, "take_profit"

        return False, 0.0, ""

    def close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, exit_reason: str):
        """Close a trade and calculate P&L."""
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = exit_reason

        # Calculate P&L in pips
        from src.core.broker_mt5 import OrderType

        is_long = trade.direction in (OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP, "long", "buy")

        # Calculate pip movement based on symbol type
        if "GOLD" in trade.symbol.upper() or "XAU" in trade.symbol.upper():
            # Gold: 1 pip = $0.10
            pip_size = 0.1
        elif "JPY" in trade.symbol:
            # JPY pairs: 1 pip = 0.01
            pip_size = 0.01
        else:
            # Forex: 1 pip = 0.0001
            pip_size = 0.0001

        if is_long:
            pip_pnl = (exit_price - trade.entry_price) / pip_size
        else:
            pip_pnl = (trade.entry_price - exit_price) / pip_size

        # Calculate P&L in dollars
        pip_value = 10.0  # $10 per pip per lot for FX
        gross_pnl = pip_pnl * pip_value * trade.volume

        # Subtract commission
        commission = self.commission_per_lot * trade.volume
        net_pnl = gross_pnl - commission

        trade.pnl = net_pnl
        trade.pnl_pct = (net_pnl / self.equity) * 100.0

        # Update equity and balance
        self.equity += net_pnl
        self.balance += net_pnl

        logger.debug(
            f"Closed {trade.direction} {trade.symbol} @ {exit_price:.5f}, "
            f"P&L: ${net_pnl:,.2f} ({trade.pnl_pct:+.2%}), reason: {exit_reason}"
        )

    def run(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> Optional[BacktestMetrics]:
        """
        Run backtest on historical data.

        Args:
            symbol: Symbol to trade
            timeframe: Timeframe (H1, H4, D1)
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            BacktestMetrics or None if failed
        """
        logger.info(
            f"Starting backtest: {symbol} {timeframe} from {start_date.date()} to {end_date.date()}"
        )

        # Fetch historical data for primary timeframe
        bars = self.fetch_historical_bars(symbol, timeframe, start_date, end_date)
        if not bars or len(bars) < 100:
            logger.error("Insufficient historical data")
            return None

        # Fetch H4 bars for trend detection (if primary is H1)
        bars_h4 = []
        if timeframe == "H1":
            bars_h4 = self.fetch_historical_bars(symbol, "H4", start_date, end_date)
            if not bars_h4:
                logger.warning("No H4 bars available - strategy may not generate signals")
                bars_h4 = []

        # Reset state
        self.equity = self.initial_capital
        self.balance = self.initial_capital
        self.trades = []
        self.open_trades = []
        self.equity_curve = [(bars[0]["time"], self.equity)]

        # Iterate through bars
        for i in range(100, len(bars)):
            current_bar = bars[i]
            current_time = current_bar["time"]

            # Check exit conditions for open trades
            for trade in self.open_trades[:]:
                should_exit, exit_price, exit_reason = self.check_exit(trade, current_bar)

                if should_exit:
                    self.close_trade(trade, exit_price, current_time, exit_reason)
                    self.trades.append(trade)
                    self.open_trades.remove(trade)

            # Build market state (match MarketState definition)
            from src.core.symbols import SymbolInfo

            from src.core.symbols import AssetClass

            symbol_info = SymbolInfo(
                symbol=symbol,
                asset_class=AssetClass.FX,
                contract_size=100000.0,
                pip_size=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                base_currency="EUR",
                quote_currency="USD",
                margin_currency="USD",
                description="Euro vs US Dollar",
            )

            # Find corresponding H4 bars (match timestamp)
            h4_window = []
            if bars_h4:
                # Get H4 bars up to current time
                h4_window = [b for b in bars_h4 if b["time"] <= current_time]
                h4_window = h4_window[-100:] if len(h4_window) > 100 else h4_window

            market_state = MarketState(
                symbol=symbol,
                timestamp=current_time,
                bid=current_bar["close"],
                ask=current_bar["close"] + (self.spread_pips * 0.0001),
                bars_h1=bars[i - 100 : i],
                bars_h4=h4_window,
                bars_d1=[],
                symbol_info=symbol_info,
            )

            # Generate signal
            signal = self.strategy.analyze(market_state)

            # Execute signal if generated
            if signal and len(self.open_trades) < 3:  # Max 3 concurrent positions
                # Calculate position size
                pip_value = 10.0
                volume = self.calculate_position_size(
                    symbol, signal.entry_price, signal.stop_loss, pip_value
                )

                # Simulate fill
                fill_price, actual_sl = self.simulate_fill(signal, current_bar)

                # Create trade
                trade = Trade(
                    entry_time=current_time,
                    exit_time=None,
                    symbol=symbol,
                    direction=signal.direction,
                    entry_price=fill_price,
                    exit_price=None,
                    volume=volume,
                    stop_loss=actual_sl,
                    take_profit=signal.take_profit,
                    strategy_name=self.strategy.name,
                )

                self.open_trades.append(trade)
                logger.debug(
                    f"Opened {signal.direction} {symbol} @ {fill_price:.5f}, "
                    f"SL: {actual_sl:.5f}, TP: {signal.take_profit:.5f}, Vol: {volume}"
                )

            # Record equity
            self.equity_curve.append((current_time, self.equity))

        # Close any remaining open trades at final price
        for trade in self.open_trades:
            final_bar = bars[-1]
            self.close_trade(trade, final_bar["close"], final_bar["time"], "end_of_backtest")
            self.trades.append(trade)

        self.open_trades = []

        # Calculate metrics
        metrics = self.calculate_metrics()

        logger.info(
            f"Backtest complete: {metrics.total_trades} trades, "
            f"Win rate: {metrics.win_rate:.1%}, "
            f"Total P&L: ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:+.2%})"
        )

        return metrics

    def calculate_metrics(self) -> BacktestMetrics:
        """Calculate backtest performance metrics."""
        if not self.trades:
            return BacktestMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_pnl_pct=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                expectancy=0.0,
                avg_trade_duration_hours=0.0,
                final_equity=self.equity,
            )

        # Win/loss stats
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        total_trades = len(self.trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0.0

        # P&L stats
        total_pnl = sum(t.pnl for t in self.trades)
        total_pnl_pct = (total_pnl / self.initial_capital) * 100.0

        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0.0

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        # Drawdown
        peak = self.initial_capital
        max_dd = 0.0
        max_dd_pct = 0.0

        for time, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0

            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        # Sharpe ratio (assuming daily returns)
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1][1]
            curr_equity = self.equity_curve[i][1]
            ret = (curr_equity - prev_equity) / prev_equity if prev_equity > 0 else 0.0
            returns.append(ret)

        if returns:
            sharpe_ratio = (
                (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0.0
            )
        else:
            sharpe_ratio = 0.0

        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))

        # Avg trade duration
        durations = []
        for t in self.trades:
            if t.exit_time:
                duration = (t.exit_time - t.entry_time).total_seconds() / 3600.0
                durations.append(duration)

        avg_duration = np.mean(durations) if durations else 0.0

        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct / 100.0,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct / 100.0,
            sharpe_ratio=sharpe_ratio,
            expectancy=expectancy,
            avg_trade_duration_hours=avg_duration,
            final_equity=self.equity,
        )

    def export_trades(self, filename: str):
        """Export trades to CSV."""
        import csv

        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Entry Time",
                    "Exit Time",
                    "Symbol",
                    "Direction",
                    "Entry Price",
                    "Exit Price",
                    "Volume",
                    "Stop Loss",
                    "Take Profit",
                    "P&L",
                    "P&L %",
                    "Exit Reason",
                    "Strategy",
                ]
            )

            for trade in self.trades:
                writer.writerow(
                    [
                        trade.entry_time,
                        trade.exit_time,
                        trade.symbol,
                        trade.direction,
                        trade.entry_price,
                        trade.exit_price,
                        trade.volume,
                        trade.stop_loss,
                        trade.take_profit,
                        f"{trade.pnl:.2f}",
                        f"{trade.pnl_pct:.2f}%",
                        trade.exit_reason,
                        trade.strategy_name,
                    ]
                )

        logger.info(f"Exported {len(self.trades)} trades to {filename}")
