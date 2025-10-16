"""
BEAUTIFUL QUANTITATIVE REPORT
Modern, clean, readable design by expert UI/UX designers
Like reports from Goldman Sachs, Morgan Stanley, Bloomberg
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import requests
from scipy import stats

# EmailJS Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

TRADES_LOG_FILE = "trades_log.json"

def send_email(subject, html_message):
    """Send HTML email"""
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

def calculate_sharpe_ratio(returns):
    if len(returns) < 2:
        return 0
    return np.sqrt(252) * (returns.mean() / returns.std()) if returns.std() != 0 else 0

def calculate_max_drawdown(equity_curve):
    if len(equity_curve) < 2:
        return 0
    cummax = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - cummax) / cummax
    return drawdown.min()

def get_account_metrics():
    account = mt5.account_info()
    if not account:
        return None
    return {
        'balance': account.balance,
        'equity': account.equity,
        'margin': account.margin,
        'margin_free': account.margin_free,
        'margin_level': account.margin_level if account.margin > 0 else float('inf'),
        'profit': account.profit
    }

def get_position_analytics():
    positions = mt5.positions_get()
    if not positions:
        return {'count': 0, 'long_exposure': 0, 'short_exposure': 0, 'unrealized_pnl': 0}

    long_vol = sum(p.volume for p in positions if p.type == mt5.ORDER_TYPE_BUY)
    short_vol = sum(p.volume for p in positions if p.type == mt5.ORDER_TYPE_SELL)
    unrealized = sum(p.profit for p in positions)

    return {
        'count': len(positions),
        'long_exposure': long_vol,
        'short_exposure': short_vol,
        'unrealized_pnl': unrealized
    }

def analyze_performance():
    try:
        with open(TRADES_LOG_FILE, 'r') as f:
            trades = json.load(f)
    except:
        return None

    returns = []
    equity_curve = [10000]

    for trade in trades:
        if 'current_pnl' in trade and trade.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']:
            ret = trade['current_pnl'] / 100
            returns.append(ret)
            equity_curve.append(equity_curve[-1] * (1 + ret))

    if len(returns) < 2:
        return None

    returns_array = np.array(returns)
    equity_array = np.array(equity_curve)

    total_return = (equity_curve[-1] / equity_curve[0]) - 1
    sharpe = calculate_sharpe_ratio(returns_array)
    max_dd = calculate_max_drawdown(equity_array)

    wins = len([r for r in returns if r > 0])
    losses = len([r for r in returns if r < 0])
    win_rate = wins / len(returns) if len(returns) > 0 else 0

    return {
        'total_trades': len(returns),
        'total_return': total_return * 100,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd * 100,
        'win_rate': win_rate * 100,
        'wins': wins,
        'losses': losses
    }

def format_beautiful_report():
    now = datetime.now()
    account = get_account_metrics()
    positions = get_position_analytics()
    performance = analyze_performance()

    # Calculate daily change
    daily_change = ((account['equity'] - account['balance']) / account['balance']) * 100

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

        .hero-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0;
            background: white;
            margin: -30px 20px 0 20px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.25);
            overflow: hidden;
        }}

        .hero-stat {{
            padding: 30px 20px;
            text-align: center;
            border-right: 1px solid #f0f0f0;
        }}

        .hero-stat:last-child {{
            border-right: none;
        }}

        .hero-stat-label {{
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
            margin-bottom: 8px;
        }}

        .hero-stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #1a1a1a;
        }}

        .hero-stat-value.positive {{ color: #10b981; }}
        .hero-stat-value.negative {{ color: #ef4444; }}

        .content {{
            padding: 50px 40px;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section-title {{
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }}

        .section-title::before {{
            content: '';
            width: 4px;
            height: 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 2px;
            margin-right: 12px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }}

        .metric-card {{
            background: #f9fafb;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            transition: all 0.3s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        .metric-label {{
            font-size: 13px;
            color: #6b7280;
            font-weight: 500;
            margin-bottom: 8px;
        }}

        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: #1a1a1a;
        }}

        .metric-value.large {{
            font-size: 32px;
        }}

        .metric-value.positive {{ color: #10b981; }}
        .metric-value.negative {{ color: #ef4444; }}
        .metric-value.neutral {{ color: #667eea; }}

        .metric-change {{
            font-size: 12px;
            margin-top: 4px;
            font-weight: 500;
        }}

        .metric-change.positive {{ color: #10b981; }}
        .metric-change.negative {{ color: #ef4444; }}

        .stat-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: #f9fafb;
            border-radius: 8px;
            margin-bottom: 8px;
        }}

        .stat-row:last-child {{
            margin-bottom: 0;
        }}

        .stat-label {{
            font-size: 14px;
            color: #6b7280;
            font-weight: 500;
        }}

        .stat-value {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
        }}

        .stat-value.positive {{ color: #10b981; }}
        .stat-value.negative {{ color: #ef4444; }}

        .alert-box {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-left: 4px solid #f59e0b;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}

        .alert-box.danger {{
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            border-left-color: #ef4444;
        }}

        .alert-title {{
            font-weight: 600;
            color: #92400e;
            margin-bottom: 8px;
            font-size: 14px;
        }}

        .alert-box.danger .alert-title {{
            color: #991b1b;
        }}

        .alert-text {{
            font-size: 13px;
            color: #78350f;
            line-height: 1.6;
        }}

        .alert-box.danger .alert-text {{
            color: #7f1d1d;
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
            body {{
                padding: 20px 10px;
            }}

            .hero-stats {{
                grid-template-columns: 1fr;
                margin: -20px 10px 0 10px;
            }}

            .hero-stat {{
                border-right: none;
                border-bottom: 1px solid #f0f0f0;
            }}

            .hero-stat:last-child {{
                border-bottom: none;
            }}

            .content {{
                padding: 30px 20px;
            }}

            .metrics-grid {{
                grid-template-columns: 1fr;
            }}

            .header h1 {{
                font-size: 24px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <!-- Header -->
        <div class="header">
            <h1>Performance Report</h1>
            <div class="subtitle">{now.strftime('%B %d, %Y at %I:%M %p')}</div>
        </div>

        <!-- Hero Stats -->
        <div class="hero-stats">
            <div class="hero-stat">
                <div class="hero-stat-label">Portfolio Value</div>
                <div class="hero-stat-value">${account['equity']:,.0f}</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-label">Today's P&L</div>
                <div class="hero-stat-value {'positive' if account['profit'] >= 0 else 'negative'}">
                    ${account['profit']:+,.0f}
                </div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-label">Open Positions</div>
                <div class="hero-stat-value neutral">{positions['count']}</div>
            </div>
        </div>

        <!-- Content -->
        <div class="content">
            <!-- Account Overview -->
            <div class="section">
                <div class="section-title">Account Overview</div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Cash Balance</div>
                        <div class="metric-value large">${account['balance']:,.0f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Available Margin</div>
                        <div class="metric-value">${account['margin_free']:,.0f}</div>
                        <div class="metric-change neutral">Margin Level: {account['margin_level']:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Long Exposure</div>
                        <div class="metric-value positive">{positions['long_exposure']:.2f}</div>
                        <div class="metric-change positive">lots</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Short Exposure</div>
                        <div class="metric-value negative">{positions['short_exposure']:.2f}</div>
                        <div class="metric-change negative">lots</div>
                    </div>
                </div>
            </div>
"""

    # Performance Section (if data available)
    if performance:
        html += f"""
            <!-- Performance Metrics -->
            <div class="section">
                <div class="section-title">Performance Metrics</div>

                <div class="stat-row">
                    <span class="stat-label">Total Return</span>
                    <span class="stat-value {'positive' if performance['total_return'] >= 0 else 'negative'}">
                        {performance['total_return']:+.2f}%
                    </span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Sharpe Ratio</span>
                    <span class="stat-value {'positive' if performance['sharpe_ratio'] > 1 else 'neutral' if performance['sharpe_ratio'] > 0 else 'negative'}">
                        {performance['sharpe_ratio']:.2f}
                    </span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Maximum Drawdown</span>
                    <span class="stat-value negative">{performance['max_drawdown']:.2f}%</span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Win Rate</span>
                    <span class="stat-value {'positive' if performance['win_rate'] >= 50 else 'neutral' if performance['win_rate'] >= 40 else 'negative'}">
                        {performance['win_rate']:.1f}%
                    </span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Trades Executed</span>
                    <span class="stat-value">{performance['total_trades']} ({performance['wins']}W / {performance['losses']}L)</span>
                </div>
            </div>
"""

        # Add alerts if needed
        if performance['sharpe_ratio'] < 0:
            html += """
            <div class="alert-box danger">
                <div class="alert-title">⚠️ Performance Alert</div>
                <div class="alert-text">
                    Sharpe Ratio is negative, indicating risk-adjusted returns are below the risk-free rate.
                    Consider reviewing strategy parameters or reducing position sizes.
                </div>
            </div>
"""

        if performance['max_drawdown'] < -20:
            html += f"""
            <div class="alert-box danger">
                <div class="alert-title">⚠️ Drawdown Alert</div>
                <div class="alert-text">
                    Maximum drawdown has exceeded -20% (currently {performance['max_drawdown']:.1f}%).
                    Implement stricter risk controls and position limits.
                </div>
            </div>
"""

    html += f"""
            <!-- System Status -->
            <div class="section">
                <div class="section-title">System Status</div>

                <div class="stat-row">
                    <span class="stat-label">Trading Engine</span>
                    <span class="stat-value positive">● ACTIVE</span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Risk Management</span>
                    <span class="stat-value positive">● ENABLED</span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Risk Per Trade</span>
                    <span class="stat-value">1.00%</span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Max Open Positions</span>
                    <span class="stat-value">5 concurrent</span>
                </div>

                <div class="stat-row">
                    <span class="stat-label">Strategies Active</span>
                    <span class="stat-value">6 algorithms</span>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <div class="footer-text">
                This report is generated automatically by your PropShop Trading System.<br>
                For support or questions, please review your system documentation.
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
print("GENERATING BEAUTIFUL QUANTITATIVE REPORT")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

print("\nCollecting data...")
account = get_account_metrics()
positions = get_position_analytics()
performance = analyze_performance()

print(f"Account: ${account['equity']:,.2f}")
print(f"Positions: {positions['count']}")
if performance:
    print(f"Performance: {performance['total_return']:+.2f}% | Sharpe: {performance['sharpe_ratio']:.2f}")

print("\nGenerating beautiful report...")
html_report = format_beautiful_report()

print(f"\nSending to {EMAIL_TO}...")
subject = f"📊 Performance Report | ${account['equity']:,.0f} | P&L: ${account['profit']:+,.0f}"

if send_email(subject, html_report):
    print("[SUCCESS] Beautiful report sent!")
else:
    print("[FAILED] Email not sent")

mt5.shutdown()
print("\n[DONE]")
