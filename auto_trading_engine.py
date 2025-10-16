"""
INSTITUTIONAL AUTO-TRADING ENGINE
Executes trades automatically across multiple strategies
Like having 1000 expert traders working 24/7
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import requests

# EmailJS Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

# TRADING CONFIGURATION
ACCOUNT_RISK_PER_TRADE = 0.01  # 1% risk per trade
MAX_OPEN_TRADES = 5
MAX_DAILY_TRADES = 10
MAX_DAILY_LOSS_PCT = 0.05  # Stop trading if down 5% in a day

# Symbols to trade
SYMBOLS = ['GOLD', 'SILVER', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD',
           'EURGBP', 'EURJPY', 'GBPJPY', 'BTCUSD', 'ETHUSD', 'XRPUSD']

TIMEFRAME = mt5.TIMEFRAME_H1
CHECK_INTERVAL = 600  # Check every 10 minutes

POSITIONS_FILE = "active_positions.json"
PERFORMANCE_FILE = "performance_log.json"

def send_email(subject, message):
    """Send email alert"""
    try:
        url = "https://api.emailjs.com/api/v1.0/email/send"
        payload = {
            "service_id": EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id": EMAILJS_PUBLIC_KEY,
            "accessToken": EMAILJS_PRIVATE_KEY,
            "template_params": {
                "to_email": EMAIL_TO,
                "subject": subject,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except:
        return False

def calculate_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def get_account_info():
    """Get account balance and equity"""
    account_info = mt5.account_info()
    if account_info:
        return {
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin_free': account_info.margin_free,
            'margin_level': account_info.margin_level if account_info.margin > 0 else 0
        }
    return None

def calculate_position_size(symbol, entry_price, stop_loss, account_balance):
    """Calculate lot size based on risk percentage"""
    risk_amount = account_balance * ACCOUNT_RISK_PER_TRADE

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return 0.01  # Minimum lot

    pip_value = symbol_info.trade_tick_value
    pip_size = symbol_info.point

    distance_in_pips = abs(entry_price - stop_loss) / pip_size
    lot_size = risk_amount / (distance_in_pips * pip_value)

    # Round to valid lot size
    lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
    lot_size = round(lot_size / symbol_info.volume_step) * symbol_info.volume_step

    return lot_size

def check_signal(symbol):
    """Check for trading signals"""
    try:
        rates = mt5.copy_rates_range(symbol, TIMEFRAME,
                                     datetime.now() - timedelta(days=30),
                                     datetime.now())

        if rates is None or len(rates) < 100:
            return None

        df = pd.DataFrame(rates)
        close = df['close']
        high = df['high']
        low = df['low']

        # Calculate indicators
        ema25 = calculate_ema(close, 25)
        ema100 = calculate_ema(close, 100)
        rsi = calculate_rsi(close, 28)
        atr = calculate_atr(high, low, close, 14)

        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]

        # Donchian channels
        upper_channel = high.rolling(50).max()
        lower_channel = low.rolling(50).min()

        signal = None

        # Strategy 1: EMA Bullish Cross
        if ema25.iloc[-1] > ema100.iloc[-1] and ema25.iloc[-2] <= ema100.iloc[-2]:
            signal = {
                'type': 'EMA_BULLISH_CROSS',
                'direction': 'LONG',
                'entry': current_price,
                'sl': current_price - (1.5 * current_atr),
                'tp1': current_price + (2 * current_atr),
                'tp2': current_price + (3 * current_atr),
                'tp3': current_price + (4.5 * current_atr),
                'confidence': 0.75
            }

        # Strategy 2: EMA Bearish Cross
        elif ema25.iloc[-1] < ema100.iloc[-1] and ema25.iloc[-2] >= ema100.iloc[-2]:
            signal = {
                'type': 'EMA_BEARISH_CROSS',
                'direction': 'SHORT',
                'entry': current_price,
                'sl': current_price + (1.5 * current_atr),
                'tp1': current_price - (2 * current_atr),
                'tp2': current_price - (3 * current_atr),
                'tp3': current_price - (4.5 * current_atr),
                'confidence': 0.75
            }

        # Strategy 3: RSI Oversold (LONG only)
        if current_rsi < 35 and ema25.iloc[-1] > ema100.iloc[-1]:
            signal = {
                'type': 'RSI_OVERSOLD',
                'direction': 'LONG',
                'entry': current_price,
                'sl': current_price - (1.5 * current_atr),
                'tp1': current_price + (2 * current_atr),
                'tp2': current_price + (3 * current_atr),
                'tp3': current_price + (4.5 * current_atr),
                'confidence': 0.85 if current_rsi < 30 else 0.70
            }

        # Strategy 4: RSI Overbought (SHORT only)
        elif current_rsi > 80 and ema25.iloc[-1] < ema100.iloc[-1]:
            signal = {
                'type': 'RSI_OVERBOUGHT',
                'direction': 'SHORT',
                'entry': current_price,
                'sl': current_price + (1.5 * current_atr),
                'tp1': current_price - (2 * current_atr),
                'tp2': current_price - (3 * current_atr),
                'tp3': current_price - (4.5 * current_atr),
                'confidence': 0.85 if current_rsi > 85 else 0.70
            }

        # Strategy 5: Donchian Breakout (LONG)
        if close.iloc[-1] > upper_channel.iloc[-2] and close.iloc[-2] <= upper_channel.iloc[-3]:
            if ema25.iloc[-1] > ema100.iloc[-1]:  # Confirm with trend
                signal = {
                    'type': 'DONCHIAN_BREAKOUT',
                    'direction': 'LONG',
                    'entry': current_price,
                    'sl': current_price - (1.5 * current_atr),
                    'tp1': current_price + (2 * current_atr),
                    'tp2': current_price + (3 * current_atr),
                    'tp3': current_price + (4.5 * current_atr),
                    'confidence': 0.80
                }

        # Strategy 6: Donchian Breakdown (SHORT)
        elif close.iloc[-1] < lower_channel.iloc[-2] and close.iloc[-2] >= lower_channel.iloc[-3]:
            if ema25.iloc[-1] < ema100.iloc[-1]:  # Confirm with trend
                signal = {
                    'type': 'DONCHIAN_BREAKDOWN',
                    'direction': 'SHORT',
                    'entry': current_price,
                    'sl': current_price + (1.5 * current_atr),
                    'tp1': current_price - (2 * current_atr),
                    'tp2': current_price - (3 * current_atr),
                    'tp3': current_price - (4.5 * current_atr),
                    'confidence': 0.80
                }

        if signal:
            signal['symbol'] = symbol
            signal['timestamp'] = datetime.now().isoformat()
            signal['rsi'] = current_rsi
            signal['ema25'] = ema25.iloc[-1]
            signal['ema100'] = ema100.iloc[-1]

        return signal

    except Exception as e:
        print(f"    [ERROR] {symbol}: {str(e)}")
        return None

def execute_trade(signal, account_balance):
    """Execute trade on MT5"""
    symbol = signal['symbol']
    direction = signal['direction']
    entry = signal['entry']
    sl = signal['sl']
    tp1 = signal['tp1']

    # Calculate lot size
    lot_size = calculate_position_size(symbol, entry, sl, account_balance)

    # Prepare request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if direction == "LONG" else mt5.ORDER_TYPE_SELL,
        "price": entry,
        "sl": sl,
        "tp": tp1,  # Set first take profit
        "deviation": 20,
        "magic": 234000,
        "comment": f"Auto_{signal['type']}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send order
    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"    [EXECUTED] {symbol} {direction} @ {entry:.5f} | Lot: {lot_size} | SL: {sl:.5f} | TP: {tp1:.5f}")
        return {
            'success': True,
            'ticket': result.order,
            'symbol': symbol,
            'direction': direction,
            'entry': entry,
            'sl': sl,
            'tp1': tp1,
            'tp2': signal['tp2'],
            'tp3': signal['tp3'],
            'lot_size': lot_size,
            'signal_type': signal['type'],
            'confidence': signal['confidence'],
            'opened_at': datetime.now().isoformat()
        }
    else:
        print(f"    [FAILED] {symbol} - Error: {result.retcode}")
        return {'success': False, 'error': result.retcode}

def manage_positions():
    """Manage open positions - trail stops, partial closes"""
    positions = mt5.positions_get()

    if not positions:
        return

    for pos in positions:
        # Check if position from our EA
        if pos.magic != 234000:
            continue

        current_price = pos.price_current
        entry_price = pos.price_open
        direction = "LONG" if pos.type == mt5.ORDER_TYPE_BUY else "SHORT"

        # Calculate unrealized P&L
        if direction == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Move SL to breakeven if profit > 1%
        if pnl_pct > 1.0 and pos.sl != pos.price_open:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "sl": entry_price,  # Move to breakeven
                "tp": pos.tp
            }
            mt5.order_send(request)
            print(f"    [BREAKEVEN] {pos.symbol} - Moved SL to breakeven")

def get_daily_performance():
    """Calculate today's performance"""
    # Get today's closed deals
    from_date = datetime.now().replace(hour=0, minute=0, second=0)
    to_date = datetime.now()

    deals = mt5.history_deals_get(from_date, to_date)

    if not deals:
        return {'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0}

    total_pnl = 0
    wins = 0
    losses = 0
    trades = 0

    for deal in deals:
        if deal.magic == 234000 and deal.entry == mt5.DEAL_ENTRY_OUT:
            trades += 1
            total_pnl += deal.profit
            if deal.profit > 0:
                wins += 1
            else:
                losses += 1

    return {
        'trades': trades,
        'pnl': total_pnl,
        'wins': wins,
        'losses': losses,
        'win_rate': (wins / trades * 100) if trades > 0 else 0
    }

def send_quantitative_update(stats, signals_found, trades_executed):
    """Send quantitative performance update like a hedge fund"""
    account = get_account_info()
    daily_perf = get_daily_performance()

    message = f"""
QUANTITATIVE PERFORMANCE UPDATE
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ACCOUNT METRICS
Balance: ${account['balance']:,.2f}
Equity: ${account['equity']:,.2f}
Free Margin: ${account['margin_free']:,.2f}
Margin Level: {account['margin_level']:.2f}%

TODAY'S PERFORMANCE
Trades: {daily_perf['trades']}
P&L: ${daily_perf['pnl']:,.2f}
Win Rate: {daily_perf['win_rate']:.1f}%
Winners: {daily_perf['wins']} | Losers: {daily_perf['losses']}

CURRENT SCAN
Symbols Scanned: {len(SYMBOLS)}
Signals Found: {signals_found}
Trades Executed: {trades_executed}
Open Positions: {len(mt5.positions_get()) if mt5.positions_get() else 0}

SYSTEM STATUS
Auto-Trading: ACTIVE
Risk Per Trade: {ACCOUNT_RISK_PER_TRADE * 100}%
Max Open Trades: {MAX_OPEN_TRADES}
Check Interval: {CHECK_INTERVAL / 60} minutes

Next scan in {CHECK_INTERVAL / 60} minutes
"""

    send_email("Quant Update: Auto-Trading Active", message)

# Main execution loop
print("="*80)
print("INSTITUTIONAL AUTO-TRADING ENGINE")
print("="*80)
print(f"Risk per trade: {ACCOUNT_RISK_PER_TRADE * 100}%")
print(f"Max open trades: {MAX_OPEN_TRADES}")
print(f"Max daily loss: {MAX_DAILY_LOSS_PCT * 100}%")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

# Send startup email
account = get_account_info()
send_email(
    "AUTO-TRADING STARTED",
    f"Institutional auto-trading engine started\nBalance: ${account['balance']:,.2f}\nRisk per trade: {ACCOUNT_RISK_PER_TRADE * 100}%"
)

scan_count = 0

try:
    while True:
        scan_count += 1
        print(f"\n{'='*80}")
        print(f"SCAN #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Check daily loss limit
        daily_perf = get_daily_performance()
        account = get_account_info()

        if daily_perf['pnl'] < -(account['balance'] * MAX_DAILY_LOSS_PCT):
            print(f"[STOP] Daily loss limit reached: ${daily_perf['pnl']:.2f}")
            send_email("AUTO-TRADING PAUSED", f"Daily loss limit reached: ${daily_perf['pnl']:.2f}\nTrading paused for today")
            break

        # Check max open trades
        open_positions = mt5.positions_get()
        num_open = len(open_positions) if open_positions else 0

        print(f"Open Positions: {num_open}/{MAX_OPEN_TRADES}")
        print(f"Today's P&L: ${daily_perf['pnl']:.2f} ({daily_perf['trades']} trades)")

        signals_found = 0
        trades_executed = 0

        if num_open < MAX_OPEN_TRADES and daily_perf['trades'] < MAX_DAILY_TRADES:
            print(f"\nScanning {len(SYMBOLS)} symbols...")

            for symbol in SYMBOLS:
                print(f"  {symbol:10s}...", end=" ")

                signal = check_signal(symbol)

                if signal:
                    signals_found += 1
                    print(f"[SIGNAL] {signal['type']} {signal['direction']} @ {signal['entry']:.5f} (Conf: {signal['confidence']:.0%})")

                    # Execute trade
                    result = execute_trade(signal, account['balance'])

                    if result['success']:
                        trades_executed += 1
                else:
                    print("[NO SIGNAL]")
        else:
            print("\nMax trades reached, managing positions only...")

        # Manage open positions
        if num_open > 0:
            print("\nManaging open positions...")
            manage_positions()

        # Send update every hour (6 scans)
        if scan_count % 6 == 0:
            send_quantitative_update(account, signals_found, trades_executed)

        print(f"\nSleeping for {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("\n\n[STOPPING] Auto-trading engine stopped by user")
    account = get_account_info()
    daily_perf = get_daily_performance()
    send_email(
        "AUTO-TRADING STOPPED",
        f"Engine stopped\nFinal balance: ${account['balance']:,.2f}\nToday's P&L: ${daily_perf['pnl']:.2f}\nTrades: {daily_perf['trades']}"
    )

mt5.shutdown()
print("[DONE]")
