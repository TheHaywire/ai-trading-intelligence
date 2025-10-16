"""MetaTrader 5 broker adapter."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None  # type: ignore

from src.core.symbols import AssetClass, SymbolInfo, get_registry
from src.utils.throttle import RateLimiter
from src.utils.timebox import retry_with_backoff

logger = logging.getLogger(__name__)


class OrderType(str, Enum):
    """Order types."""

    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"


class OrderStatus(str, Enum):
    """Order execution status."""

    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class Position:
    """Open trading position."""

    ticket: int
    symbol: str
    type: OrderType
    volume: float
    open_price: float
    open_time: datetime
    stop_loss: float
    take_profit: float
    profit: float
    commission: float
    swap: float
    magic: int = 0
    comment: str = ""

    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.type in (OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP)

    @property
    def net_profit(self) -> float:
        """Get net profit including commission and swap."""
        return self.profit + self.commission + self.swap


@dataclass
class AccountInfo:
    """MT5 account information."""

    login: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    currency: str
    leverage: int
    server: str
    company: str
    name: str

    @property
    def margin_utilization(self) -> float:
        """Get margin utilization percentage."""
        return (self.margin / self.equity * 100.0) if self.equity > 0 else 0.0


@dataclass
class OrderRequest:
    """Order placement request."""

    symbol: str
    order_type: OrderType
    volume: float
    price: float
    stop_loss: float
    take_profit: float = 0.0
    comment: str = ""
    magic: int = 0
    deviation: int = 10


class MT5BrokerError(Exception):
    """MT5-specific errors."""

    pass


class MT5Broker:
    """MetaTrader 5 broker adapter."""

    def __init__(
        self,
        login: str,
        password: str,
        server: str,
        paper_mode: bool = False,
        rate_limit_per_second: int = 10,
    ):
        """
        Initialize MT5 broker connection.

        Args:
            login: MT5 account login
            password: MT5 account password
            server: MT5 server name
            paper_mode: If True, simulate operations without real connection
            rate_limit_per_second: Maximum requests per second
        """
        self.login = int(login) if login.isdigit() else 0
        self.password = password
        self.server = server
        self.paper_mode = paper_mode
        self.connected = False
        self.rate_limiter = RateLimiter(max_calls=rate_limit_per_second, period_seconds=1.0)
        self.symbol_registry = get_registry()

        if mt5 is None and not paper_mode:
            raise MT5BrokerError("MetaTrader5 package not installed")

    def connect(self) -> bool:
        """
        Connect to MT5 terminal.

        Returns:
            True if connection successful
        """
        if self.paper_mode:
            logger.info("Running in paper mode - no MT5 connection")
            self.connected = True
            return True

        if not mt5.initialize():
            error = mt5.last_error()
            raise MT5BrokerError(f"MT5 initialize failed: {error}")

        def _login() -> bool:
            return mt5.login(self.login, password=self.password, server=self.server)

        try:
            success = retry_with_backoff(_login, max_attempts=3)
            if not success:
                error = mt5.last_error()
                raise MT5BrokerError(f"MT5 login failed: {error}")

            self.connected = True
            logger.info(f"Connected to MT5: {self.server}, account {self.login}")
            return True

        except Exception as e:
            logger.error(f"MT5 connection failed: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from MT5 terminal."""
        if not self.paper_mode and self.connected:
            mt5.shutdown()
        self.connected = False
        logger.info("Disconnected from MT5")

    def get_account_info(self) -> AccountInfo:
        """
        Get account information.

        Returns:
            AccountInfo object
        """
        if self.paper_mode:
            # Return mock data for paper mode
            return AccountInfo(
                login=self.login,
                balance=100000.0,
                equity=100000.0,
                margin=0.0,
                free_margin=100000.0,
                margin_level=0.0,
                profit=0.0,
                currency="USD",
                leverage=100,
                server=self.server,
                company="Paper Trading",
                name="Paper Account",
            )

        self._check_connected()
        self.rate_limiter.acquire(wait=True)

        info = mt5.account_info()
        if info is None:
            raise MT5BrokerError(f"Failed to get account info: {mt5.last_error()}")

        return AccountInfo(
            login=info.login,
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level,
            profit=info.profit,
            currency=info.currency,
            leverage=info.leverage,
            server=info.server,
            company=info.company,
            name=info.name,
        )

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """
        Get symbol information from broker and registry.

        Args:
            symbol: Trading symbol

        Returns:
            SymbolInfo or None if not found
        """
        symbol = symbol.upper()

        if not self.paper_mode and self.connected:
            self.rate_limiter.acquire(wait=True)
            broker_info = mt5.symbol_info(symbol)

            if broker_info:
                # Update registry with broker data
                broker_data = {
                    "trade_contract_size": broker_info.trade_contract_size,
                    "volume_min": broker_info.volume_min,
                    "volume_max": broker_info.volume_max,
                    "volume_step": broker_info.volume_step,
                }
                self.symbol_registry.update_from_broker(symbol, broker_data)

        return self.symbol_registry.get(symbol)

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get open positions.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Position objects
        """
        if self.paper_mode:
            return []

        self._check_connected()
        self.rate_limiter.acquire(wait=True)

        if symbol:
            positions = mt5.positions_get(symbol=symbol.upper())
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        return [self._parse_position(p) for p in positions]

    def _parse_position(self, mt5_position: Any) -> Position:
        """Parse MT5 position to Position object."""
        order_type = OrderType.BUY if mt5_position.type == 0 else OrderType.SELL

        return Position(
            ticket=mt5_position.ticket,
            symbol=mt5_position.symbol,
            type=order_type,
            volume=mt5_position.volume,
            open_price=mt5_position.price_open,
            open_time=datetime.fromtimestamp(mt5_position.time, tz=timezone.utc),
            stop_loss=mt5_position.sl,
            take_profit=mt5_position.tp,
            profit=mt5_position.profit,
            commission=getattr(mt5_position, 'commission', 0.0),
            swap=getattr(mt5_position, 'swap', 0.0),
            magic=getattr(mt5_position, 'magic', 0),
            comment=getattr(mt5_position, 'comment', ""),
        )

    def place_order(self, request: OrderRequest) -> tuple[bool, str, Optional[int]]:
        """
        Place a trading order.

        Args:
            request: OrderRequest object

        Returns:
            (success, message, ticket)
        """
        if request.stop_loss == 0.0:
            return False, "Stop loss is mandatory", None

        if self.paper_mode:
            logger.info(f"[PAPER] Place order: {request}")
            return True, "Paper order placed", 999999

        self._check_connected()
        self.rate_limiter.acquire(wait=True)

        # Prepare MT5 order request
        symbol_info = mt5.symbol_info(request.symbol.upper())
        if symbol_info is None:
            return False, f"Symbol {request.symbol} not found", None

        # Map order type
        mt5_order_type = self._map_order_type(request.order_type)

        order_dict = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol.upper(),
            "volume": request.volume,
            "type": mt5_order_type,
            "price": request.price,
            "sl": request.stop_loss,
            "tp": request.take_profit,
            "deviation": request.deviation,
            "magic": request.magic,
            "comment": request.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(order_dict)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Order failed: {result.comment if result else 'Unknown error'}"
            logger.error(error_msg)
            return False, error_msg, None

        logger.info(f"Order placed: ticket={result.order}, volume={request.volume}")
        return True, "Order placed successfully", result.order

    def close_position(self, ticket: int) -> tuple[bool, str]:
        """
        Close an open position.

        Args:
            ticket: Position ticket number

        Returns:
            (success, message)
        """
        if self.paper_mode:
            logger.info(f"[PAPER] Close position: {ticket}")
            return True, "Paper position closed"

        self._check_connected()
        self.rate_limiter.acquire(wait=True)

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, f"Position {ticket} not found"

        position = position[0]

        # Create closing order (opposite direction)
        close_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position.symbol).bid if position.type == 0 else mt5.symbol_info_tick(position.symbol).ask

        order_dict = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": position.magic,
            "comment": "Close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(order_dict)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Close failed: {result.comment if result else 'Unknown error'}"
            logger.error(error_msg)
            return False, error_msg

        logger.info(f"Position closed: ticket={ticket}")
        return True, "Position closed successfully"

    def get_bars(self, symbol: str, timeframe: str, count: int = 100) -> Optional[List[Dict]]:
        """
        Get historical bars for a symbol.

        Args:
            symbol: Symbol name
            timeframe: Timeframe ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
            count: Number of bars

        Returns:
            List of OHLCV dicts or None
        """
        if self.paper_mode:
            return None

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

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            return None

        return [
            {
                "time": datetime.fromtimestamp(bar["time"], tz=timezone.utc),
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
                "volume": int(bar["tick_volume"]),
            }
            for bar in rates
        ]

    def get_tick(self, symbol: str):
        """
        Get current tick for symbol.

        Args:
            symbol: Symbol name

        Returns:
            Tick object with bid/ask/time
        """
        if self.paper_mode:
            return None

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        from dataclasses import dataclass

        @dataclass
        class Tick:
            symbol: str
            bid: float
            ask: float
            time: datetime

        return Tick(
            symbol=symbol,
            bid=tick.bid,
            ask=tick.ask,
            time=datetime.fromtimestamp(tick.time, tz=timezone.utc),
        )

    def modify_position(
        self,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> tuple[bool, str]:
        """
        Modify position stop loss or take profit.

        Args:
            ticket: Position ticket
            stop_loss: New stop loss (None to keep current)
            take_profit: New take profit (None to keep current)

        Returns:
            (success, message)
        """
        if self.paper_mode:
            logger.info(f"[PAPER] Modify position: {ticket}, SL={stop_loss}, TP={take_profit}")
            return True, "Paper position modified"

        self._check_connected()
        self.rate_limiter.acquire(wait=True)

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, f"Position {ticket} not found"

        position = position[0]

        sl = stop_loss if stop_loss is not None else position.sl
        tp = take_profit if take_profit is not None else position.tp

        order_dict = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": position.symbol,
            "sl": sl,
            "tp": tp,
        }

        result = mt5.order_send(order_dict)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Modify failed: {result.comment if result else 'Unknown error'}"
            logger.error(error_msg)
            return False, error_msg

        logger.info(f"Position modified: ticket={ticket}")
        return True, "Position modified successfully"

    def _map_order_type(self, order_type: OrderType) -> int:
        """Map OrderType to MT5 order type constant."""
        mapping = {
            OrderType.BUY: mt5.ORDER_TYPE_BUY,
            OrderType.SELL: mt5.ORDER_TYPE_SELL,
            OrderType.BUY_LIMIT: mt5.ORDER_TYPE_BUY_LIMIT,
            OrderType.SELL_LIMIT: mt5.ORDER_TYPE_SELL_LIMIT,
            OrderType.BUY_STOP: mt5.ORDER_TYPE_BUY_STOP,
            OrderType.SELL_STOP: mt5.ORDER_TYPE_SELL_STOP,
        }
        return mapping.get(order_type, mt5.ORDER_TYPE_BUY)

    def _check_connected(self) -> None:
        """Check if connected to MT5."""
        if not self.connected:
            raise MT5BrokerError("Not connected to MT5")

    def __enter__(self) -> "MT5Broker":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()
