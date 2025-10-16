"""
MT5 SERVICE - All MetaTrader5 operations
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def init_mt5():
    """Initialize MT5 connection"""
    if not mt5.initialize():
        print("[ERROR] MT5 initialization failed")
        return False
    return True

def get_account_info():
    """Get account information"""
    return mt5.account_info()

def get_positions():
    """Get all open positions"""
    return mt5.positions_get()

def get_position_count():
    """Get number of open positions"""
    positions = get_positions()
    return len(positions) if positions else 0

def close_position(ticket):
    """Close a position by ticket"""
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return {'success': False, 'error': 'Position not found'}

    position = positions[0]

    # Prepare close request
    close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = mt5.symbol_info_tick(position.symbol).bid if close_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(position.symbol).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": close_type,
        "position": ticket,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "Close position",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return {'success': True, 'profit': position.profit}
    else:
        return {'success': False, 'error': f'Close failed: {result.retcode if result else "Unknown"}'}

def close_all_positions():
    """Close all open positions"""
    positions = get_positions()
    if not positions:
        return {'success': True, 'count': 0, 'total_pnl': 0}

    closed_count = 0
    total_pnl = 0
    errors = []

    for position in positions:
        result = close_position(position.ticket)
        if result['success']:
            closed_count += 1
            total_pnl += result['profit']
        else:
            errors.append(f"{position.symbol}: {result['error']}")

    return {
        'success': len(errors) == 0,
        'count': closed_count,
        'total_pnl': total_pnl,
        'errors': errors
    }

def close_losing_positions():
    """Close only losing positions"""
    positions = get_positions()
    if not positions:
        return {'success': True, 'count': 0, 'total_pnl': 0}

    closed_count = 0
    total_pnl = 0
    errors = []

    for position in positions:
        if position.profit < 0:
            result = close_position(position.ticket)
            if result['success']:
                closed_count += 1
                total_pnl += result['profit']
            else:
                errors.append(f"{position.symbol}: {result['error']}")

    return {
        'success': len(errors) == 0,
        'count': closed_count,
        'total_pnl': total_pnl,
        'errors': errors
    }

def get_symbol_data(symbol, timeframe=mt5.TIMEFRAME_H4, count=300):
    """Get historical data for a symbol"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def shutdown_mt5():
    """Shutdown MT5 connection"""
    mt5.shutdown()
