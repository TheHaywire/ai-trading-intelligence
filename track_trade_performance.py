"""
TRADE PERFORMANCE TRACKER
- Monitors open trades in real-time
- Checks if SL/TP levels hit
- Sends performance update emails
- Provides post-trade analysis and lessons learned
"""

import MetaTrader5 as mt5
import json
import requests
from datetime import datetime
import pandas as pd

# EmailJS Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

TRADES_LOG_FILE = "trades_log.json"

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
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False

def get_current_price(symbol):
    """Get current market price"""
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return (tick.bid + tick.ask) / 2
        return None
    except:
        return None

def check_trade_status(trade):
    """Check if trade hit SL or TP"""
    current_price = get_current_price(trade['symbol'])

    if not current_price:
        return trade['status'], 0, "NO DATA"

    direction = trade['direction']
    entry = trade['entry']
    sl = trade['stop_loss']
    tp1 = trade['tp1']
    tp2 = trade['tp2']
    tp3 = trade['tp3']

    # Calculate current P&L
    if direction == "LONG":
        pnl_pct = ((current_price - entry) / entry) * 100

        # Check if hit SL
        if current_price <= sl:
            return "CLOSED_LOSS", pnl_pct, "Stop Loss Hit"

        # Check if hit TPs
        if current_price >= tp3:
            return "CLOSED_WIN", pnl_pct, "TP3 Hit (Full Target)"
        elif current_price >= tp2:
            return "PARTIAL_WIN", pnl_pct, "TP2 Hit"
        elif current_price >= tp1:
            return "PARTIAL_WIN", pnl_pct, "TP1 Hit"

        return "OPEN", pnl_pct, "In Progress"

    else:  # SHORT
        pnl_pct = ((entry - current_price) / entry) * 100

        # Check if hit SL
        if current_price >= sl:
            return "CLOSED_LOSS", pnl_pct, "Stop Loss Hit"

        # Check if hit TPs
        if current_price <= tp3:
            return "CLOSED_WIN", pnl_pct, "TP3 Hit (Full Target)"
        elif current_price <= tp2:
            return "PARTIAL_WIN", pnl_pct, "TP2 Hit"
        elif current_price <= tp1:
            return "PARTIAL_WIN", pnl_pct, "TP1 Hit"

        return "OPEN", pnl_pct, "In Progress"

def analyze_trade_outcome(trade, outcome, pnl_pct):
    """Provide analysis and lessons learned"""
    analysis = []

    if outcome == "CLOSED_WIN":
        analysis.append("WINNER! Trade hit full target TP3.")
        analysis.append(f"Profit: {pnl_pct:+.2f}%")
        analysis.append("What went right:")
        for signal in trade['signals']:
            analysis.append(f"  - {signal} played out as expected")
        analysis.append("Key lesson: Strategy is working, maintain discipline")

    elif outcome == "PARTIAL_WIN":
        analysis.append("PARTIAL WIN! Trade hit partial target.")
        analysis.append(f"Current profit: {pnl_pct:+.2f}%")
        analysis.append("Recommendation: Move SL to breakeven if not done already")
        analysis.append("Let remaining position run to higher targets")

    elif outcome == "CLOSED_LOSS":
        analysis.append("LOSS. Trade hit stop loss.")
        analysis.append(f"Loss: {pnl_pct:+.2f}%")
        analysis.append("What to review:")
        analysis.append("  - Was market condition suitable for the strategy?")
        analysis.append("  - Was there news/event that caused reversal?")
        analysis.append("  - Did price respect the technical levels?")
        analysis.append("Key lesson: Losses are part of trading, protect capital with SL")

    elif outcome == "OPEN":
        if pnl_pct > 0:
            analysis.append("Trade currently in profit.")
            analysis.append(f"Unrealized P&L: {pnl_pct:+.2f}%")
            analysis.append("Recommendation: Be patient, let it reach targets")
        else:
            analysis.append("Trade currently in drawdown.")
            analysis.append(f"Unrealized P&L: {pnl_pct:+.2f}%")
            analysis.append("Recommendation: Trust your stop loss, don't move it wider")

    return "\n".join(analysis)

