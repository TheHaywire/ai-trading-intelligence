"""
LIVE MARKET COMMAND CENTER
Real-time market updates, opportunities, positions, and actionable intelligence
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

def get_technical_snapshot(symbol, timeframe=mt5.TIMEFRAME_H4):
    """Get comprehensive technical snapshot"""
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

    # Volatility
    df['Volatility'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252) * 100

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Trend determination
    if latest['close'] > latest['SMA_50'] > latest['SMA_200']:
        trend = "STRONG UPTREND"
        trend_score = 10
    elif latest['close'] > latest['SMA_50']:
        trend = "UPTREND"
        trend_score = 7
    elif latest['close'] < latest['SMA_50'] < latest['SMA_200']:
        trend = "STRONG DOWNTREND"
        trend_score = -10
    elif latest['close'] < latest['SMA_50']:
        trend = "DOWNTREND"
        trend_score = -7
    else:
        trend = "RANGING"
        trend_score = 0

    # Momentum
    rsi = latest['RSI']
    if rsi > 70:
        momentum = "OVERBOUGHT"
    elif rsi < 30:
        momentum = "OVERSOLD"
    else:
        momentum = "NEUTRAL"

    # MACD signal
    if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
        macd_signal = "BULLISH CROSS"
    elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
        macd_signal = "BEARISH CROSS"
    elif latest['MACD'] > latest['MACD_Signal']:
        macd_signal = "BULLISH"
    else:
        macd_signal = "BEARISH"

    # Price change
    price_change_pct = ((latest['close'] - prev['close']) / prev['close']) * 100

    # Calculate 24h change
    if len(df) >= 24:
        day_ago_price = df.iloc[-24]['close']
        day_change_pct = ((latest['close'] - day_ago_price) / day_ago_price) * 100
    else:
        day_change_pct = price_change_pct

    return {
        'symbol': symbol,
        'price': latest['close'],
        'change_24h': day_change_pct,
        'change_4h': price_change_pct,
        'trend': trend,
        'trend_score': trend_score,
        'rsi': rsi,
        'momentum': momentum,
        'macd_signal': macd_signal,
        'volatility': latest['Volatility'],
        'atr': latest['ATR'],
        'sma_20': latest['SMA_20'],
        'sma_50': latest['SMA_50'],
        'sma_200': latest['SMA_200'],
        'volume': latest['tick_volume']
    }

def identify_trade_setup(snapshot):
    """Identify if there's a trade setup"""
    if snapshot is None:
        return None

    setups = []

    # Trend following setups
    if snapshot['trend'] in ['STRONG UPTREND', 'UPTREND']:
        if snapshot['rsi'] < 50 and snapshot['macd_signal'] == 'BULLISH':
            setups.append({
                'type': 'LONG',
                'reason': 'Pullback in uptrend with bullish MACD',
                'confidence': 85,
                'entry': snapshot['price'],
                'stop': snapshot['price'] - (snapshot['atr'] * 2),
                'target': snapshot['price'] + (snapshot['atr'] * 3)
            })
        elif snapshot['macd_signal'] == 'BULLISH CROSS':
            setups.append({
                'type': 'LONG',
                'reason': 'MACD bullish crossover in uptrend',
                'confidence': 80,
                'entry': snapshot['price'],
                'stop': snapshot['price'] - (snapshot['atr'] * 2),
                'target': snapshot['price'] + (snapshot['atr'] * 3)
            })

    elif snapshot['trend'] in ['STRONG DOWNTREND', 'DOWNTREND']:
        if snapshot['rsi'] > 50 and snapshot['macd_signal'] == 'BEARISH':
            setups.append({
                'type': 'SHORT',
                'reason': 'Pullback in downtrend with bearish MACD',
                'confidence': 85,
                'entry': snapshot['price'],
                'stop': snapshot['price'] + (snapshot['atr'] * 2),
                'target': snapshot['price'] - (snapshot['atr'] * 3)
            })
        elif snapshot['macd_signal'] == 'BEARISH CROSS':
            setups.append({
                'type': 'SHORT',
                'reason': 'MACD bearish crossover in downtrend',
                'confidence': 80,
                'entry': snapshot['price'],
                'stop': snapshot['price'] + (snapshot['atr'] * 2),
                'target': snapshot['price'] - (snapshot['atr'] * 3)
            })

    # Mean reversion in ranging market
    elif snapshot['trend'] == 'RANGING':
        if snapshot['rsi'] < 30:
            setups.append({
                'type': 'LONG',
                'reason': 'Oversold in ranging market',
                'confidence': 70,
                'entry': snapshot['price'],
                'stop': snapshot['price'] - (snapshot['atr'] * 1.5),
                'target': snapshot['sma_20']
            })
        elif snapshot['rsi'] > 70:
            setups.append({
                'type': 'SHORT',
                'reason': 'Overbought in ranging market',
                'confidence': 70,
                'entry': snapshot['price'],
                'stop': snapshot['price'] + (snapshot['atr'] * 1.5),
                'target': snapshot['sma_20']
            })

    return setups if setups else None

