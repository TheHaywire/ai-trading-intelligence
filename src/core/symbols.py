"""Symbol metadata and classification."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class AssetClass(str, Enum):
    """Asset class classification."""

    FX = "fx"
    INDICES = "indices"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    STOCKS = "stocks"


@dataclass
class SymbolInfo:
    """Trading symbol metadata."""

    symbol: str
    asset_class: AssetClass
    contract_size: float
    pip_size: float
    min_lot: float
    max_lot: float
    lot_step: float
    base_currency: str
    quote_currency: str
    margin_currency: str
    description: str = ""

    @property
    def point_value(self) -> float:
        """Get point value for margin calculations."""
        return self.contract_size * self.pip_size


class SymbolRegistry:
    """Registry of trading symbols and their metadata."""

    def __init__(self) -> None:
        self._symbols: Dict[str, SymbolInfo] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize common symbols with default metadata."""
        # Major FX pairs
        fx_pairs = [
            ("EURUSD", "EUR", "USD"),
            ("GBPUSD", "GBP", "USD"),
            ("USDJPY", "USD", "JPY"),
            ("USDCHF", "USD", "CHF"),
            ("AUDUSD", "AUD", "USD"),
            ("USDCAD", "USD", "CAD"),
            ("NZDUSD", "NZD", "USD"),
        ]

        for symbol, base, quote in fx_pairs:
            self._symbols[symbol] = SymbolInfo(
                symbol=symbol,
                asset_class=AssetClass.FX,
                contract_size=100000.0,
                pip_size=0.0001 if quote != "JPY" else 0.01,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                base_currency=base,
                quote_currency=quote,
                margin_currency=base,
                description=f"{base}/{quote}",
            )

        # Minor FX pairs
        minor_pairs = [
            ("EURGBP", "EUR", "GBP"),
            ("EURJPY", "EUR", "JPY"),
            ("GBPJPY", "GBP", "JPY"),
            ("EURCHF", "EUR", "CHF"),
            ("AUDJPY", "AUD", "JPY"),
            ("CADJPY", "CAD", "JPY"),
        ]

        for symbol, base, quote in minor_pairs:
            self._symbols[symbol] = SymbolInfo(
                symbol=symbol,
                asset_class=AssetClass.FX,
                contract_size=100000.0,
                pip_size=0.01 if quote == "JPY" else 0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                base_currency=base,
                quote_currency=quote,
                margin_currency=base,
                description=f"{base}/{quote}",
            )

        # US Indices
        self.register(
            SymbolInfo(
                symbol="US30",
                asset_class=AssetClass.INDICES,
                contract_size=10.0,
                pip_size=1.0,
                min_lot=0.01,
                max_lot=50.0,
                lot_step=0.01,
                base_currency="USD",
                quote_currency="USD",
                margin_currency="USD",
                description="Dow Jones Industrial Average",
            )
        )

        self.register(
            SymbolInfo(
                symbol="US500",
                asset_class=AssetClass.INDICES,
                contract_size=50.0,
                pip_size=0.01,
                min_lot=0.01,
                max_lot=50.0,
                lot_step=0.01,
                base_currency="USD",
                quote_currency="USD",
                margin_currency="USD",
                description="S&P 500",
            )
        )

        self.register(
            SymbolInfo(
                symbol="NAS100",
                asset_class=AssetClass.INDICES,
                contract_size=20.0,
                pip_size=0.01,
                min_lot=0.01,
                max_lot=50.0,
                lot_step=0.01,
                base_currency="USD",
                quote_currency="USD",
                margin_currency="USD",
                description="Nasdaq 100",
            )
        )

        # Commodities
        self.register(
            SymbolInfo(
                symbol="XAUUSD",
                asset_class=AssetClass.COMMODITIES,
                contract_size=100.0,
                pip_size=0.01,
                min_lot=0.01,
                max_lot=50.0,
                lot_step=0.01,
                base_currency="XAU",
                quote_currency="USD",
                margin_currency="USD",
                description="Gold vs USD",
            )
        )

        self.register(
            SymbolInfo(
                symbol="XAGUSD",
                asset_class=AssetClass.COMMODITIES,
                contract_size=5000.0,
                pip_size=0.001,
                min_lot=0.01,
                max_lot=50.0,
                lot_step=0.01,
                base_currency="XAG",
                quote_currency="USD",
                margin_currency="USD",
                description="Silver vs USD",
            )
        )

        self.register(
            SymbolInfo(
                symbol="WTIUSD",
                asset_class=AssetClass.COMMODITIES,
                contract_size=1000.0,
                pip_size=0.01,
                min_lot=0.01,
                max_lot=50.0,
                lot_step=0.01,
                base_currency="WTI",
                quote_currency="USD",
                margin_currency="USD",
                description="WTI Crude Oil",
            )
        )

        # Crypto
        self.register(
            SymbolInfo(
                symbol="BTCUSD",
                asset_class=AssetClass.CRYPTO,
                contract_size=1.0,
                pip_size=1.0,
                min_lot=0.01,
                max_lot=10.0,
                lot_step=0.01,
                base_currency="BTC",
                quote_currency="USD",
                margin_currency="USD",
                description="Bitcoin vs USD",
            )
        )

        self.register(
            SymbolInfo(
                symbol="ETHUSD",
                asset_class=AssetClass.CRYPTO,
                contract_size=1.0,
                pip_size=0.01,
                min_lot=0.01,
                max_lot=10.0,
                lot_step=0.01,
                base_currency="ETH",
                quote_currency="USD",
                margin_currency="USD",
                description="Ethereum vs USD",
            )
        )

    def register(self, symbol_info: SymbolInfo) -> None:
        """Register a symbol."""
        self._symbols[symbol_info.symbol.upper()] = symbol_info

    def get(self, symbol: str) -> Optional[SymbolInfo]:
        """Get symbol information."""
        return self._symbols.get(symbol.upper())

    def get_asset_class(self, symbol: str) -> Optional[AssetClass]:
        """Get asset class for a symbol."""
        info = self.get(symbol)
        return info.asset_class if info else None

    def list_symbols(self, asset_class: Optional[AssetClass] = None) -> list[str]:
        """List all symbols, optionally filtered by asset class."""
        if asset_class is None:
            return list(self._symbols.keys())
        return [s for s, info in self._symbols.items() if info.asset_class == asset_class]

    def update_from_broker(self, symbol: str, broker_data: dict) -> None:
        """Update symbol info with data from broker."""
        existing = self.get(symbol)
        if existing:
            # Update mutable fields
            existing.contract_size = broker_data.get("trade_contract_size", existing.contract_size)
            existing.min_lot = broker_data.get("volume_min", existing.min_lot)
            existing.max_lot = broker_data.get("volume_max", existing.max_lot)
            existing.lot_step = broker_data.get("volume_step", existing.lot_step)


# Global registry instance
_registry = SymbolRegistry()


def get_registry() -> SymbolRegistry:
    """Get the global symbol registry."""
    return _registry
