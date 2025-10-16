# Role: MT5 Broker Adapter
Build a robust adapter for MetaTrader 5.

## Requirements
- Login/connect, symbol normalization, contract size, tick size/point value.
- Place/modify/close orders with mandatory SL.
- Query open positions, pending orders, equity/balance/PL stream.
- Simulate margin using min(broker leverage, rules leverage).
- Reduce-only mode honored at adapter layer.

## Files
- `core/broker_mt5.py`
- `core/symbols.py` (symbol metadata registry)
- `utils/throttle.py` (to rate-limit ops)
- `utils/timebox.py` (deadline contexts for broker calls)

Include retry logic and structured error messages.