print("="*100)
print("LIVE MARKET COMMAND CENTER")
print("="*100)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

# Get account status
account = mt5.account_info()
positions = mt5.positions_get()

print(f"\n{'='*100}")
print("ACCOUNT STATUS")
print(f"{'='*100}")
print(f"Balance:        ${account.balance:,.2f}")
print(f"Equity:         ${account.equity:,.2f}")
print(f"Unrealized P&L: ${account.profit:,.2f}")
print(f"Margin Level:   {account.margin_level:.2f}%")
print(f"Open Positions: {len(positions) if positions else 0}")

# Market scan - all major symbols
SYMBOLS = [
    'GOLD', 'SILVER', 'XPDUSD', 'XPTUSD',  # Metals
    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD', 'USDCAD', 'USDCHF',  # Forex majors
    'EURGBP', 'EURJPY', 'GBPJPY',  # Forex crosses
    'BTCUSD', 'ETHUSD', 'XRPUSD',  # Crypto
    'US100Cash', 'US500Cash', 'US30Cash', 'GER40Cash', 'UK100Cash',  # Indices
    'USOUSD', 'UKOUSD'  # Oil
]

print(f"\n{'='*100}")
print("MARKET OVERVIEW - ALL SYMBOLS")
print(f"{'='*100}")

market_data = []
opportunities = []

for symbol in SYMBOLS:
    snapshot = get_technical_snapshot(symbol)
    if snapshot:
        market_data.append(snapshot)

        # Check for trade setups
        setups = identify_trade_setup(snapshot)
        if setups:
            for setup in setups:
                opportunities.append({
                    'symbol': symbol,
                    'setup': setup,
                    'snapshot': snapshot
                })

        # Print summary
        trend_emoji = "[UP]" if snapshot['trend_score'] > 0 else "[DOWN]" if snapshot['trend_score'] < 0 else "[FLAT]"
        print(f"{symbol:12s} | ${snapshot['price']:>10.5f} | {snapshot['change_24h']:>+6.2f}% | {trend_emoji} {snapshot['trend']:20s} | RSI: {snapshot['rsi']:>5.1f}")

# Sort opportunities by confidence
opportunities.sort(key=lambda x: x['setup']['confidence'], reverse=True)

print(f"\n{'='*100}")
print(f"TRADE OPPORTUNITIES IDENTIFIED: {len(opportunities)}")
print(f"{'='*100}")

