"""
ADVANCED TRADING INTELLIGENCE SYSTEM
- Generates charts for each opportunity
- Provides complete trade setup (entry, SL, TP, R:R)
- Sends beautiful HTML email with embedded charts
- Tracks decisions and performance
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import mplfinance as mpf
from io import BytesIO
import base64
import json
import os

# EmailJS Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

# Symbol list - Focus on liquid markets
SYMBOLS = {
    'Precious Metals': ['GOLD', 'SILVER', 'XPTUSD', 'XPDUSD'],
    'Forex Majors': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD'],
    'Forex Minors': ['EURJPY', 'GBPJPY', 'EURGBP', 'EURAUD', 'EURCHF', 'EURCAD', 'GBPAUD',
                     'GBPCHF', 'GBPCAD', 'AUDJPY', 'AUDNZD', 'NZDJPY', 'CADJPY', 'CHFJPY'],
    'Exotic Forex': ['USDMXN', 'USDZAR', 'USDSEK', 'USDNOK', 'USDDKK', 'USDPLN', 'USDHUF'],
    'Crypto': ['BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD', 'ADAUSD', 'DOGEUSD', 'SOLUSD']
}

TIMEFRAME = mt5.TIMEFRAME_H1
TRADES_LOG_FILE = "trades_log.json"

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
    atr = tr.rolling(period).mean()
    return atr

def generate_trade_setup(symbol, df, signals, score):
    """Generate complete trade setup with entry, SL, TP, R:R"""
    close = df['close']
    high = df['high']
    low = df['low']

    current_price = close.iloc[-1]
    atr = calculate_atr(high, low, close, 14).iloc[-1]

    # Determine trade direction based on signals
    direction = None
    if any('Bullish' in s or 'Oversold' in s or 'Breakout Above' in s for s in signals):
        direction = "LONG"
    elif any('Bearish' in s or 'Overbought' in s or 'Breakdown Below' in s for s in signals):
        direction = "SHORT"

    if not direction:
        return None

    # Calculate position sizing based on risk
    risk_percent = 1.0  # Risk 1% per trade

    if direction == "LONG":
        entry = current_price
        stop_loss = entry - (1.5 * atr)  # 1.5 ATR stop loss
        take_profit_1 = entry + (2 * atr)  # 2:1 R:R
        take_profit_2 = entry + (3 * atr)  # 3:1 R:R
        take_profit_3 = entry + (4.5 * atr)  # 4.5:1 R:R
    else:  # SHORT
        entry = current_price
        stop_loss = entry + (1.5 * atr)
        take_profit_1 = entry - (2 * atr)
        take_profit_2 = entry - (3 * atr)
        take_profit_3 = entry - (4.5 * atr)

    risk_amount = abs(entry - stop_loss)

    return {
        'direction': direction,
        'entry': entry,
        'stop_loss': stop_loss,
        'tp1': take_profit_1,
        'tp2': take_profit_2,
        'tp3': take_profit_3,
        'risk_amount': risk_amount,
        'reward_1': abs(take_profit_1 - entry),
        'reward_2': abs(take_profit_2 - entry),
        'reward_3': abs(take_profit_3 - entry),
        'rr1': abs(take_profit_1 - entry) / risk_amount,
        'rr2': abs(take_profit_2 - entry) / risk_amount,
        'rr3': abs(take_profit_3 - entry) / risk_amount,
        'atr': atr,
        'risk_percent': risk_percent
    }

def generate_chart(symbol, df, trade_setup, signals):
    """Generate trading chart with indicators and levels"""
    # Prepare data
    df_chart = df.copy()
    df_chart['time'] = pd.to_datetime(df_chart['time'], unit='s')
    df_chart.set_index('time', inplace=True)
    df_chart = df_chart[['open', 'high', 'low', 'close', 'tick_volume']]

    # Take last 100 bars for clarity
    df_chart = df_chart.iloc[-100:]

    close = df_chart['close']

    # Calculate indicators
    ema25 = calculate_ema(close, 25)
    ema100 = calculate_ema(close, 100)
    rsi = calculate_rsi(close, 28)

    # Create additional plots
    apds = []

    # EMA lines
    apds.append(mpf.make_addplot(ema25, color='blue', width=1.5, label='EMA 25'))
    apds.append(mpf.make_addplot(ema100, color='red', width=1.5, label='EMA 100'))

    # Trade levels
    if trade_setup:
        entry_line = [trade_setup['entry']] * len(df_chart)
        sl_line = [trade_setup['stop_loss']] * len(df_chart)
        tp1_line = [trade_setup['tp1']] * len(df_chart)

        apds.append(mpf.make_addplot(entry_line, color='yellow', width=2, linestyle='--', label='Entry'))
        apds.append(mpf.make_addplot(sl_line, color='red', width=2, linestyle='--', label='Stop Loss'))
        apds.append(mpf.make_addplot(tp1_line, color='green', width=2, linestyle='--', label='TP1'))

    # Create figure
    fig, axes = mpf.plot(
        df_chart,
        type='candle',
        style='charles',
        addplot=apds,
        volume=False,
        title=f'{symbol} - H1 Chart',
        ylabel='Price',
        figsize=(12, 8),
        returnfig=True,
        tight_layout=True
    )

    # Add RSI subplot
    ax_rsi = fig.add_subplot(4, 1, 4)
    ax_rsi.plot(df_chart.index, rsi, color='purple', linewidth=1.5)
    ax_rsi.axhline(80, color='red', linestyle='--', alpha=0.5)
    ax_rsi.axhline(35, color='green', linestyle='--', alpha=0.5)
    ax_rsi.axhline(50, color='gray', linestyle='--', alpha=0.3)
    ax_rsi.set_ylabel('RSI (28)')
    ax_rsi.set_ylim(0, 100)
    ax_rsi.grid(True, alpha=0.3)

    # Convert to base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close(fig)

    return image_base64

def check_symbol(symbol, category):
    """Comprehensive check for one symbol"""
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

        current_price = close.iloc[-1]

        # Calculate indicators
        ema25 = calculate_ema(close, 25)
        ema100 = calculate_ema(close, 100)
        rsi = calculate_rsi(close, 28)

        # Donchian channels
        upper_channel = high.rolling(50).max()
        lower_channel = low.rolling(50).min()

        # Price momentum
        price_change_24h = ((close.iloc[-1] / close.iloc[-24]) - 1) * 100 if len(close) >= 24 else 0
        price_change_7d = ((close.iloc[-1] / close.iloc[-168]) - 1) * 100 if len(close) >= 168 else 0

        atr = calculate_atr(high, low, close, 14)
        volatility = (atr.iloc[-1] / close.iloc[-1]) * 100

        signals = []
        score = 0

        # EMA Crossover
        for i in range(-3, 0):
            if ema25.iloc[i-1] <= ema100.iloc[i-1] and ema25.iloc[i] > ema100.iloc[i]:
                signals.append("EMA Bullish Cross")
                score += 3
                break
            elif ema25.iloc[i-1] >= ema100.iloc[i-1] and ema25.iloc[i] < ema100.iloc[i]:
                signals.append("EMA Bearish Cross")
                score += 3
                break

        # RSI extremes
        current_rsi = rsi.iloc[-1]
        if current_rsi < 35:
            signals.append(f"RSI Oversold ({current_rsi:.1f})")
            score += 2 if current_rsi < 30 else 1
        elif current_rsi > 80:
            signals.append(f"RSI Overbought ({current_rsi:.1f})")
            score += 2 if current_rsi > 85 else 1

        # Donchian breakout
        if close.iloc[-1] > upper_channel.iloc[-2] and close.iloc[-2] <= upper_channel.iloc[-3]:
            signals.append("Breakout Above 50H High")
            score += 3
        elif close.iloc[-1] < lower_channel.iloc[-2] and close.iloc[-2] >= lower_channel.iloc[-3]:
            signals.append("Breakdown Below 50H Low")
            score += 3

        # Trend
        if ema25.iloc[-1] > ema100.iloc[-1]:
            trend = "Uptrend"
        else:
            trend = "Downtrend"

        # High momentum
        if abs(price_change_24h) > 2:
            signals.append(f"High Momentum ({price_change_24h:+.1f}%)")
            score += 1

        return {
            'symbol': symbol,
            'category': category,
            'price': current_price,
            'change_24h': price_change_24h,
            'change_7d': price_change_7d,
            'rsi': current_rsi,
            'trend': trend,
            'volatility': volatility,
            'signals': signals,
            'score': score,
            'df': df
        }

    except Exception as e:
        return None

def save_trade_log(opportunities):
    """Save trade recommendations to log file"""
    if os.path.exists(TRADES_LOG_FILE):
        with open(TRADES_LOG_FILE, 'r') as f:
            logs = json.load(f)
    else:
        logs = []

    for opp in opportunities:
        if opp.get('trade_setup'):
            logs.append({
                'timestamp': datetime.now().isoformat(),
                'symbol': opp['symbol'],
                'direction': opp['trade_setup']['direction'],
                'entry': opp['trade_setup']['entry'],
                'stop_loss': opp['trade_setup']['stop_loss'],
                'tp1': opp['trade_setup']['tp1'],
                'tp2': opp['trade_setup']['tp2'],
                'tp3': opp['trade_setup']['tp3'],
                'rr1': opp['trade_setup']['rr1'],
                'signals': opp['signals'],
                'score': opp['score'],
                'status': 'PENDING'
            })

    with open(TRADES_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def format_html_email(opportunities):
    """Format beautiful HTML email with charts and trade setups"""
    now = datetime.now()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 32px;
            font-weight: 600;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 16px;
        }}
        .content {{
            padding: 30px;
        }}
        .opportunity {{
            background: white;
            border: 3px solid #667eea;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        .opp-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .opp-symbol {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .opp-score {{
            font-size: 20px;
            font-weight: bold;
            color: white;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 10px 20px;
            border-radius: 20px;
        }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .trade-setup {{
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .trade-direction {{
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .long {{ background: linear-gradient(135deg, #34d399 0%, #10b981 100%); color: white; }}
        .short {{ background: linear-gradient(135deg, #f87171 0%, #ef4444 100%); color: white; }}
        .trade-levels {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .level-box {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #667eea;
        }}
        .level-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .level-value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }}
        .entry-box {{ border-left-color: #fbbf24; }}
        .sl-box {{ border-left-color: #ef4444; }}
        .tp-box {{ border-left-color: #10b981; }}
        .rr-box {{ border-left-color: #667eea; }}
        .signals {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 15px 0;
        }}
        .signal-badge {{
            background: #667eea;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }}
        .risk-warning {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .action-btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            margin: 10px 5px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Trading Intelligence Report</h1>
            <p>{now.strftime('%A, %B %d, %Y - %I:%M %p')}</p>
            <p>{len(opportunities)} High-Probability Setups Identified</p>
        </div>

        <div class="content">
"""

    if opportunities:
        for i, opp in enumerate(opportunities, 1):
            trade = opp.get('trade_setup')
            if not trade:
                continue

            direction_class = 'long' if trade['direction'] == 'LONG' else 'short'

            html += f"""
            <div class="opportunity">
                <div class="opp-header">
                    <div>
                        <div class="opp-symbol">#{i} {opp['symbol']}</div>
                        <div style="color:#666; font-size:14px;">{opp['category']}</div>
                    </div>
                    <div class="opp-score">Score: {opp['score']}/10</div>
                </div>

                <div class="signals">
"""
            for signal in opp['signals']:
                html += f'<span class="signal-badge">{signal}</span>'

            html += f"""
                </div>

                <div class="chart-container">
                    <img src="data:image/png;base64,{opp['chart']}" alt="{opp['symbol']} Chart">
                </div>

                <div class="trade-setup">
                    <div class="trade-direction {direction_class}">
                        {trade['direction']} SETUP
                    </div>

                    <div class="trade-levels">
                        <div class="level-box entry-box">
                            <div class="level-label">Entry Price</div>
                            <div class="level-value">${trade['entry']:.5f}</div>
                        </div>
                        <div class="level-box sl-box">
                            <div class="level-label">Stop Loss</div>
                            <div class="level-value">${trade['stop_loss']:.5f}</div>
                        </div>
                        <div class="level-box tp-box">
                            <div class="level-label">Take Profit 1 (50%)</div>
                            <div class="level-value">${trade['tp1']:.5f}</div>
                        </div>
                        <div class="level-box tp-box">
                            <div class="level-label">Take Profit 2 (30%)</div>
                            <div class="level-value">${trade['tp2']:.5f}</div>
                        </div>
                        <div class="level-box tp-box">
                            <div class="level-label">Take Profit 3 (20%)</div>
                            <div class="level-value">${trade['tp3']:.5f}</div>
                        </div>
                        <div class="level-box rr-box">
                            <div class="level-label">Risk:Reward</div>
                            <div class="level-value">
                                1:{trade['rr1']:.1f} / 1:{trade['rr2']:.1f} / 1:{trade['rr3']:.1f}
                            </div>
                        </div>
                    </div>

                    <div class="risk-warning">
                        <strong>Risk Management:</strong><br>
                        - Risk per trade: {trade['risk_percent']}% of account<br>
                        - ATR: {trade['atr']:.5f}<br>
                        - Move SL to breakeven after TP1 hit<br>
                        - Consider partial profits at each TP level
                    </div>
                </div>
            </div>
"""

    html += """
        </div>

        <div class="footer">
            <p><strong>Important:</strong> These are algorithmic recommendations based on technical analysis.</p>
            <p>Always perform your own analysis and manage risk appropriately.</p>
            <p>Past performance does not guarantee future results.</p>
            <p><strong>Reply to this email with your trading decisions for performance tracking!</strong></p>
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
            <p>Generated by PropShop Trading Intelligence System | Powered by MetaTrader 5</p>
        </div>
    </div>
</body>
</html>
"""

    return html

