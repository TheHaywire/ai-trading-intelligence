"""
GOLD REVERSAL PROBABILITY ANALYSIS
Should we hold GOLD shorts waiting for reversal, or cut losses now?
Deep quantitative analysis with historical data
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

print("="*100)
print("GOLD REVERSAL PROBABILITY ANALYSIS")
print("="*100)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

# Get comprehensive Gold data (12 months of H4 data)
print("[1/7] Fetching Gold historical data...")
rates = mt5.copy_rates_from_pos('GOLD', mt5.TIMEFRAME_H4, 0, 2000)

if rates is None or len(rates) == 0:
    print("Failed to get Gold data")
    exit()

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

# Calculate comprehensive indicators
print("[2/7] Calculating technical indicators...")

# Moving Averages
df['SMA_20'] = df['close'].rolling(20).mean()
df['SMA_50'] = df['close'].rolling(50).mean()
df['SMA_100'] = df['close'].rolling(100).mean()
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
df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

# Bollinger Bands
df['BB_Middle'] = df['close'].rolling(20).mean()
bb_std = df['close'].rolling(20).std()
df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']

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

# Volume
df['Volume_SMA'] = df['tick_volume'].rolling(20).mean()
df['Volume_Ratio'] = df['tick_volume'] / df['Volume_SMA']

current = df.iloc[-1]
print(f"\nCurrent Gold Price: ${current['close']:.2f}")
print(f"Current RSI: {current['RSI']:.1f}")
print(f"Current MACD: {current['MACD']:.2f}")
print(f"Distance from SMA 50: {((current['close'] - current['SMA_50']) / current['SMA_50'] * 100):.2f}%")
print(f"Distance from SMA 200: {((current['close'] - current['SMA_200']) / current['SMA_200'] * 100):.2f}%")

# HISTORICAL ANALYSIS: What happens after RSI > 70?
print("\n[3/7] Analyzing historical RSI overbought reversals...")

overbought_periods = df[df['RSI'] > 70].copy()
print(f"Found {len(overbought_periods)} periods where RSI > 70")

reversal_outcomes = []

for idx in overbought_periods.index:
    # Look ahead 24 candles (4 days on H4)
    future_idx = idx + 24
    if future_idx < len(df):
        entry_price = df.loc[idx, 'close']
        future_prices = df.loc[idx:future_idx, 'close']

        # Find lowest price in next 4 days
        lowest_future = future_prices.min()
        highest_future = future_prices.max()

        # Calculate if a short would profit
        max_profit = ((entry_price - lowest_future) / entry_price) * 100
        max_loss = ((highest_future - entry_price) / entry_price) * 100

        final_price = df.loc[future_idx, 'close']
        final_pnl = ((entry_price - final_price) / entry_price) * 100

        reversal_outcomes.append({
            'entry_price': entry_price,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'final_pnl': final_pnl,
            'reversed': final_pnl > 1  # Profitable short = reversal
        })

if reversal_outcomes:
    reversals_df = pd.DataFrame(reversal_outcomes)

    reversal_rate = (reversals_df['reversed'].sum() / len(reversals_df)) * 100
    avg_profit_if_reversed = reversals_df[reversals_df['reversed']]['final_pnl'].mean()
    avg_loss_if_continued = reversals_df[~reversals_df['reversed']]['final_pnl'].mean()
    avg_max_loss = reversals_df['max_loss'].mean()

    print(f"\nReversal Statistics (RSI > 70):")
    print(f"  Reversal Rate (4 days): {reversal_rate:.1f}%")
    print(f"  Avg Profit if Reversed: +{avg_profit_if_reversed:.2f}%")
    print(f"  Avg Loss if Continued: {avg_loss_if_continued:.2f}%")
    print(f"  Avg Max Drawdown: {avg_max_loss:.2f}%")

    # Expected Value calculation
    ev = (reversal_rate/100 * avg_profit_if_reversed) + ((100-reversal_rate)/100 * avg_loss_if_continued)
    print(f"  Expected Value: {ev:.2f}%")

# TREND STRENGTH ANALYSIS
print("\n[4/7] Analyzing trend strength and exhaustion signals...")

# Price vs moving averages
above_sma50 = current['close'] > current['SMA_50']
above_sma200 = current['close'] > current['SMA_200']
sma50_above_sma200 = current['SMA_50'] > current['SMA_200']

trend_strength_score = 0
if above_sma50: trend_strength_score += 1
if above_sma200: trend_strength_score += 1
if sma50_above_sma200: trend_strength_score += 1
if current['MACD'] > current['MACD_Signal']: trend_strength_score += 1
if current['close'] > current['BB_Upper']: trend_strength_score -= 1  # Overextended
if current['RSI'] > 75: trend_strength_score -= 1  # Extreme overbought

print(f"Trend Strength Score: {trend_strength_score}/4")
print(f"  Price > SMA 50: {above_sma50}")
print(f"  Price > SMA 200: {above_sma200}")
print(f"  SMA 50 > SMA 200: {sma50_above_sma200}")
print(f"  MACD Bullish: {current['MACD'] > current['MACD_Signal']}")
print(f"  RSI: {current['RSI']:.1f} ({'EXTREME' if current['RSI'] > 75 else 'OVERBOUGHT' if current['RSI'] > 70 else 'NEUTRAL'})")

# SUPPORT/RESISTANCE ANALYSIS
print("\n[5/7] Calculating key support/resistance levels...")

recent_data = df.tail(200)

# Find recent swing highs and lows
from scipy.signal import argrelextrema

highs_idx = argrelextrema(recent_data['high'].values, np.greater, order=5)[0]
lows_idx = argrelextrema(recent_data['low'].values, np.less, order=5)[0]

resistance_levels = recent_data.iloc[highs_idx]['high'].values
support_levels = recent_data.iloc[lows_idx]['low'].values

# Find nearest levels
current_price = current['close']
nearest_resistance = resistance_levels[resistance_levels > current_price]
nearest_support = support_levels[support_levels < current_price]

if len(nearest_resistance) > 0:
    next_resistance = nearest_resistance.min()
    resistance_distance = ((next_resistance - current_price) / current_price) * 100
    print(f"Nearest Resistance: ${next_resistance:.2f} (+{resistance_distance:.2f}%)")
else:
    next_resistance = None
    print(f"Nearest Resistance: NONE (making new highs!)")

if len(nearest_support) > 0:
    next_support = nearest_support.max()
    support_distance = ((current_price - next_support) / current_price) * 100
    print(f"Nearest Support: ${next_support:.2f} (-{support_distance:.2f}%)")
else:
    next_support = None
    print(f"Nearest Support: NONE")

# Key moving average support
print(f"SMA 50 Support: ${current['SMA_50']:.2f} (-{((current_price - current['SMA_50'])/current_price*100):.2f}%)")
print(f"SMA 200 Support: ${current['SMA_200']:.2f} (-{((current_price - current['SMA_200'])/current_price*100):.2f}%)")

# MOMENTUM DIVERGENCE
print("\n[6/7] Checking for bearish divergences...")

recent_highs = df.tail(50)
price_highs = argrelextrema(recent_highs['high'].values, np.greater, order=3)[0]

if len(price_highs) >= 2:
    last_two_highs = price_highs[-2:]
    price1 = recent_highs.iloc[last_two_highs[0]]['high']
    price2 = recent_highs.iloc[last_two_highs[1]]['high']
    rsi1 = recent_highs.iloc[last_two_highs[0]]['RSI']
    rsi2 = recent_highs.iloc[last_two_highs[1]]['RSI']

    bearish_divergence = (price2 > price1) and (rsi2 < rsi1)

    if bearish_divergence:
        print("BEARISH DIVERGENCE DETECTED!")
        print(f"  Price: ${price1:.2f} -> ${price2:.2f} (higher high)")
        print(f"  RSI: {rsi1:.1f} -> {rsi2:.1f} (lower high)")
        print("  This suggests weakening momentum - reversal possible")
    else:
        print("No bearish divergence detected")
        print("  Both price and momentum making higher highs - trend still strong")
else:
    print("Insufficient data for divergence analysis")

# SCENARIO ANALYSIS & RECOMMENDATION
print("\n[7/7] SCENARIO ANALYSIS - HOLD vs CUT")
print("="*100)

# Get current GOLD short positions
positions = mt5.positions_get(symbol='GOLD')
short_positions = [p for p in positions if p.type == mt5.ORDER_TYPE_SELL]

if short_positions:
    total_loss = sum(p.profit for p in short_positions)
    avg_entry = sum(p.price_open * p.volume for p in short_positions) / sum(p.volume for p in short_positions)

    print(f"\nCURRENT SITUATION:")
    print(f"  {len(short_positions)} GOLD SHORT positions")
    print(f"  Average Entry: ${avg_entry:.2f}")
    print(f"  Current Price: ${current_price:.2f}")
    print(f"  Current Loss: ${total_loss:,.2f}")
    print(f"  Loss Percentage: {((current_price - avg_entry)/avg_entry*100):.2f}%")

    # Calculate scenarios
    print(f"\nSCENARIO 1: HOLD & WAIT FOR REVERSAL")
    print(f"  Probability of reversal in 4 days: {reversal_rate:.1f}%")
    print(f"  Expected profit if reversed: ${total_loss * (avg_profit_if_reversed/abs(total_loss/current_price*100)):,.2f}")
    print(f"  Expected additional loss if continues: ${total_loss * (avg_max_loss/abs(total_loss/current_price*100)):,.2f}")
    print(f"  Expected Value: ${total_loss * (ev/abs(total_loss/current_price*100)):,.2f}")

    print(f"\nSCENARIO 2: CUT LOSSES NOW")
    print(f"  Immediate Loss: ${total_loss:,.2f}")
    print(f"  Capital Preserved: ${sum(p.volume * p.price_current for p in short_positions):,.2f}")
    print(f"  Can Redeploy: YES (into winning trades)")

    # Calculate risk of further loss
    if next_resistance:
        additional_risk = ((next_resistance - current_price) / current_price) * abs(total_loss)
        print(f"\nRISK ANALYSIS:")
        print(f"  If Gold reaches next resistance (${next_resistance:.2f}):")
        print(f"  Additional Loss: ${additional_risk:,.2f}")
        print(f"  Total Loss Would Be: ${total_loss + additional_risk:,.2f}")

    # QUANTITATIVE RECOMMENDATION
    print(f"\n{'='*100}")
    print("QUANTITATIVE RECOMMENDATION:")
    print(f"{'='*100}")

    # Decision factors
    reversal_likely = reversal_rate > 50
    trend_weakening = trend_strength_score < 2
    at_resistance = next_resistance and resistance_distance < 2
    extreme_rsi = current['RSI'] > 75

    hold_score = 0
    cut_score = 0

    if reversal_likely:
        hold_score += 2
        print("[+2 HOLD] Historical reversal rate > 50%")
    else:
        cut_score += 2
        print("[+2 CUT] Historical reversal rate < 50%")

    if trend_weakening:
        hold_score += 1
        print("[+1 HOLD] Trend showing weakness")
    else:
        cut_score += 2
        print("[+2 CUT] Trend still strong")

    if at_resistance:
        hold_score += 2
        print("[+2 HOLD] Near resistance level")
    else:
        cut_score += 1
        print("[+1 CUT] No resistance nearby - can go higher")

    if extreme_rsi:
        hold_score += 1
        print("[+1 HOLD] RSI extremely overbought")

    if ev > 0:
        hold_score += 1
        print("[+1 HOLD] Positive expected value")
    else:
        cut_score += 1
        print("[+1 CUT] Negative expected value")

    # Current loss magnitude
    loss_pct = abs(total_loss / (sum(p.volume * p.price_open for p in short_positions)) * 100)
    if loss_pct > 5:
        cut_score += 2
        print("[+2 CUT] Loss exceeds 5% - risk management rule")

    print(f"\nFINAL SCORE:")
    print(f"  HOLD: {hold_score} points")
    print(f"  CUT: {cut_score} points")

    if hold_score > cut_score:
        recommendation = "HOLD"
        action = f"Wait for reversal. Set stop loss at ${next_resistance if next_resistance else current_price * 1.03:.2f}"
    else:
        recommendation = "CUT LOSSES NOW"
        action = "Close all GOLD shorts immediately. Market trend too strong."

    print(f"\n{'='*100}")
    print(f"VERDICT: {recommendation}")
    print(f"ACTION: {action}")
    print(f"{'='*100}")

else:
    print("No GOLD short positions found")
    recommendation = "N/A"
    action = "No positions to analyze"

# Generate HTML report
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            margin: 0;
            padding: 30px 15px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .content {{
            padding: 40px;
        }}
        .verdict {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            margin: 30px 0;
            font-size: 24px;
            font-weight: 700;
        }}
        .verdict.hold {{
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }}
        .stat {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: #333;
        }}
        .stat-value.negative {{ color: #ef4444; }}
        .stat-value.positive {{ color: #10b981; }}
        .section {{
            margin: 30px 0;
        }}
        .section h2 {{
            color: #1e293b;
            border-bottom: 2px solid #f59e0b;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .scenario {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin: 15px 0;
            border-left: 4px solid #3b82f6;
        }}
        .score-box {{
            display: flex;
            justify-content: space-around;
            margin: 25px 0;
        }}
        .score-item {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            flex: 1;
            margin: 0 10px;
        }}
        .score-item.winner {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            transform: scale(1.05);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        table th {{
            background: #f1f5f9;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        table td {{
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GOLD REVERSAL ANALYSIS</h1>
            <div style="opacity: 0.9; margin-top: 10px;">Should We Hold or Cut Losses?</div>
            <div style="opacity: 0.8; font-size: 14px; margin-top: 5px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="content">
            <div class="verdict {'hold' if recommendation == 'HOLD' else ''}">
                {recommendation}
            </div>

            <div style="text-align: center; font-size: 18px; color: #64748b; margin-bottom: 30px;">
                {action}
            </div>

            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-label">Current Price</div>
                    <div class="stat-value">${current['close']:.2f}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">RSI</div>
                    <div class="stat-value {'negative' if current['RSI'] > 70 else 'positive'}">{current['RSI']:.1f}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Current Loss</div>
                    <div class="stat-value negative">${total_loss:,.0f}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Reversal Probability</div>
                    <div class="stat-value">{reversal_rate:.1f}%</div>
                </div>
            </div>

            <div class="section">
                <h2>Historical Analysis</h2>
                <p>Based on {len(reversal_outcomes)} historical instances when Gold RSI > 70:</p>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Reversal Rate (4 days)</td>
                        <td style="font-weight: 600;">{reversal_rate:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Avg Profit if Reversed</td>
                        <td style="color: #10b981; font-weight: 600;">+{avg_profit_if_reversed:.2f}%</td>
                    </tr>
                    <tr>
                        <td>Avg Loss if Continued</td>
                        <td style="color: #ef4444; font-weight: 600;">{avg_loss_if_continued:.2f}%</td>
                    </tr>
                    <tr>
                        <td>Expected Value</td>
                        <td style="font-weight: 600; font-size: 18px;">{ev:.2f}%</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2>Scenario Comparison</h2>

                <div class="scenario">
                    <h3 style="margin-top: 0; color: #f59e0b;">Scenario 1: Hold & Wait</h3>
                    <p><strong>If Gold reverses:</strong> Could recover ${abs(total_loss * (avg_profit_if_reversed/abs(total_loss/(avg_entry)*100))):,.0f}</p>
                    <p><strong>If Gold continues:</strong> Could lose additional ${abs(total_loss * (avg_max_loss/abs(total_loss/(avg_entry)*100))):,.0f}</p>
                    <p><strong>Expected outcome:</strong> ${total_loss * (ev/abs(total_loss/(avg_entry)*100)):,.0f}</p>
                </div>

                <div class="scenario" style="border-left-color: #ef4444;">
                    <h3 style="margin-top: 0; color: #ef4444;">Scenario 2: Cut Losses Now</h3>
                    <p><strong>Immediate loss:</strong> ${total_loss:,.0f} (locked in)</p>
                    <p><strong>Capital preserved:</strong> ${sum(p.volume * p.price_current for p in short_positions):,.0f}</p>
                    <p><strong>Benefit:</strong> Can redeploy capital into winning trades immediately</p>
                </div>
            </div>

            <div class="section">
                <h2>Decision Score</h2>
                <div class="score-box">
                    <div class="score-item {'winner' if hold_score > cut_score else ''}">
                        <div style="font-size: 14px; opacity: 0.8;">HOLD</div>
                        <div style="font-size: 48px; font-weight: 700;">{hold_score}</div>
                        <div style="font-size: 12px; opacity: 0.8;">points</div>
                    </div>
                    <div class="score-item {'winner' if cut_score > hold_score else ''}">
                        <div style="font-size: 14px; opacity: 0.8;">CUT</div>
                        <div style="font-size: 48px; font-weight: 700;">{cut_score}</div>
                        <div style="font-size: 12px; opacity: 0.8;">points</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Key Levels</h2>
                <table>
                    <tr>
                        <th>Level</th>
                        <th>Price</th>
                        <th>Distance</th>
                    </tr>
                    <tr>
                        <td>Current Price</td>
                        <td style="font-weight: 700;">${current_price:.2f}</td>
                        <td>-</td>
                    </tr>
"""

