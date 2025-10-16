"""
FULL MARKET SCAN - ALL AVAILABLE INSTRUMENTS
Scans EVERYTHING your broker offers and finds opportunities
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

# EXPANDED SYMBOL LIST - Comprehensive coverage
SYMBOLS = {
    'Precious Metals': [
        'GOLD', 'XAUUSD', 'SILVER', 'XAGUSD', 'PLATINUM', 'XPTUSD',
        'PALLADIUM', 'XPDUSD', 'COPPER'
    ],

    'Forex Majors': [
        'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD'
    ],

    'Forex Minors': [
        'EURJPY', 'GBPJPY', 'EURGBP', 'EURAUD', 'EURCHF', 'EURCAD', 'EURNZD',
        'GBPAUD', 'GBPCHF', 'GBPCAD', 'GBPNZD', 'AUDJPY', 'AUDCHF', 'AUDCAD',
        'AUDNZD', 'NZDJPY', 'NZDCHF', 'NZDCAD', 'CADJPY', 'CADCHF', 'CHFJPY'
    ],

    'Exotic Forex': [
        'USDMXN', 'USDZAR', 'USDTRY', 'USDSEK', 'USDNOK', 'USDDKK', 'USDPLN',
        'USDHUF', 'USDCZK', 'USDSGD', 'USDHKD', 'EURPLN', 'EURTRY', 'EURSEK',
        'EURNOK', 'GBPSEK', 'GBPNOK', 'GBPPLN'
    ],

    'US Indices': [
        'US30', 'US500', 'US100', 'US2000', 'SPX500', 'NAS100', 'DJ30',
        'DJI30', 'USTEC', 'SPX', 'NDX'
    ],

    'European Indices': [
        'UK100', 'GER40', 'GER30', 'FRA40', 'ESP35', 'ITA40', 'EU50',
        'STOXX50', 'DAX', 'FTSE', 'CAC'
    ],

    'Asian Indices': [
        'JPN225', 'HK50', 'CHINA50', 'AUS200', 'IND50', 'SING30',
        'NIKKEI', 'HSI', 'ASX'
    ],

    'Crypto': [
        'BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD', 'BCHUSD', 'ADAUSD',
        'DOGEUSD', 'SOLUSD', 'DOTUSD', 'MATICUSD', 'BNBUSD'
    ],

    'Energy': [
        'CRUDE', 'BRENT', 'USOIL', 'UKOIL', 'NGAS', 'XBRUSD', 'XTIUSD',
        'WTI', 'OIL', 'GASO', 'HEATOIL'
    ],

    'Agriculture': [
        'WHEAT', 'CORN', 'SOYBEAN', 'SUGAR', 'COFFEE', 'COTTON', 'COCOA',
        'RICE', 'OATS'
    ],

    'Bonds': [
        'US10Y', 'US30Y', 'US5Y', 'US2Y', 'DE10Y', 'UK10Y', 'JP10Y',
        'USTBOND', 'BUND', 'GILT'
    ]
}

TIMEFRAME = mt5.TIMEFRAME_H1

def send_email(subject, message):
    """Send email via EmailJS"""
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
                signals.append("EMA BULLISH CROSS")
                score += 3
                break
            elif ema25.iloc[i-1] >= ema100.iloc[i-1] and ema25.iloc[i] < ema100.iloc[i]:
                signals.append("EMA BEARISH CROSS")
                score += 3
                break

        # RSI extremes
        current_rsi = rsi.iloc[-1]
        if current_rsi < 35:
            signals.append(f"RSI OVERSOLD ({current_rsi:.1f})")
            score += 2 if current_rsi < 30 else 1
        elif current_rsi > 80:
            signals.append(f"RSI OVERBOUGHT ({current_rsi:.1f})")
            score += 2 if current_rsi > 85 else 1

        # Donchian breakout
        if close.iloc[-1] > upper_channel.iloc[-2] and close.iloc[-2] <= upper_channel.iloc[-3]:
            signals.append("BREAKOUT ABOVE 50H HIGH")
            score += 3
        elif close.iloc[-1] < lower_channel.iloc[-2] and close.iloc[-2] >= lower_channel.iloc[-3]:
            signals.append("BREAKDOWN BELOW 50H LOW")
            score += 3

        # Trend
        if ema25.iloc[-1] > ema100.iloc[-1]:
            trend = "UPTREND"
            trend_strength = ((ema25.iloc[-1] / ema100.iloc[-1]) - 1) * 100
        else:
            trend = "DOWNTREND"
            trend_strength = ((ema100.iloc[-1] / ema25.iloc[-1]) - 1) * 100

        # High momentum
        if abs(price_change_24h) > 2:
            signals.append(f"HIGH MOMENTUM 24H ({price_change_24h:+.1f}%)")
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

def format_email(opportunities, all_data):
    """Format comprehensive market email"""
    message = f"FULL MARKET SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    if opportunities:
        message += f"{'='*60}\n"
        message += f"HIGH PRIORITY OPPORTUNITIES ({len(opportunities)})\n"
        message += f"{'='*60}\n\n"

        for opp in opportunities[:20]:  # Top 20 only
            message += f"{opp['symbol']} ({opp['category']}) - SCORE: {opp['score']}/10\n"
            message += f"  Price: ${opp['price']:.6f} | Trend: {opp['trend']} ({opp['trend_strength']:.2f}%)\n"
            message += f"  RSI: {opp['rsi']:.1f} | 24H: {opp['change_24h']:+.1f}% | 7D: {opp['change_7d']:+.1f}%\n"
            message += f"  Signals:\n"
            for sig in opp['signals']:
                message += f"    - {sig}\n"
            message += "\n"

        if len(opportunities) > 20:
            message += f"... and {len(opportunities) - 20} more opportunities\n\n"
    else:
        message += "No high-priority signals detected at this time.\n\n"

    # Category summaries
    message += f"\n{'='*60}\n"
    message += f"MARKET OVERVIEW BY CATEGORY\n"
    message += f"{'='*60}\n\n"

    for category, symbols in SYMBOLS.items():
        category_data = [d for d in all_data if d and d['category'] == category]
        if category_data:
            message += f"{category} ({len(category_data)} instruments):\n"
            for data in sorted(category_data, key=lambda x: abs(x['change_24h']), reverse=True)[:5]:
                emoji = "+" if data['change_24h'] > 0 else "-"
                message += f"  {emoji} {data['symbol']}: ${data['price']:.6f} "
                message += f"({data['change_24h']:+.1f}% 24H) "
                message += f"RSI:{data['rsi']:.0f} {data['trend']}\n"
            message += "\n"

    # Top movers
    message += f"{'='*60}\n"
    message += f"TOP MOVERS (24H)\n"
    message += f"{'='*60}\n\n"

    valid_data = [d for d in all_data if d]
    if valid_data:
        sorted_gainers = sorted(valid_data, key=lambda x: x['change_24h'], reverse=True)[:10]
        sorted_losers = sorted(valid_data, key=lambda x: x['change_24h'])[:10]

        message += "Biggest Gainers:\n"
        for i, data in enumerate(sorted_gainers, 1):
            message += f"  {i}. {data['symbol']} ({data['category']}): {data['change_24h']:+.2f}%\n"

        message += "\nBiggest Losers:\n"
        for i, data in enumerate(sorted_losers, 1):
            message += f"  {i}. {data['symbol']} ({data['category']}): {data['change_24h']:+.2f}%\n"

    # Most volatile
    if valid_data:
        message += f"\nMost Volatile:\n"
        sorted_volatile = sorted(valid_data, key=lambda x: x['volatility'], reverse=True)[:10]
        for i, data in enumerate(sorted_volatile, 1):
            message += f"  {i}. {data['symbol']} ({data['category']}): {data['volatility']:.2f}% ATR\n"

    total_symbols = sum(len(syms) for syms in SYMBOLS.values())
    message += f"\n\nScanned {len(valid_data)}/{total_symbols} instruments at {datetime.now().strftime('%H:%M:%S')}\n"
    message += f"Opportunities found: {len(opportunities)}\n"

    return message

# Initialize MT5
print("="*80)
print("FULL MARKET SCAN - ALL INSTRUMENTS")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

all_data = []
total_symbols = sum(len(syms) for syms in SYMBOLS.values())
current = 0
scanned = 0

print(f"\nScanning {total_symbols} symbols across {len(SYMBOLS)} categories...\n")

for category, symbol_list in SYMBOLS.items():
    print(f"\n{category}:")
    for symbol in symbol_list:
        current += 1
        print(f"  [{current}/{total_symbols}] {symbol:12s}...", end=" ")
        result = check_symbol(symbol, category)
        if result:
            all_data.append(result)
            scanned += 1
            if result['signals']:
                print(f"[SCORE {result['score']}] {', '.join(result['signals'][:2])}")
            else:
                print("[OK]")
        else:
            print("[SKIP]")

# Filter high-priority opportunities (score >= 2)
opportunities = [d for d in all_data if d and d['score'] >= 2]
opportunities.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'='*80}")
print(f"SCAN COMPLETE")
print(f"{'='*80}")
print(f"Total symbols attempted: {total_symbols}")
print(f"Successfully scanned: {scanned}")
print(f"Opportunities found (score >= 2): {len(opportunities)}")

if opportunities:
    print(f"\nTop 10 Opportunities:")
    for i, opp in enumerate(opportunities[:10], 1):
        print(f"  {i}. {opp['symbol']:12s} Score:{opp['score']} - {', '.join(opp['signals'][:2])}")

# Format and send email
subject = f"FULL MARKET SCAN: {len(opportunities)} Opportunities ({scanned} instruments)"
message = format_email(opportunities, all_data)

print(f"\nSending detailed email to {EMAIL_TO}...")
send_email(subject, message)

print("\n[DONE] Check your email!")

mt5.shutdown()