def format_performance_email(trades_data):
    """Format performance tracking email"""
    now = datetime.now()

    open_trades = [t for t in trades_data if t['current_status'] in ['OPEN', 'PARTIAL_WIN']]
    closed_wins = [t for t in trades_data if t['current_status'] == 'CLOSED_WIN']
    closed_losses = [t for t in trades_data if t['current_status'] == 'CLOSED_LOSS']

    total_pnl = sum(t['current_pnl'] for t in closed_wins + closed_losses)
    win_rate = len(closed_wins) / len(closed_wins + closed_losses) * 100 if (closed_wins or closed_losses) else 0

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
            margin: 0 0 10px 0;
            font-size: 36px;
            font-weight: 600;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            padding: 25px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stat-box {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .positive {{ color: #10b981; }}
        .negative {{ color: #ef4444; }}
        .neutral {{ color: #667eea; }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 24px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .trade-card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .trade-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .symbol {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .status {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
        }}
        .status-open {{ background: #dbeafe; color: #1e40af; }}
        .status-win {{ background: #d1fae5; color: #065f46; }}
        .status-loss {{ background: #fee2e2; color: #991b1b; }}
        .status-partial {{ background: #fef3c7; color: #92400e; }}
        .pnl-display {{
            font-size: 28px;
            font-weight: bold;
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 15px 0;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-label {{
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }}
        .analysis {{
            background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
            border-left: 4px solid #7c3aed;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
        }}
        .analysis-title {{
            font-weight: bold;
            color: #5b21b6;
            margin-bottom: 10px;
        }}
        .analysis-text {{
            color: #4c1d95;
            line-height: 1.6;
            white-space: pre-line;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 13px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Trade Performance Report</h1>
            <p>{now.strftime('%A, %B %d, %Y - %I:%M %p')}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value neutral">{len(trades_data)}</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat-box">
                <div class="stat-value positive">{len(closed_wins)}</div>
                <div class="stat-label">Winners</div>
            </div>
            <div class="stat-box">
                <div class="stat-value negative">{len(closed_losses)}</div>
                <div class="stat-label">Losers</div>
            </div>
            <div class="stat-box">
                <div class="stat-value {'positive' if total_pnl > 0 else 'negative'}">{total_pnl:+.1f}%</div>
                <div class="stat-label">Total P&L</div>
            </div>
        </div>

        <div class="content">
"""

    # Open Trades
    if open_trades:
        html += """
            <div class="section">
                <div class="section-title">Open Trades</div>
"""
        for trade in open_trades:
            status_class = 'status-partial' if trade['current_status'] == 'PARTIAL_WIN' else 'status-open'
            pnl_class = 'positive' if trade['current_pnl'] > 0 else 'negative' if trade['current_pnl'] < 0 else 'neutral'

            html += f"""
                <div class="trade-card">
                    <div class="trade-header">
                        <div class="symbol">{trade['symbol']} - {trade['direction']}</div>
                        <div class="status {status_class}">{trade['status_message']}</div>
                    </div>

                    <div class="pnl-display {pnl_class}">
                        {trade['current_pnl']:+.2f}% Unrealized P&L
                    </div>

                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-label">Entry</div>
                            <div class="metric-value">${trade['entry']:.5f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Current</div>
                            <div class="metric-value">${trade['current_price']:.5f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Stop Loss</div>
                            <div class="metric-value">${trade['stop_loss']:.5f}</div>
                        </div>
                    </div>

                    <div class="analysis">
                        <div class="analysis-title">Analysis & Recommendations</div>
                        <div class="analysis-text">{trade['analysis']}</div>
                    </div>
                </div>
"""

        html += "</div>"

    # Closed Trades
    if closed_wins or closed_losses:
        html += f"""
            <div class="section">
                <div class="section-title">Closed Trades</div>
                <div style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
                    <strong>Win Rate:</strong> {win_rate:.1f}%
                    ({len(closed_wins)} wins / {len(closed_losses)} losses)
                </div>
"""

        for trade in closed_wins + closed_losses:
            status_class = 'status-win' if trade['current_status'] == 'CLOSED_WIN' else 'status-loss'
            pnl_class = 'positive' if trade['current_pnl'] > 0 else 'negative'

            html += f"""
                <div class="trade-card">
                    <div class="trade-header">
                        <div class="symbol">{trade['symbol']} - {trade['direction']}</div>
                        <div class="status {status_class}">{trade['status_message']}</div>
                    </div>

                    <div class="pnl-display {pnl_class}">
                        {trade['current_pnl']:+.2f}% Realized P&L
                    </div>

                    <div class="analysis">
                        <div class="analysis-title">Post-Trade Analysis</div>
                        <div class="analysis-text">{trade['analysis']}</div>
                    </div>
                </div>
"""

        html += "</div>"

    html += """
        </div>

        <div class="footer">
            <p><strong>Performance tracking is automatic.</strong></p>
            <p>Run this script anytime to get updated trade status.</p>
            <p>Reply with trade outcomes if you close manually for accurate tracking.</p>
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
            <p>PropShop Trading Intelligence System | Real-Time Performance Tracking</p>
        </div>
    </div>
</body>
</html>
"""

    return html

# Main execution
print("="*80)
print("TRADE PERFORMANCE TRACKER")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

# Load trades
with open(TRADES_LOG_FILE, 'r') as f:
    trades = json.load(f)

print(f"\nTracking {len(trades)} trades...")
print()

trades_data = []

for trade in trades:
    print(f"Checking {trade['symbol']:10s}...", end=" ")

    current_status, current_pnl, status_message = check_trade_status(trade)
    current_price = get_current_price(trade['symbol'])

    # Update trade status
    trade['current_status'] = current_status
    trade['current_pnl'] = current_pnl
    trade['status_message'] = status_message
    trade['current_price'] = current_price if current_price else trade['entry']
    trade['checked_at'] = datetime.now().isoformat()

    # Generate analysis
    analysis = analyze_trade_outcome(trade, current_status, current_pnl)
    trade['analysis'] = analysis

    trades_data.append(trade)

    print(f"[{current_status}] {current_pnl:+.2f}% - {status_message}")

# Update log file
with open(TRADES_LOG_FILE, 'w') as f:
    json.dump(trades, f, indent=2)

print(f"\n[OK] Updated {TRADES_LOG_FILE}")

# Calculate stats
open_trades = [t for t in trades_data if t['current_status'] in ['OPEN', 'PARTIAL_WIN']]
closed_trades = [t for t in trades_data if t['current_status'] in ['CLOSED_WIN', 'CLOSED_LOSS']]

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"Open: {len(open_trades)} | Closed: {len(closed_trades)}")

if closed_trades:
    wins = [t for t in closed_trades if t['current_status'] == 'CLOSED_WIN']
    losses = [t for t in closed_trades if t['current_status'] == 'CLOSED_LOSS']
    print(f"Winners: {len(wins)} | Losers: {len(losses)}")

    total_pnl = sum(t['current_pnl'] for t in closed_trades)
    print(f"Total P&L: {total_pnl:+.2f}%")

# Send email
print(f"\nSending performance report to {EMAIL_TO}...")
subject = f"Trade Performance: {len(open_trades)} Open | {len(closed_trades)} Closed"
html_message = format_performance_email(trades_data)

if send_email(subject, html_message):
    print("[SUCCESS] Performance report sent!")
else:
    print("[FAILED] Email not sent")

mt5.shutdown()
print("\n[DONE]")
