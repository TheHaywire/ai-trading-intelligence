"""
QUANTITATIVE OPPORTUNITIES SCANNER
Beautiful, readable format showing trade opportunities
Like reports from Renaissance Technologies, Citadel
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

# Symbols to scan
SYMBOLS = ['GOLD', 'SILVER', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD', 'USDCAD',
           'EURGBP', 'EURJPY', 'GBPJPY', 'BTCUSD', 'ETHUSD', 'XRPUSD', 'LTCUSD']

TIMEFRAME = mt5.TIMEFRAME_H1

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

def scan_symbol(symbol):
    """Scan symbol for opportunities"""
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

        # Price momentum
        momentum_24h = ((close.iloc[-1] / close.iloc[-24]) - 1) * 100 if len(close) >= 24 else 0

        opportunities = []

        # Strategy 1: EMA Bullish Cross
        if ema25.iloc[-1] > ema100.iloc[-1] and ema25.iloc[-2] <= ema100.iloc[-2]:
            opportunities.append({
                'strategy': 'EMA Crossover',
                'direction': 'LONG',
                'signal': 'Bullish Cross',
                'entry': current_price,
                'sl': current_price - (1.5 * current_atr),
                'tp': current_price + (3 * current_atr),
                'confidence': 75,
                'rr_ratio': 2.0,
                'timeframe': '1H',
                'trigger': 'EMA25 crossed above EMA100'
            })

        # Strategy 2: EMA Bearish Cross
        elif ema25.iloc[-1] < ema100.iloc[-1] and ema25.iloc[-2] >= ema100.iloc[-2]:
            opportunities.append({
                'strategy': 'EMA Crossover',
                'direction': 'SHORT',
                'signal': 'Bearish Cross',
                'entry': current_price,
                'sl': current_price + (1.5 * current_atr),
                'tp': current_price - (3 * current_atr),
                'confidence': 75,
                'rr_ratio': 2.0,
                'timeframe': '1H',
                'trigger': 'EMA25 crossed below EMA100'
            })

        # Strategy 3: RSI Oversold with Trend
        if current_rsi < 35 and ema25.iloc[-1] > ema100.iloc[-1]:
            confidence = 85 if current_rsi < 30 else 70
            opportunities.append({
                'strategy': 'RSI Mean Reversion',
                'direction': 'LONG',
                'signal': 'Oversold in Uptrend',
                'entry': current_price,
                'sl': current_price - (1.5 * current_atr),
                'tp': current_price + (3 * current_atr),
                'confidence': confidence,
                'rr_ratio': 2.0,
                'timeframe': '1H',
                'trigger': f'RSI at {current_rsi:.1f} (oversold) + uptrend'
            })

        # Strategy 4: RSI Overbought with Trend
        elif current_rsi > 80 and ema25.iloc[-1] < ema100.iloc[-1]:
            confidence = 85 if current_rsi > 85 else 70
            opportunities.append({
                'strategy': 'RSI Mean Reversion',
                'direction': 'SHORT',
                'signal': 'Overbought in Downtrend',
                'entry': current_price,
                'sl': current_price + (1.5 * current_atr),
                'tp': current_price - (3 * current_atr),
                'confidence': confidence,
                'rr_ratio': 2.0,
                'timeframe': '1H',
                'trigger': f'RSI at {current_rsi:.1f} (overbought) + downtrend'
            })

        # Strategy 5: Donchian Breakout
        if close.iloc[-1] > upper_channel.iloc[-2] and close.iloc[-2] <= upper_channel.iloc[-3]:
            if ema25.iloc[-1] > ema100.iloc[-1]:
                opportunities.append({
                    'strategy': 'Donchian Breakout',
                    'direction': 'LONG',
                    'signal': 'Breakout',
                    'entry': current_price,
                    'sl': current_price - (1.5 * current_atr),
                    'tp': current_price + (3 * current_atr),
                    'confidence': 80,
                    'rr_ratio': 2.0,
                    'timeframe': '1H',
                    'trigger': 'Price broke above 50-period high'
                })

        # Strategy 6: Donchian Breakdown
        elif close.iloc[-1] < lower_channel.iloc[-2] and close.iloc[-2] >= lower_channel.iloc[-3]:
            if ema25.iloc[-1] < ema100.iloc[-1]:
                opportunities.append({
                    'strategy': 'Donchian Breakout',
                    'direction': 'SHORT',
                    'signal': 'Breakdown',
                    'entry': current_price,
                    'sl': current_price + (1.5 * current_atr),
                    'tp': current_price - (3 * current_atr),
                    'confidence': 80,
                    'rr_ratio': 2.0,
                    'timeframe': '1H',
                    'trigger': 'Price broke below 50-period low'
                })

        # Add symbol data to each opportunity
        for opp in opportunities:
            opp['symbol'] = symbol
            opp['current_price'] = current_price
            opp['rsi'] = current_rsi
            opp['momentum_24h'] = momentum_24h
            opp['volatility'] = (current_atr / current_price) * 100

        return opportunities

    except Exception as e:
        print(f"    [ERROR] {symbol}: {str(e)}")
        return []

def format_opportunities_email(all_opportunities):
    """Format beautiful opportunities email"""
    now = datetime.now()

    # Sort by confidence
    all_opportunities.sort(key=lambda x: x['confidence'], reverse=True)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            line-height: 1.6;
        }}

        .email-wrapper {{
            max-width: 680px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 50px 40px;
            text-align: center;
            color: white;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}

        .header .subtitle {{
            font-size: 16px;
            opacity: 0.95;
            font-weight: 400;
        }}

        .stats-bar {{
            display: flex;
            justify-content: space-around;
            background: white;
            margin: -30px 20px 0 20px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.25);
            padding: 25px;
        }}

        .stat {{
            text-align: center;
        }}

        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
        }}

        .stat-label {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }}

        .content {{
            padding: 50px 40px;
        }}

        .opportunity-card {{
            background: #ffffff;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}

        .opportunity-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.1);
            border-color: #667eea;
        }}

        .opp-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid #f3f4f6;
        }}

        .opp-symbol {{
            font-size: 24px;
            font-weight: 700;
            color: #1a1a1a;
        }}

        .opp-direction {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
        }}

        .long {{
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            color: #065f46;
        }}

        .short {{
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            color: #991b1b;
        }}

        .opp-strategy {{
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 12px;
        }}

        .opp-trigger {{
            background: #f3f4f6;
            padding: 12px;
            border-radius: 8px;
            font-size: 13px;
            color: #374151;
            margin-bottom: 16px;
        }}

        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }}

        .metric-box {{
            background: #f9fafb;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }}

        .metric-label {{
            font-size: 11px;
            color: #6b7280;
            margin-bottom: 4px;
        }}

        .metric-value {{
            font-size: 18px;
            font-weight: 700;
            color: #1a1a1a;
        }}

        .trade-levels {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}

        .level-box {{
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }}

        .level-box.entry {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        }}

        .level-box.sl {{
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        }}

        .level-box.tp {{
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        }}

        .level-label {{
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .level-value {{
            font-size: 16px;
            font-weight: 700;
        }}

        .confidence-bar {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #f3f4f6;
        }}

        .confidence-label {{
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 8px;
        }}

        .confidence-progress {{
            height: 8px;
            background: #f3f4f6;
            border-radius: 4px;
            overflow: hidden;
        }}

        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px;
        }}

        .no-opportunities {{
            text-align: center;
            padding: 60px 40px;
        }}

        .no-opportunities-icon {{
            font-size: 48px;
            margin-bottom: 16px;
        }}

        .no-opportunities-text {{
            font-size: 18px;
            color: #6b7280;
        }}

        .footer {{
            background: #f9fafb;
            padding: 30px 40px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}

        .footer-text {{
            font-size: 12px;
            color: #9ca3af;
            line-height: 1.8;
        }}

        .footer-brand {{
            font-weight: 600;
            color: #667eea;
            margin-top: 8px;
        }}

        @media (max-width: 600px) {{
            .stats-bar {{
                flex-direction: column;
                gap: 20px;
            }}

            .metrics-row {{
                grid-template-columns: 1fr;
            }}

            .trade-levels {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="header">
            <h1>🎯 Trading Opportunities</h1>
            <div class="subtitle">{now.strftime('%B %d, %Y at %I:%M %p')}</div>
        </div>

        <div class="stats-bar">
            <div class="stat">
                <div class="stat-value">{len(all_opportunities)}</div>
                <div class="stat-label">Opportunities Found</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len([o for o in all_opportunities if o['confidence'] >= 80])}</div>
                <div class="stat-label">High Confidence</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(SYMBOLS)}</div>
                <div class="stat-label">Markets Scanned</div>
            </div>
        </div>

        <div class="content">
"""

    if all_opportunities:
        for opp in all_opportunities:
            direction_class = 'long' if opp['direction'] == 'LONG' else 'short'

            html += f"""
            <div class="opportunity-card">
                <div class="opp-header">
                    <div class="opp-symbol">{opp['symbol']}</div>
                    <div class="opp-direction {direction_class}">{opp['direction']}</div>
                </div>

                <div class="opp-strategy">{opp['strategy']} • {opp['signal']}</div>

                <div class="opp-trigger">
                    📊 {opp['trigger']}
                </div>

                <div class="metrics-row">
                    <div class="metric-box">
                        <div class="metric-label">Current Price</div>
                        <div class="metric-value">${opp['current_price']:.5f}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">RSI (28)</div>
                        <div class="metric-value">{opp['rsi']:.1f}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">24H Momentum</div>
                        <div class="metric-value" style="color: {'#10b981' if opp['momentum_24h'] > 0 else '#ef4444'}">
                            {opp['momentum_24h']:+.1f}%
                        </div>
                    </div>
                </div>

                <div class="trade-levels">
                    <div class="level-box entry">
                        <div class="level-label">Entry</div>
                        <div class="level-value">${opp['entry']:.5f}</div>
                    </div>
                    <div class="level-box sl">
                        <div class="level-label">Stop Loss</div>
                        <div class="level-value">${opp['sl']:.5f}</div>
                    </div>
                    <div class="level-box tp">
                        <div class="level-label">Take Profit</div>
                        <div class="level-value">${opp['tp']:.5f}</div>
                    </div>
                </div>

                <div class="confidence-bar">
                    <div class="confidence-label">
                        Confidence Level: {opp['confidence']}% • Risk/Reward: 1:{opp['rr_ratio']:.1f}
                    </div>
                    <div class="confidence-progress">
                        <div class="confidence-fill" style="width: {opp['confidence']}%"></div>
                    </div>
                </div>
            </div>
"""
    else:
        html += """
            <div class="no-opportunities">
                <div class="no-opportunities-icon">📊</div>
                <div class="no-opportunities-text">
                    No high-probability opportunities detected at this time.<br>
                    We'll continue monitoring and alert you when setups emerge.
                </div>
            </div>
"""

    html += f"""
        </div>

        <div class="footer">
            <div class="footer-text">
                Opportunities are scanned every 10 minutes across {len(SYMBOLS)} markets.<br>
                All setups include risk management with 1.5 ATR stop loss and 3 ATR target (2:1 R:R minimum).
            </div>
            <div class="footer-brand">PropShop Quantitative Trading</div>
        </div>
    </div>
</body>
</html>
"""

    return html