if opportunities:
    for i, opp in enumerate(opportunities[:10], 1):  # Top 10
        setup = opp['setup']
        snapshot = opp['snapshot']

        rr_ratio = abs(setup['target'] - setup['entry']) / abs(setup['entry'] - setup['stop'])

        print(f"\n[{i}] {opp['symbol']} - {setup['type']}")
        print(f"    Reason: {setup['reason']}")
        print(f"    Confidence: {setup['confidence']}%")
        print(f"    Entry: {setup['entry']:.5f}")
        print(f"    Stop: {setup['stop']:.5f}")
        print(f"    Target: {setup['target']:.5f}")
        print(f"    Risk/Reward: 1:{rr_ratio:.2f}")
        print(f"    Current Trend: {snapshot['trend']} | RSI: {snapshot['rsi']:.1f}")
else:
    print("No high-confidence setups at this time")

# Open positions analysis
print(f"\n{'='*100}")
print("CURRENT POSITIONS STATUS")
print(f"{'='*100}")

if positions:
    total_profit = 0
    for pos in positions:
        position_type = "LONG" if pos.type == mt5.ORDER_TYPE_BUY else "SHORT"
        pnl_pct = ((pos.price_current - pos.price_open) / pos.price_open * 100) if position_type == "LONG" else ((pos.price_open - pos.price_current) / pos.price_open * 100)

        status = "[WIN]" if pos.profit > 0 else "[LOSS]"

        # Get current market snapshot for this position
        snap = get_technical_snapshot(pos.symbol)
        trend_alignment = ""
        if snap:
            if (position_type == "LONG" and snap['trend_score'] > 0) or (position_type == "SHORT" and snap['trend_score'] < 0):
                trend_alignment = "[ALIGNED]"
            else:
                trend_alignment = "[AGAINST TREND]"

        print(f"{status} {pos.symbol:12s} {position_type:5s} | Entry: {pos.price_open:>10.5f} | Current: {pos.price_current:>10.5f} | P&L: ${pos.profit:>+10,.2f} ({pnl_pct:>+6.2f}%) {trend_alignment}")
        total_profit += pos.profit

    print(f"\nTotal Unrealized P&L: ${total_profit:,.2f}")
else:
    print("No open positions")

# Market movers (biggest changes)
print(f"\n{'='*100}")
print("TOP MOVERS (24H)")
print(f"{'='*100}")

market_data.sort(key=lambda x: abs(x['change_24h']), reverse=True)
print("\nBiggest Gainers:")
gainers = [m for m in market_data if m['change_24h'] > 0][:5]
for m in gainers:
    print(f"  {m['symbol']:12s}: +{m['change_24h']:.2f}% | {m['trend']}")

print("\nBiggest Losers:")
losers = [m for m in market_data if m['change_24h'] < 0][:5]
for m in losers:
    print(f"  {m['symbol']:12s}: {m['change_24h']:.2f}% | {m['trend']}")

# Market sentiment
print(f"\n{'='*100}")
print("MARKET SENTIMENT")
print(f"{'='*100}")

bullish_count = len([m for m in market_data if m['trend_score'] > 0])
bearish_count = len([m for m in market_data if m['trend_score'] < 0])
neutral_count = len([m for m in market_data if m['trend_score'] == 0])

print(f"Bullish Markets: {bullish_count} ({bullish_count/len(market_data)*100:.1f}%)")
print(f"Bearish Markets: {bearish_count} ({bearish_count/len(market_data)*100:.1f}%)")
print(f"Ranging Markets: {neutral_count} ({neutral_count/len(market_data)*100:.1f}%)")

if bullish_count > bearish_count * 1.5:
    sentiment = "RISK-ON (Bullish sentiment across markets)"
elif bearish_count > bullish_count * 1.5:
    sentiment = "RISK-OFF (Bearish sentiment across markets)"
else:
    sentiment = "MIXED (No clear directional bias)"

print(f"\nOverall Sentiment: {sentiment}")

