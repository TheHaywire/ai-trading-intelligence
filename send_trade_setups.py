"""
Send Trade Setups Email - Professional format without embedded images
Charts saved locally in /charts folder for your review
"""

import json
from datetime import datetime
import requests

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
        if response.status_code == 200:
            print(f"[OK] Email sent")
            return True
        else:
            print(f"[FAIL] Email failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False

def calculate_rr_ratios(trade):
    """Calculate all R:R ratios"""
    risk = abs(trade['entry'] - trade['stop_loss'])
    rr1 = abs(trade['tp1'] - trade['entry']) / risk
    rr2 = abs(trade['tp2'] - trade['entry']) / risk
    rr3 = abs(trade['tp3'] - trade['entry']) / risk
    return rr1, rr2, rr3

def format_trade_email(trades):
    """Format professional HTML email"""
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
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 36px;
            font-weight: 600;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.95;
            font-size: 18px;
        }}
        .stats {{
            background: rgba(255,255,255,0.15);
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 16px;
        }}
        .content {{
            padding: 30px;
        }}
        .trade {{
            background: white;
            border: 3px solid #667eea;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .trade-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .symbol {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .direction {{
            font-size: 24px;
            font-weight: bold;
            padding: 12px 25px;
            border-radius: 25px;
            color: white;
        }}
        .long {{ background: linear-gradient(135deg, #34d399 0%, #10b981 100%); }}
        .short {{ background: linear-gradient(135deg, #f87171 0%, #ef4444 100%); }}
        .levels {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .level {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 10px;
            padding: 15px;
            border-left: 5px solid #667eea;
        }}
        .level-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        .level-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .entry {{ border-left-color: #fbbf24; }}
        .sl {{ border-left-color: #ef4444; }}
        .tp {{ border-left-color: #10b981; }}
        .signals {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 20px 0;
        }}
        .signal {{
            background: #667eea;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }}
        .risk {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-left: 5px solid #f59e0b;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .risk-title {{
            font-size: 16px;
            font-weight: bold;
            color: #92400e;
            margin-bottom: 10px;
        }}
        .risk-item {{
            margin: 8px 0;
            color: #78350f;
        }}
        .action {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin: 30px 0;
        }}
        .action h3 {{
            margin: 0 0 10px 0;
            font-size: 20px;
        }}
        .action p {{
            margin: 5px 0;
            opacity: 0.95;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 25px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
        .footer p {{
            margin: 8px 0;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Trading Intelligence Report</h1>
            <p>{now.strftime('%A, %B %d, %Y')}</p>
            <p>{now.strftime('%I:%M %p')}</p>
            <div class="stats">
                {len(trades)} High-Probability Trade Setups Ready for Execution
            </div>
        </div>

        <div class="content">
"""

    for i, trade in enumerate(trades, 1):
        direction_class = 'long' if trade['direction'] == 'LONG' else 'short'

        # Calculate R:R ratios if not present
        rr1, rr2, rr3 = calculate_rr_ratios(trade)

        html += f"""
            <div class="trade">
                <div class="trade-header">
                    <div class="symbol">#{i} {trade['symbol']}</div>
                    <div class="direction {direction_class}">{trade['direction']}</div>
                </div>

                <div class="signals">
"""
        for signal in trade['signals']:
            html += f'<span class="signal">{signal}</span>'

        html += f"""
                </div>

                <div class="levels">
                    <div class="level entry">
                        <div class="level-label">Entry Price</div>
                        <div class="level-value">${trade['entry']:.5f}</div>
                    </div>
                    <div class="level sl">
                        <div class="level-label">Stop Loss</div>
                        <div class="level-value">${trade['stop_loss']:.5f}</div>
                    </div>
                    <div class="level tp">
                        <div class="level-label">Take Profit 1 (50%)</div>
                        <div class="level-value">${trade['tp1']:.5f}</div>
                    </div>
                    <div class="level tp">
                        <div class="level-label">Take Profit 2 (30%)</div>
                        <div class="level-value">${trade['tp2']:.5f}</div>
                    </div>
                    <div class="level tp">
                        <div class="level-label">Take Profit 3 (20%)</div>
                        <div class="level-value">${trade['tp3']:.5f}</div>
                    </div>
                    <div class="level">
                        <div class="level-label">Risk:Reward Ratio</div>
                        <div class="level-value">1:{rr1:.1f} / 1:{rr2:.1f} / 1:{rr3:.1f}</div>
                    </div>
                </div>

                <div class="risk">
                    <div class="risk-title">Risk Management Guidelines</div>
                    <div class="risk-item">Risk 1% of account per trade</div>
                    <div class="risk-item">Move stop loss to breakeven after TP1 is hit</div>
                    <div class="risk-item">Close 50% at TP1, 30% at TP2, let 20% run to TP3</div>
                    <div class="risk-item">Trail stop loss if price moves strongly in your favor</div>
                </div>
            </div>
"""

    html += """
            <div class="action">
                <h3>Next Steps</h3>
                <p>1. Review each trade setup carefully</p>
                <p>2. Check current market conditions</p>
                <p>3. Decide which trades align with your strategy</p>
                <p>4. Execute trades with proper position sizing</p>
                <p>5. Reply to this email with your decisions for performance tracking</p>
            </div>
        </div>

        <div class="footer">
            <p><strong>Important Disclaimer:</strong></p>
            <p>These are algorithmic recommendations based on technical analysis of historical data.</p>
            <p>Always perform your own analysis and never risk more than you can afford to lose.</p>
            <p>Past performance does not guarantee future results.</p>
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
            <p><strong>Charts Available:</strong> Check your local folder for detailed charts with all indicators</p>
            <p>Location: C:/Users/manan/OneDrive/Desktop/PropShop- IF/charts/</p>
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
            <p>Generated by PropShop Trading Intelligence System</p>
            <p>Powered by MetaTrader 5 | Based on validated strategies with 13.9% avg return</p>
        </div>
    </div>
</body>
</html>
"""

    return html

# Load trades
print("="*80)
print("SENDING TRADE SETUPS EMAIL")
print("="*80)

with open(TRADES_LOG_FILE, 'r') as f:
    trades = json.load(f)

pending_trades = [t for t in trades if t['status'] == 'PENDING']

print(f"\nFound {len(pending_trades)} pending trade setups")
print(f"\nTrades:")
for i, trade in enumerate(pending_trades, 1):
    print(f"  {i}. {trade['symbol']:10s} {trade['direction']:5s} @ ${trade['entry']:.5f} | R:R 1:{trade['rr1']:.1f}")

# Send email
subject = f"Trading Intelligence: {len(pending_trades)} Trade Setups Ready"
html_message = format_trade_email(pending_trades)

print(f"\nSending email to {EMAIL_TO}...")
if send_email(subject, html_message):
    print("\n[SUCCESS] Email sent! Check your inbox.")
else:
    print("\n[FAILED] Email not sent.")