# Main execution
print("="*80)
print("SCANNING FOR TRADING OPPORTUNITIES")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

all_opportunities = []

print(f"\nScanning {len(SYMBOLS)} symbols...\n")

for symbol in SYMBOLS:
    print(f"  {symbol:10s}...", end=" ")
    opps = scan_symbol(symbol)

    if opps:
        all_opportunities.extend(opps)
        print(f"[{len(opps)} opportunities]")
    else:
        print("[No signals]")

print(f"\n{'='*80}")
print(f"FOUND {len(all_opportunities)} OPPORTUNITIES")
print(f"{'='*80}")

if all_opportunities:
    print("\nTop Opportunities:")
    for i, opp in enumerate(sorted(all_opportunities, key=lambda x: x['confidence'], reverse=True)[:5], 1):
        print(f"  {i}. {opp['symbol']:10s} {opp['direction']:5s} - {opp['strategy']:20s} (Confidence: {opp['confidence']}%)")

print(f"\nGenerating beautiful email...")
html_email = format_opportunities_email(all_opportunities)

print(f"Sending to {EMAIL_TO}...")
subject = f"🎯 {len(all_opportunities)} Trading Opportunities Detected"

if send_email(subject, html_email):
    print("[SUCCESS] Opportunities email sent!")
else:
    print("[FAILED] Email not sent")

mt5.shutdown()
print("\n[DONE]")
