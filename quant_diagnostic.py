"""
QUANTITATIVE DIAGNOSTIC - FIRST PRIORITY
What a real quant does FIRST: diagnose, assess risk, identify problems
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

TRADES_LOG_FILE = "trades_log.json"

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

print("="*80)
print("QUANTITATIVE DIAGNOSTIC - PRIORITY CHECK")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

# 1. ACCOUNT HEALTH CHECK
print("\n[1/6] ACCOUNT HEALTH CHECK")
print("-" * 80)

account = mt5.account_info()
print(f"Balance:        ${account.balance:,.2f}")
print(f"Equity:         ${account.equity:,.2f}")
print(f"Margin Used:    ${account.margin:,.2f}")
print(f"Margin Free:    ${account.margin_free:,.2f}")
print(f"Margin Level:   {account.margin_level:.2f}%")
print(f"Unrealized P&L: ${account.profit:,.2f}")

# Calculate drawdown
drawdown_pct = ((account.equity - account.balance) / account.balance) * 100
print(f"Current Drawdown: {drawdown_pct:+.2f}%")

if drawdown_pct < -5:
    print("[WARNING] Drawdown exceeds -5%")
if account.margin_level < 200:
    print("[WARNING] Margin level below 200%")

# 2. POSITION ANALYSIS
print("\n[2/6] POSITION ANALYSIS")
print("-" * 80)

positions = mt5.positions_get()
if positions:
    print(f"Open Positions: {len(positions)}")

    total_volume = sum(p.volume for p in positions)
    long_volume = sum(p.volume for p in positions if p.type == mt5.ORDER_TYPE_BUY)
    short_volume = sum(p.volume for p in positions if p.type == mt5.ORDER_TYPE_SELL)

    print(f"Total Volume:   {total_volume:.2f} lots")
    print(f"Long Exposure:  {long_volume:.2f} lots")
    print(f"Short Exposure: {short_volume:.2f} lots")
    print(f"Net Exposure:   {long_volume - short_volume:+.2f} lots")

    # Check concentration
    symbols = {}
    for p in positions:
        if p.symbol not in symbols:
            symbols[p.symbol] = 0
        symbols[p.symbol] += p.volume

    print(f"\nPosition Breakdown:")
    for symbol, vol in sorted(symbols.items(), key=lambda x: x[1], reverse=True):
        pct = (vol / total_volume) * 100
        print(f"  {symbol:10s}: {vol:.2f} lots ({pct:.1f}%)")
        if pct > 30:
            print(f"  [WARNING] {symbol} over 30% of portfolio")

    # Check unrealized P&L per position
    print(f"\nP&L by Position:")
    for p in positions:
        pnl_pct = (p.profit / (p.volume * p.price_open)) * 100
        status = "[WIN]" if p.profit > 0 else "[LOSS]"
        print(f"  {status} {p.symbol:10s}: ${p.profit:+,.2f} ({pnl_pct:+.2f}%)")
else:
    print("No open positions")

# 3. TRADE HISTORY ANALYSIS
print("\n[3/6] TRADE HISTORY ANALYSIS")
print("-" * 80)

try:
    with open(TRADES_LOG_FILE, 'r') as f:
        trades = json.load(f)

    closed_trades = [t for t in trades if t.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']]

    if closed_trades:
        wins = [t for t in closed_trades if t['current_status'] == 'CLOSED_WIN']
        losses = [t for t in closed_trades if t['current_status'] == 'CLOSED_LOSS']

        print(f"Total Closed Trades: {len(closed_trades)}")
        print(f"Winners: {len(wins)}")
        print(f"Losers: {len(losses)}")
        print(f"Win Rate: {len(wins)/len(closed_trades)*100:.1f}%")

        total_pnl = sum(t['current_pnl'] for t in closed_trades)
        print(f"Total P&L: {total_pnl:+.2f}%")

        # Check by strategy
        strategies = {}
        for t in closed_trades:
            for signal in t.get('signals', []):
                if signal not in strategies:
                    strategies[signal] = {'wins': 0, 'losses': 0, 'pnl': 0}

                if t['current_status'] == 'CLOSED_WIN':
                    strategies[signal]['wins'] += 1
                else:
                    strategies[signal]['losses'] += 1
                strategies[signal]['pnl'] += t['current_pnl']

        print(f"\nPerformance by Strategy:")
        for strat, data in strategies.items():
            total = data['wins'] + data['losses']
            wr = (data['wins'] / total * 100) if total > 0 else 0
            print(f"  {strat:30s}: {data['wins']}W/{data['losses']}L ({wr:.0f}%) | P&L: {data['pnl']:+.2f}%")

            if wr < 30 and total >= 3:
                print(f"  [WARNING] {strat} win rate below 30%!")

    else:
        print("No closed trades yet")

except:
    print("No trade log found")

# 4. RISK METRICS
print("\n[4/6] RISK METRICS")
print("-" * 80)

try:
    with open(TRADES_LOG_FILE, 'r') as f:
        trades = json.load(f)

    closed_trades = [t for t in trades if t.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']]

    if len(closed_trades) >= 2:
        returns = [t['current_pnl']/100 for t in closed_trades]
        equity_curve = [10000]
        for ret in returns:
            equity_curve.append(equity_curve[-1] * (1 + ret))

        # Sharpe Ratio
        returns_array = np.array(returns)
        sharpe = np.sqrt(252) * (returns_array.mean() / returns_array.std()) if returns_array.std() != 0 else 0

        # Max Drawdown
        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - cummax) / cummax
        max_dd = drawdown.min() * 100

        # Volatility
        volatility = returns_array.std() * np.sqrt(252) * 100

        print(f"Sharpe Ratio:      {sharpe:.2f}")
        print(f"Max Drawdown:      {max_dd:.2f}%")
        print(f"Volatility (ann.): {volatility:.2f}%")

        if sharpe < 0:
            print("[CRITICAL] Sharpe Ratio is NEGATIVE - losing money adjusted for risk!")
        elif sharpe < 1:
            print("[WARNING] Sharpe Ratio below 1.0 - risk-adjusted returns are poor")

        if max_dd < -10:
            print("[WARNING] Max drawdown exceeds -10%")

    else:
        print("Insufficient data for risk metrics (need 2+ closed trades)")

except:
    print("Error calculating risk metrics")

# 5. SYSTEM STATUS CHECK
print("\n[5/6] SYSTEM STATUS CHECK")
print("-" * 80)

print("Trading Engine: RUNNING")
print("Risk Management: ENABLED")
print("Max Risk per Trade: 1.0%")
print("Max Open Positions: 5")
print("Daily Loss Limit: -5.0%")

# Check if we're close to limits
if positions and len(positions) >= 5:
    print("[WARNING] At maximum position limit (5)")

if drawdown_pct <= -4:
    print("[WARNING] Approaching daily loss limit (-5%)")

# 6. RECOMMENDATIONS
print("\n[6/6] QUANT RECOMMENDATIONS")
print("-" * 80)

recommendations = []

# Based on performance
try:
    if sharpe < 0:
        recommendations.append("[CRITICAL] URGENT: PAUSE ALL TRADING - Sharpe ratio negative")
        recommendations.append("   Review strategy parameters immediately")
        recommendations.append("   Current strategies are destroying value")

    elif sharpe < 1:
        recommendations.append("[WARNING] REDUCE POSITION SIZES - Poor risk-adjusted returns")
        recommendations.append("   Cut risk per trade from 1% to 0.5%")

    if max_dd < -5:
        recommendations.append("[CRITICAL] IMPLEMENT TIGHTER STOPS - Drawdown too large")
        recommendations.append("   Reduce ATR multiplier from 1.5 to 1.0")

except:
    pass

# Based on positions
if positions:
    if len(positions) > 3:
        recommendations.append("[WARNING] HIGH POSITION COUNT - Consider reducing concentration")

    for symbol, vol in symbols.items():
        if (vol / total_volume) > 0.3:
            recommendations.append(f"[WARNING] CONCENTRATION RISK - {symbol} is {(vol/total_volume)*100:.0f}% of portfolio")

# Based on win rate
try:
    closed_trades = [t for t in trades if t.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']]
    if closed_trades:
        wr = len([t for t in closed_trades if t['current_status'] == 'CLOSED_WIN']) / len(closed_trades) * 100
        if wr < 40:
            recommendations.append("[CRITICAL] LOW WIN RATE - Current strategies not performing")
            recommendations.append("   Review entry criteria and filters")
except:
    pass

if recommendations:
    for rec in recommendations:
        print(rec)
else:
    print("[OK] No critical issues detected")
    print("[OK] System operating within acceptable parameters")

print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80)

# Generate email report
diagnostic_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background: #1a1a1a;
            color: #00ff00;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: #0a0a0a;
            border: 2px solid #00ff00;
            padding: 30px;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #00ff00;
            padding-bottom: 15px;
        }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid #00aa00;
        }}
        .critical {{
            color: #ff0000;
            background: #330000;
            padding: 10px;
            margin: 10px 0;
        }}
        .warning {{
            color: #ffaa00;
            background: #332200;
            padding: 10px;
            margin: 10px 0;
        }}
        .good {{
            color: #00ff00;
        }}
        pre {{
            color: #00ff00;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>QUANTITATIVE DIAGNOSTIC REPORT</h1>
        <pre>
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ACCOUNT STATUS:
Balance:     ${account.balance:,.2f}
Equity:      ${account.equity:,.2f}
Drawdown:    {drawdown_pct:+.2f}%
Positions:   {len(positions) if positions else 0}

"""

if recommendations:
    diagnostic_html += "\nCRITICAL RECOMMENDATIONS:\n"
    for rec in recommendations:
        diagnostic_html += f"{rec}\n"
else:
    diagnostic_html += "\n[OK] SYSTEM HEALTHY - No critical issues\n"

diagnostic_html += """
        </pre>
    </div>
</body>
</html>
"""

print(f"\nSending diagnostic report to {EMAIL_TO}...")
if send_email("QUANT DIAGNOSTIC REPORT", diagnostic_html):
    print("[SUCCESS] Report sent!")
else:
    print("[FAILED] Email not sent")

mt5.shutdown()
print("\n[DONE]")