if next_resistance:
    html += f"""
                    <tr>
                        <td>Next Resistance</td>
                        <td>${next_resistance:.2f}</td>
                        <td style="color: #ef4444;">+{resistance_distance:.2f}%</td>
                    </tr>
"""
else:
    html += """
                    <tr>
                        <td>Next Resistance</td>
                        <td colspan="2" style="color: #ef4444; font-weight: 600;">NONE - Making new highs!</td>
                    </tr>
"""

if next_support:
    html += f"""
                    <tr>
                        <td>Next Support</td>
                        <td>${next_support:.2f}</td>
                        <td style="color: #10b981;">-{support_distance:.2f}%</td>
                    </tr>
"""

html += f"""
                    <tr>
                        <td>SMA 50</td>
                        <td>${current['SMA_50']:.2f}</td>
                        <td>-{((current_price - current['SMA_50'])/current_price*100):.2f}%</td>
                    </tr>
                    <tr>
                        <td>SMA 200</td>
                        <td>${current['SMA_200']:.2f}</td>
                        <td>-{((current_price - current['SMA_200'])/current_price*100):.2f}%</td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

print("\nSending analysis to email...")
if send_email("GOLD: Hold or Cut? - Quantitative Analysis", html):
    print("[SUCCESS] Analysis sent!")
else:
    print("[FAILED] Email not sent")

mt5.shutdown()
print("\n[DONE]")
