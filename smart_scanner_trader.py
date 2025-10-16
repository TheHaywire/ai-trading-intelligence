"""
SMART SCANNER & AUTO-TRADER
Scans all popular symbols, identifies high-probability setups with TREND FILTERS,
and executes trades with proper risk management (0.5% risk per trade)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import requests

# EmailJS Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

# TRADING PARAMETERS (IMPROVED)
RISK_PER_TRADE = 0.005  # 0.5% risk per trade (reduced from 1%)
MAX_POSITIONS = 5  # Maximum open positions
MIN_CONFIDENCE = 75  # Minimum setup confidence to trade
ATR_STOP_MULTIPLIER = 2.0  # Wider stops (increased from 1.5)
ATR_TARGET_MULTIPLIER = 3.0  # 1:1.5 risk/reward minimum

def send_email(subject, html_message):
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
                "message": html_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except:
        return False

def get_technical_analysis(symbol, timeframe=mt5.TIMEFRAME_H4):
    """Get comprehensive technical analysis with STRICT TREND FILTERS"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 300)
    if rates is None or len(rates) == 0:
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')

    # Calculate indicators
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    df['SMA_200'] = df['close'].rolling(200).mean()
    df['EMA_12'] = df['close'].ewm(span=12).mean()
    df['EMA_26'] = df['close'].ewm(span=26).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()

    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()

    # Stochastic
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    df['Stoch_K'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    return {
        'symbol': symbol,
        'price': latest['close'],
        'rsi': latest['RSI'],
        'macd': latest['MACD'],
        'macd_signal': latest['MACD_Signal'],
        'sma_20': latest['SMA_20'],
        'sma_50': latest['SMA_50'],
        'sma_200': latest['SMA_200'],
        'atr': latest['ATR'],
        'stoch_k': latest['Stoch_K'],
        'stoch_d': latest['Stoch_D'],
        'prev_macd': prev['MACD'],
        'prev_macd_signal': prev['MACD_Signal'],
        'df': df
    }

def identify_setup(analysis):
    """Identify trade setups with STRICT TREND FILTERS - NO COUNTER-TREND TRADES"""
    if analysis is None:
        return None

    symbol = analysis['symbol']
    price = analysis['price']
    rsi = analysis['rsi']
    macd = analysis['macd']
    macd_signal = analysis['macd_signal']
    sma_50 = analysis['sma_50']
    sma_200 = analysis['sma_200']
    atr = analysis['atr']
    stoch_k = analysis['stoch_k']
    prev_macd = analysis['prev_macd']
    prev_macd_signal = analysis['prev_macd_signal']

    # CRITICAL: Determine market trend
    uptrend = price > sma_50 and sma_50 > sma_200
    downtrend = price < sma_50 and sma_50 < sma_200

    # MACD crossovers
    macd_bullish_cross = macd > macd_signal and prev_macd <= prev_macd_signal
    macd_bearish_cross = macd < macd_signal and prev_macd >= prev_macd_signal
    macd_bullish = macd > macd_signal
    macd_bearish = macd < macd_signal

    setups = []

    # === LONG SETUPS (ONLY IN UPTREND) ===
    if uptrend:
        confidence = 0
        reasons = []

        # Setup 1: MACD Bullish Crossover in Uptrend
        if macd_bullish_cross:
            confidence = 85
            reasons.append("MACD bullish crossover in uptrend")

        # Setup 2: Pullback in Uptrend
        elif macd_bullish and rsi < 60 and rsi > 40:
            confidence = 80
            reasons.append("Healthy pullback in uptrend (RSI 40-60)")

        # Setup 3: Oversold in Uptrend
        elif rsi < 35 and stoch_k < 25:
            confidence = 75
            reasons.append("Oversold pullback in uptrend")

        if confidence >= MIN_CONFIDENCE:
            setups.append({
                'type': 'LONG',
                'confidence': confidence,
                'reasons': reasons,
                'entry': price,
                'stop': price - (atr * ATR_STOP_MULTIPLIER),
                'target': price + (atr * ATR_TARGET_MULTIPLIER),
                'atr': atr,
                'trend': 'UPTREND'
            })

    # === SHORT SETUPS (ONLY IN DOWNTREND) ===
    elif downtrend:
        confidence = 0
        reasons = []

        # Setup 1: MACD Bearish Crossover in Downtrend
        if macd_bearish_cross:
            confidence = 85
            reasons.append("MACD bearish crossover in downtrend")

        # Setup 2: Pullback in Downtrend
        elif macd_bearish and rsi > 40 and rsi < 60:
            confidence = 80
            reasons.append("Pullback bounce in downtrend (RSI 40-60)")

        # Setup 3: Overbought in Downtrend
        elif rsi > 65 and stoch_k > 75:
            confidence = 75
            reasons.append("Overbought bounce in downtrend")

        if confidence >= MIN_CONFIDENCE:
            setups.append({
                'type': 'SHORT',
                'confidence': confidence,
                'reasons': reasons,
                'entry': price,
                'stop': price + (atr * ATR_STOP_MULTIPLIER),
                'target': price - (atr * ATR_TARGET_MULTIPLIER),
                'atr': atr,
                'trend': 'DOWNTREND'
            })

    return setups if setups else None

def calculate_position_size(account_balance, risk_per_trade, entry, stop_loss, symbol):
    """Calculate position size based on risk amount and stop distance"""
    risk_amount = account_balance * risk_per_trade
    stop_distance = abs(entry - stop_loss)

    # Get symbol info for pip value calculation
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return None

    # Calculate position size
    tick_value = symbol_info.trade_tick_value
    tick_size = symbol_info.trade_tick_size

    point_value = tick_value / tick_size if tick_size != 0 else 0
    stop_points = stop_distance / symbol_info.point

    if stop_points > 0 and point_value > 0:
        volume = risk_amount / (stop_points * point_value)

        # Round to lot step
        lot_step = symbol_info.volume_step
        volume = round(volume / lot_step) * lot_step

        # Apply min/max limits
        volume = max(symbol_info.volume_min, min(volume, symbol_info.volume_max))

        return volume
    return None

def execute_trade(symbol, setup, account_balance):
    """Execute trade with proper risk management"""
    # Calculate position size
    volume = calculate_position_size(
        account_balance,
        RISK_PER_TRADE,
        setup['entry'],
        setup['stop'],
        symbol
    )

    if volume is None or volume < mt5.symbol_info(symbol).volume_min:
        return {'success': False, 'error': 'Position size too small'}

    # Prepare order
    order_type = mt5.ORDER_TYPE_BUY if setup['type'] == 'LONG' else mt5.ORDER_TYPE_SELL
    price = setup['entry']

    # Get current bid/ask
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {'success': False, 'error': 'Cannot get tick data'}

    if order_type == mt5.ORDER_TYPE_BUY:
        price = tick.ask
    else:
        price = tick.bid

    # Create order request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": setup['stop'],
        "tp": setup['target'],
        "deviation": 20,
        "magic": 234000,
        "comment": f"Smart Scanner - {setup['reasons'][0][:50]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send order
    result = mt5.order_send(request)

    if result is None:
        return {'success': False, 'error': 'order_send failed'}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            'success': False,
            'error': f'Order failed: {result.retcode}',
            'retcode': result.retcode
        }

    return {
        'success': True,
        'ticket': result.order,
        'volume': volume,
        'price': result.price,
        'sl': setup['stop'],
        'tp': setup['target']
    }