# Generate beautiful HTML report
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            margin: 0;
            padding: 30px 15px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .timestamp {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: #333;
        }}
        .stat-value.positive {{ color: #10b981; }}
        .stat-value.negative {{ color: #ef4444; }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            margin: 0 0 20px 0;
            color: #1e3c72;
            font-size: 20px;
            border-bottom: 2px solid #1e3c72;
            padding-bottom: 10px;
        }}
        .opportunity {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }}
        .opportunity-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .symbol-badge {{
            font-size: 20px;
            font-weight: 700;
        }}
        .confidence {{
            background: rgba(255,255,255,0.3);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }}
        .setup-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .detail {{
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 8px;
        }}
        .detail-label {{
            font-size: 11px;
            opacity: 0.8;
            margin-bottom: 4px;
        }}
        .detail-value {{
            font-size: 16px;
            font-weight: 600;
        }}
        .market-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .market-table th {{
            background: #f1f5f9;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #334155;
        }}
        .market-table td {{
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .market-table tr:hover {{
            background: #f8fafc;
        }}
        .trend-up {{ color: #10b981; font-weight: 600; }}
        .trend-down {{ color: #ef4444; font-weight: 600; }}
        .trend-neutral {{ color: #6b7280; }}
        .position {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 4px solid #ccc;
        }}
        .position.win {{ border-left-color: #10b981; }}
        .position.loss {{ border-left-color: #ef4444; }}
        .position-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .alert {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .sentiment-bar {{
            display: flex;
            height: 40px;
            border-radius: 20px;
            overflow: hidden;
            margin: 15px 0;
        }}
        .bullish {{ background: #10b981; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; }}
        .bearish {{ background: #ef4444; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; }}
        .neutral {{ background: #6b7280; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LIVE MARKET COMMAND CENTER</h1>
            <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="dashboard">
            <div class="stat-card">
                <div class="stat-label">Balance</div>
                <div class="stat-value">${account.balance:,.0f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Equity</div>
                <div class="stat-value">${account.equity:,.0f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Unrealized P&L</div>
                <div class="stat-value {'positive' if account.profit > 0 else 'negative'}">${account.profit:+,.0f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Open Positions</div>
                <div class="stat-value">{len(positions) if positions else 0}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Opportunities</div>
                <div class="stat-value">{len(opportunities)}</div>
            </div>
        </div>

        <div class="content">
"""

# Market Sentiment
bullish_pct = (bullish_count/len(market_data)*100)
bearish_pct = (bearish_count/len(market_data)*100)
neutral_pct = (neutral_count/len(market_data)*100)

html += f"""
            <div class="section">
                <h2>Market Sentiment</h2>
                <div class="sentiment-bar">
                    <div class="bullish" style="width: {bullish_pct}%">{bullish_count} Bullish</div>
                    <div class="neutral" style="width: {neutral_pct}%">{neutral_count}</div>
                    <div class="bearish" style="width: {bearish_pct}%">{bearish_count} Bearish</div>
                </div>
                <p style="text-align: center; font-weight: 600; color: #334155;">{sentiment}</p>
            </div>
"""

# Trade Opportunities
html += f"""
            <div class="section">
                <h2>High-Confidence Trade Opportunities ({len(opportunities)})</h2>
"""

if opportunities:
    for i, opp in enumerate(opportunities[:5], 1):
        setup = opp['setup']
        snapshot = opp['snapshot']
        rr_ratio = abs(setup['target'] - setup['entry']) / abs(setup['entry'] - setup['stop'])

        html += f"""
                <div class="opportunity">
                    <div class="opportunity-header">
                        <div>
                            <span class="symbol-badge">{opp['symbol']}</span>
                            <span style="margin-left: 15px; font-size: 18px; font-weight: 600;">{setup['type']}</span>
                        </div>
                        <div class="confidence">{setup['confidence']}% Confidence</div>
                    </div>
                    <div style="margin-bottom: 10px;">{setup['reason']}</div>
                    <div class="setup-details">
                        <div class="detail">
                            <div class="detail-label">Entry Price</div>
                            <div class="detail-value">{setup['entry']:.5f}</div>
                        </div>
                        <div class="detail">
                            <div class="detail-label">Stop Loss</div>
                            <div class="detail-value">{setup['stop']:.5f}</div>
                        </div>
                        <div class="detail">
                            <div class="detail-label">Take Profit</div>
                            <div class="detail-value">{setup['target']:.5f}</div>
                        </div>
                        <div class="detail">
                            <div class="detail-label">Risk/Reward</div>
                            <div class="detail-value">1:{rr_ratio:.2f}</div>
                        </div>
                        <div class="detail">
                            <div class="detail-label">Trend</div>
                            <div class="detail-value">{snapshot['trend']}</div>
                        </div>
                        <div class="detail">
                            <div class="detail-label">RSI</div>
                            <div class="detail-value">{snapshot['rsi']:.1f}</div>
                        </div>
                    </div>
                </div>
"""
else:
    html += "<p>No high-confidence setups at this time. Wait for better opportunities.</p>"

html += "</div>"

# Current Positions
html += f"""
            <div class="section">
                <h2>Current Positions ({len(positions) if positions else 0})</h2>
"""

if positions:
    for pos in positions:
        position_type = "LONG" if pos.type == mt5.ORDER_TYPE_BUY else "SHORT"
        pnl_pct = ((pos.price_current - pos.price_open) / pos.price_open * 100) if position_type == "LONG" else ((pos.price_open - pos.price_current) / pos.price_open * 100)
        win_class = "win" if pos.profit > 0 else "loss"

        snap = get_technical_snapshot(pos.symbol)
        trend_warning = ""
        if snap:
            if (position_type == "LONG" and snap['trend_score'] < 0) or (position_type == "SHORT" and snap['trend_score'] > 0):
                trend_warning = '<div class="alert" style="margin-top: 10px; background: #fee2e2; border-left-color: #dc2626;">WARNING: Position against current trend!</div>'

        html += f"""
                <div class="position {win_class}">
                    <div class="position-header">
                        <div>
                            <strong style="font-size: 16px;">{pos.symbol}</strong>
                            <span style="margin-left: 10px; color: #666;">{position_type}</span>
                        </div>
                        <div>
                            <span style="font-size: 18px; font-weight: 700; color: {'#10b981' if pos.profit > 0 else '#ef4444'};">${pos.profit:+,.2f}</span>
                            <span style="margin-left: 8px; color: #666;">({pnl_pct:+.2f}%)</span>
                        </div>
                    </div>
                    <div style="font-size: 13px; color: #666;">
                        Entry: {pos.price_open:.5f} | Current: {pos.price_current:.5f} | Volume: {pos.volume} lots
                    </div>
                    {trend_warning}
                </div>
"""
else:
    html += "<p>No open positions</p>"

html += "</div>"

# Top Movers
html += """
            <div class="section">
                <h2>Top Market Movers (24H)</h2>
                <table class="market-table">
                    <tr>
                        <th>Symbol</th>
                        <th>Price</th>
                        <th>24H Change</th>
                        <th>Trend</th>
                        <th>RSI</th>
                    </tr>
"""

top_movers = sorted(market_data, key=lambda x: abs(x['change_24h']), reverse=True)[:15]
for m in top_movers:
    trend_class = "trend-up" if m['trend_score'] > 0 else "trend-down" if m['trend_score'] < 0 else "trend-neutral"
    change_class = "trend-up" if m['change_24h'] > 0 else "trend-down"

    html += f"""
                    <tr>
                        <td><strong>{m['symbol']}</strong></td>
                        <td>{m['price']:.5f}</td>
                        <td class="{change_class}">{m['change_24h']:+.2f}%</td>
                        <td class="{trend_class}">{m['trend']}</td>
                        <td>{m['rsi']:.1f}</td>
                    </tr>
"""

html += """
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

print(f"\n{'='*100}")
print("Sending comprehensive market update to email...")
print(f"{'='*100}")

if send_email("LIVE MARKET UPDATE", html):
    print("[SUCCESS] Market update sent to your email!")
else:
    print("[FAILED] Could not send email")

mt5.shutdown()
print("\n[DONE]")