def send_email(subject, html_message):
    """Send HTML email via EmailJS"""
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
        if response.status_code == 200:
            print(f"[OK] Email sent: {subject}")
            return True
        else:
            print(f"[FAIL] Email failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Email error: {str(e)}")
        return False

# Main execution
print("="*80)
print("ADVANCED TRADING INTELLIGENCE SYSTEM")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

all_data = []
total_symbols = sum(len(syms) for syms in SYMBOLS.values())
current = 0

print(f"\nScanning {total_symbols} symbols...\n")

for category, symbol_list in SYMBOLS.items():
    print(f"{category}:")
    for symbol in symbol_list:
        current += 1
        print(f"  [{current}/{total_symbols}] {symbol:12s}...", end=" ")
        result = check_symbol(symbol, category)
        if result:
            all_data.append(result)
            if result['signals']:
                print(f"[SCORE {result['score']}]")
            else:
                print("[OK]")
        else:
            print("[SKIP]")

# Filter opportunities (score >= 2)
opportunities = [d for d in all_data if d and d['score'] >= 2]
opportunities.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'='*80}")
print(f"Found {len(opportunities)} opportunities")
print(f"{'='*80}")

# Generate charts and trade setups
print("\nGenerating charts and trade setups...\n")
for i, opp in enumerate(opportunities, 1):
    print(f"  [{i}/{len(opportunities)}] {opp['symbol']}...", end=" ")

    # Generate trade setup
    trade_setup = generate_trade_setup(opp['symbol'], opp['df'], opp['signals'], opp['score'])
    opp['trade_setup'] = trade_setup

    if trade_setup:
        # Generate chart
        chart_base64 = generate_chart(opp['symbol'], opp['df'], trade_setup, opp['signals'])
        opp['chart'] = chart_base64
        print(f"[{trade_setup['direction']} @ ${trade_setup['entry']:.5f}, R:R 1:{trade_setup['rr1']:.1f}]")
    else:
        print("[NO SETUP]")

# Filter only opportunities with valid trade setups
opportunities = [o for o in opportunities if o.get('trade_setup')]

print(f"\n{'='*80}")
print(f"{len(opportunities)} complete trade setups generated")
print(f"{'='*80}")

if opportunities:
    # Save to log
    save_trade_log(opportunities)
    print(f"\n[OK] Saved to {TRADES_LOG_FILE}")

    # Send email
    subject = f"Trading Intelligence: {len(opportunities)} High-Probability Setups with Charts"
    html_message = format_html_email(opportunities)

    print(f"\nSending email to {EMAIL_TO}...")
    send_email(subject, html_message)

    print("\n[DONE] Check your email!")
    print("\nNext steps:")
    print("1. Review each trade setup and chart")
    print("2. Decide which trades to take")
    print("3. Reply to the email with your decisions")
    print("4. I'll track performance and send follow-up reports")
else:
    print("\n[INFO] No high-probability setups at this time")

mt5.shutdown()