print("="*100)
print("SMART SCANNER & AUTO-TRADER")
print("="*100)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Risk per trade: {RISK_PER_TRADE*100}%")
print(f"Max positions: {MAX_POSITIONS}")
print(f"Min confidence: {MIN_CONFIDENCE}%")
print(f"Stop multiplier: {ATR_STOP_MULTIPLIER}x ATR")
print(f"Target multiplier: {ATR_TARGET_MULTIPLIER}x ATR\n")

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

# Get account info
account = mt5.account_info()
positions = mt5.positions_get()
current_position_count = len(positions) if positions else 0

print(f"Account Balance: ${account.balance:,.2f}")
print(f"Current Positions: {current_position_count}/{MAX_POSITIONS}")

if current_position_count >= MAX_POSITIONS:
    print(f"\n[WARNING] Already at maximum position limit ({MAX_POSITIONS})")
    print("No new trades will be opened until positions are closed")

# All symbols to scan
SYMBOLS = [
    # Metals
    'GOLD', 'SILVER', 'XPDUSD', 'XPTUSD',
    # Forex Majors
    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD', 'USDCAD', 'USDCHF',
    # Forex Crosses
    'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'EURAUD',
    # Crypto
    'BTCUSD', 'ETHUSD', 'XRPUSD',
    # Indices
    'US100Cash', 'US500Cash', 'US30Cash', 'GER40Cash', 'UK100Cash',
    # Commodities
    'USOUSD', 'UKOUSD'
]

print(f"\n{'='*100}")
print(f"SCANNING {len(SYMBOLS)} SYMBOLS FOR SETUPS")
print(f"{'='*100}\n")

all_setups = []
scanned = 0
errors = 0

for symbol in SYMBOLS:
    # Check if symbol exists
    if not mt5.symbol_select(symbol, True):
        errors += 1
        continue

    analysis = get_technical_analysis(symbol)
    if analysis:
        setups = identify_setup(analysis)
        if setups:
            for setup in setups:
                all_setups.append({
                    'symbol': symbol,
                    'setup': setup,
                    'analysis': analysis
                })
            print(f"[SETUP] {symbol:12s} | {setup['type']:5s} | Confidence: {setup['confidence']}% | {setup['trend']}")
    scanned += 1

print(f"\nScanned: {scanned} symbols")
print(f"Errors: {errors} symbols")
print(f"Setups found: {len(all_setups)}")

