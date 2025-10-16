"""
PROFESSIONAL MARKET SCAN - Beautiful HTML Email Report
Scans all markets and sends professionally formatted email
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

# EmailJS Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

# Symbol list
SYMBOLS = {
    'Precious Metals': ['GOLD', 'SILVER', 'XPTUSD', 'XPDUSD', 'COPPER'],
    'Forex Majors': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD'],
    'Forex Minors': ['EURJPY', 'GBPJPY', 'EURGBP', 'EURAUD', 'EURCHF', 'EURCAD', 'EURNZD',
                     'GBPAUD', 'GBPCHF', 'GBPCAD', 'GBPNZD', 'AUDJPY', 'AUDCHF', 'AUDCAD',
                     'AUDNZD', 'NZDJPY', 'NZDCHF', 'NZDCAD', 'CADJPY', 'CADCHF', 'CHFJPY'],
    'Exotic Forex': ['USDMXN', 'USDZAR', 'USDTRY', 'USDSEK', 'USDNOK', 'USDDKK', 'USDPLN',
                     'USDHUF', 'USDCZK', 'USDSGD', 'USDHKD', 'EURPLN', 'EURTRY', 'EURSEK',
                     'EURNOK', 'GBPSEK', 'GBPNOK', 'GBPPLN'],
    'Crypto': ['BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD', 'BCHUSD', 'ADAUSD', 'DOGEUSD',
               'SOLUSD', 'DOTUSD', 'MATICUSD', 'BNBUSD']
}

TIMEFRAME = mt5.TIMEFRAME_H1

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

def calculate_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

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

        # ATR for volatility
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        # Price momentum
        price_change_24h = ((close.iloc[-1] / close.iloc[-24]) - 1) * 100 if len(close) >= 24 else 0
        price_change_7d = ((close.iloc[-1] / close.iloc[-168]) - 1) * 100 if len(close) >= 168 else 0

        volatility = (atr.iloc[-1] / close.iloc[-1]) * 100

        signals = []
        score = 0

        # EMA Crossover (recent 3 bars)
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
            trend_strength = ((ema25.iloc[-1] / ema100.iloc[-1]) - 1) * 100
        else:
            trend = "Downtrend"
            trend_strength = ((ema100.iloc[-1] / ema25.iloc[-1]) - 1) * 100

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
            'trend_strength': trend_strength,
            'volatility': volatility,
            'signals': signals,
            'score': score,
            'ema25': ema25.iloc[-1],
            'ema100': ema100.iloc[-1]
        }

    except Exception as e:
        return None

def format_html_email(opportunities, all_data):
    """Format beautiful HTML email"""
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
            max-width: 900px;
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
        .stats-bar {{
            display: flex;
            background-color: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stat {{
            flex: 1;
            padding: 20px;
            text-align: center;
            border-right: 1px solid #e0e0e0;
        }}
        .stat:last-child {{
            border-right: none;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 22px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .opportunity-card {{
            background: #fff;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: transform 0.2s;
        }}
        .opportunity-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .opp-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .opp-symbol {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .opp-category {{
            font-size: 12px;
            color: #666;
            background: #f0f0f0;
            padding: 4px 12px;
            border-radius: 12px;
        }}
        .opp-score {{
            font-size: 20px;
            font-weight: bold;
            color: white;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 8px 16px;
            border-radius: 20px;
        }}
        .opp-metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 15px;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 6px;
        }}
        .metric-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }}
        .positive {{ color: #10b981; }}
        .negative {{ color: #ef4444; }}
        .signals {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .signal-badge {{
            background: #667eea;
            color: white;
            padding: 6px 14px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .table th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            border-bottom: 2px solid #e0e0e0;
        }}
        .table td {{
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 14px;
        }}
        .table tr:hover {{
            background: #f8f9fa;
        }}
        .trend-up {{ color: #10b981; }}
        .trend-down {{ color: #ef4444; }}
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
            <h1>Market Scan Report</h1>
            <p>{now.strftime('%A, %B %d, %Y - %I:%M %p')}</p>
        </div>

        <div class="stats-bar">
            <div class="stat">
                <div class="stat-value">{len(all_data)}</div>
                <div class="stat-label">Instruments Scanned</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(opportunities)}</div>
                <div class="stat-label">Opportunities Found</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(SYMBOLS)}</div>
                <div class="stat-label">Asset Classes</div>
            </div>
        </div>

        <div class="content">
"""

    # High Priority Opportunities
    if opportunities:
        html += """
            <div class="section">
                <div class="section-title">🎯 High Priority Opportunities</div>
"""
        for opp in opportunities[:10]:
            price_change_color = 'positive' if opp['change_24h'] > 0 else 'negative'
            trend_color = 'trend-up' if opp['trend'] == 'Uptrend' else 'trend-down'

            html += f"""
                <div class="opportunity-card">
                    <div class="opp-header">
                        <div>
                            <div class="opp-symbol">{opp['symbol']}</div>
                            <div class="opp-category">{opp['category']}</div>
                        </div>
                        <div class="opp-score">Score: {opp['score']}/10</div>
                    </div>

                    <div class="opp-metrics">
                        <div class="metric">
                            <div class="metric-label">Current Price</div>
                            <div class="metric-value">${opp['price']:.6f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">24H Change</div>
                            <div class="metric-value {price_change_color}">{opp['change_24h']:+.2f}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">RSI (28)</div>
                            <div class="metric-value">{opp['rsi']:.1f}</div>
                        </div>
                    </div>

                    <div class="opp-metrics">
                        <div class="metric">
                            <div class="metric-label">Trend</div>
                            <div class="metric-value {trend_color}">{opp['trend']}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">7D Change</div>
                            <div class="metric-value {price_change_color}">{opp['change_7d']:+.2f}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Volatility</div>
                            <div class="metric-value">{opp['volatility']:.2f}%</div>
                        </div>
                    </div>

                    <div class="signals">
"""
            for signal in opp['signals']:
                html += f'<span class="signal-badge">{signal}</span>'

            html += """
                    </div>
                </div>
"""

        if len(opportunities) > 10:
            html += f"<p style='text-align:center; color:#666;'>... and {len(opportunities) - 10} more opportunities</p>"

        html += "</div>"

    # Top Movers
    valid_data = [d for d in all_data if d]
    if valid_data:
        html += """
            <div class="section">
                <div class="section-title">📊 Top Market Movers (24H)</div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Symbol</th>
                            <th>Category</th>
                            <th>Price</th>
                            <th>24H Change</th>
                            <th>RSI</th>
                        </tr>
                    </thead>
                    <tbody>
"""

        sorted_by_change = sorted(valid_data, key=lambda x: abs(x['change_24h']), reverse=True)[:10]
        for i, data in enumerate(sorted_by_change, 1):
            change_class = 'positive' if data['change_24h'] > 0 else 'negative'
            html += f"""
                        <tr>
                            <td><strong>#{i}</strong></td>
                            <td><strong>{data['symbol']}</strong></td>
                            <td>{data['category']}</td>
                            <td>${data['price']:.6f}</td>
                            <td class="{change_class}"><strong>{data['change_24h']:+.2f}%</strong></td>
                            <td>{data['rsi']:.1f}</td>
                        </tr>
"""

        html += """
                    </tbody>
                </table>
            </div>
"""

    # Market Overview by Category
    html += """
            <div class="section">
                <div class="section-title">🌍 Market Overview by Category</div>
"""

    for category, symbols in SYMBOLS.items():
        category_data = [d for d in all_data if d and d['category'] == category]
        if category_data:
            avg_change = sum(d['change_24h'] for d in category_data) / len(category_data)
            avg_rsi = sum(d['rsi'] for d in category_data) / len(category_data)

            html += f"""
                <div style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:15px;">
                    <h3 style="margin:0 0 10px 0; color:#333;">{category} ({len(category_data)} instruments)</h3>
                    <div style="display:flex; gap:20px; margin-bottom:10px;">
                        <div>
                            <span style="font-size:12px; color:#666;">Avg 24H Change:</span>
                            <span style="font-size:16px; font-weight:600; color:{'#10b981' if avg_change > 0 else '#ef4444'};"> {avg_change:+.2f}%</span>
                        </div>
                        <div>
                            <span style="font-size:12px; color:#666;">Avg RSI:</span>
                            <span style="font-size:16px; font-weight:600; color:#333;"> {avg_rsi:.1f}</span>
                        </div>
                    </div>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Price</th>
                                <th>24H</th>
                                <th>RSI</th>
                                <th>Trend</th>
                            </tr>
                        </thead>
                        <tbody>
"""

            for data in sorted(category_data, key=lambda x: abs(x['change_24h']), reverse=True)[:5]:
                change_class = 'positive' if data['change_24h'] > 0 else 'negative'
                trend_class = 'trend-up' if data['trend'] == 'Uptrend' else 'trend-down'
                html += f"""
                            <tr>
                                <td><strong>{data['symbol']}</strong></td>
                                <td>${data['price']:.6f}</td>
                                <td class="{change_class}">{data['change_24h']:+.2f}%</td>
                                <td>{data['rsi']:.0f}</td>
                                <td class="{trend_class}">{data['trend']}</td>
                            </tr>
"""

            html += """
                        </tbody>
                    </table>
                </div>
"""

    html += """
        </div>

        <div class="footer">
            <p><strong>Disclaimer:</strong> This report is for informational purposes only. Not financial advice.</p>
            <p>Generated by PropShop Trading System | Powered by MetaTrader 5</p>
            <p>Next scan: Run manually or wait for hourly alert system</p>
        </div>
    </div>
</body>
</html>
"""

    return html

# Initialize MT5
print("="*80)
print("PROFESSIONAL MARKET SCAN - HTML EMAIL")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

all_data = []
total_symbols = sum(len(syms) for syms in SYMBOLS.values())
current = 0

print(f"\nScanning {total_symbols} symbols across {len(SYMBOLS)} categories...\n")

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

# Filter opportunities
opportunities = [d for d in all_data if d and d['score'] >= 2]
opportunities.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'='*80}")
print(f"SCAN COMPLETE")
print(f"{'='*80}")
print(f"Symbols scanned: {len(all_data)}")
print(f"Opportunities found: {len(opportunities)}")

# Format and send HTML email
subject = f"Market Report: {len(opportunities)} Opportunities | {len(all_data)} Instruments"
html_message = format_html_email(opportunities, all_data)

print(f"\nSending professional HTML email to {EMAIL_TO}...")
send_email(subject, html_message)

print("\n[DONE] Check your email!")

mt5.shutdown()