# Sort by confidence
all_setups.sort(key=lambda x: x['setup']['confidence'], reverse=True)

# Execute trades
print(f"\n{'='*100}")
print("TRADE EXECUTION")
print(f"{'='*100}\n")

executed_trades = []
slots_available = MAX_POSITIONS - current_position_count

if slots_available <= 0:
    print("No slots available for new positions")
else:
    print(f"Available slots: {slots_available}\n")

    for i, item in enumerate(all_setups[:slots_available], 1):
        symbol = item['symbol']
        setup = item['setup']
        analysis = item['analysis']

        print(f"[{i}/{slots_available}] Executing {symbol} {setup['type']}...")
        print(f"  Confidence: {setup['confidence']}%")
        print(f"  Reasons: {', '.join(setup['reasons'])}")
        print(f"  Entry: {setup['entry']:.5f}")
        print(f"  Stop: {setup['stop']:.5f}")
        print(f"  Target: {setup['target']:.5f}")

        result = execute_trade(symbol, setup, account.balance)

        if result['success']:
            print(f"  [SUCCESS] Order #{result['ticket']} executed!")
            print(f"  Volume: {result['volume']} lots")
            print(f"  Fill Price: {result['price']:.5f}")

            executed_trades.append({
                'symbol': symbol,
                'type': setup['type'],
                'confidence': setup['confidence'],
                'reasons': setup['reasons'],
                'ticket': result['ticket'],
                'volume': result['volume'],
                'entry': result['price'],
                'stop': result['sl'],
                'target': result['tp'],
                'trend': setup['trend']
            })
        else:
            print(f"  [FAILED] {result['error']}")

        print()

print(f"{'='*100}")
print(f"EXECUTION SUMMARY: {len(executed_trades)} trades executed")
print(f"{'='*100}\n")

# Generate HTML report
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 30px 15px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat {{
            background: white;
            padding: 15px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }}
        .content {{
            padding: 30px;
        }}
        .trade-card {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }}
        .trade-card.short {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        }}
        .trade-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .symbol {{
            font-size: 20px;
            font-weight: 700;
        }}
        .confidence {{
            background: rgba(255,255,255,0.3);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 14px;
        }}
        .trade-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }}
        .detail {{
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 8px;
        }}
        .detail-label {{
            font-size: 10px;
            opacity: 0.8;
            margin-bottom: 4px;
        }}
        .detail-value {{
            font-size: 14px;
            font-weight: 600;
        }}
        .no-trades {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SMART SCANNER EXECUTION REPORT</h1>
            <div style="opacity: 0.9; margin-top: 10px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-label">Symbols Scanned</div>
                <div class="stat-value">{scanned}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Setups Found</div>
                <div class="stat-value">{len(all_setups)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Trades Executed</div>
                <div class="stat-value">{len(executed_trades)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Risk Per Trade</div>
                <div class="stat-value">{RISK_PER_TRADE*100}%</div>
            </div>
        </div>

        <div class="content">
            <h2 style="color: #333; margin-bottom: 20px;">Executed Trades</h2>
"""

if executed_trades:
    for trade in executed_trades:
        card_class = "short" if trade['type'] == 'SHORT' else ""
        rr_ratio = abs(trade['target'] - trade['entry']) / abs(trade['entry'] - trade['stop'])

        html += f"""
            <div class="trade-card {card_class}">
                <div class="trade-header">
                    <div>
                        <span class="symbol">{trade['symbol']}</span>
                        <span style="margin-left: 15px; font-size: 18px;">{trade['type']}</span>
                    </div>
                    <div class="confidence">{trade['confidence']}% Confidence</div>
                </div>
                <div style="margin-bottom: 10px;">
                    {' | '.join(trade['reasons'])}
                </div>
                <div style="font-size: 13px; opacity: 0.9; margin-bottom: 10px;">
                    Order #{trade['ticket']} | {trade['volume']} lots | Trend: {trade['trend']}
                </div>
                <div class="trade-details">
                    <div class="detail">
                        <div class="detail-label">Entry</div>
                        <div class="detail-value">{trade['entry']:.5f}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Stop Loss</div>
                        <div class="detail-value">{trade['stop']:.5f}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Take Profit</div>
                        <div class="detail-value">{trade['target']:.5f}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Risk/Reward</div>
                        <div class="detail-value">1:{rr_ratio:.2f}</div>
                    </div>
                </div>
            </div>
"""
else:
    html += """
            <div class="no-trades">
                <h3>No trades executed this scan</h3>
                <p>Either no high-confidence setups found, or position limit reached</p>
            </div>
"""

html += """
        </div>
    </div>
</body>
</html>
"""

print("Sending execution report to email...")
if send_email("SMART SCANNER - Trade Execution Report", html):
    print("[SUCCESS] Report sent!")
else:
    print("[FAILED] Email not sent")

mt5.shutdown()
print("\n[DONE]")
