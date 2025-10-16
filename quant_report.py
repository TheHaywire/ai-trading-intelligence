"""
QUANTITATIVE PERFORMANCE REPORT
Institutional-grade analytics like Renaissance Technologies, Citadel, Two Sigma
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

def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """Calculate annualized Sharpe ratio"""
    if len(returns) < 2:
        return 0
    excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
    return np.sqrt(252) * (excess_returns.mean() / excess_returns.std()) if excess_returns.std() != 0 else 0

def calculate_sortino_ratio(returns, risk_free_rate=0.02):
    """Calculate Sortino ratio (downside deviation)"""
    if len(returns) < 2:
        return 0
    excess_returns = returns - (risk_free_rate / 252)
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
    return np.sqrt(252) * (excess_returns.mean() / downside_std) if downside_std != 0 else 0

def calculate_max_drawdown(equity_curve):
    """Calculate maximum drawdown"""
    if len(equity_curve) < 2:
        return 0
    cummax = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - cummax) / cummax
    return drawdown.min()

def calculate_var(returns, confidence=0.95):
    """Calculate Value at Risk"""
    if len(returns) < 2:
        return 0
    return np.percentile(returns, (1 - confidence) * 100)

def calculate_cvar(returns, confidence=0.95):
    """Calculate Conditional Value at Risk (Expected Shortfall)"""
    if len(returns) < 2:
        return 0
    var = calculate_var(returns, confidence)
    return returns[returns <= var].mean()

def calculate_calmar_ratio(returns, max_dd):
    """Calculate Calmar ratio (return / max drawdown)"""
    if max_dd == 0:
        return 0
    annual_return = (1 + returns.mean()) ** 252 - 1
    return annual_return / abs(max_dd)

def get_account_metrics():
    """Get current account state"""
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
    """Analyze current open positions"""
    positions = mt5.positions_get()
    if not positions:
        return {
            'count': 0,
            'total_volume': 0,
            'long_exposure': 0,
            'short_exposure': 0,
            'net_exposure': 0,
            'avg_holding_time': 0,
            'unrealized_pnl': 0
        }

    long_vol = sum(p.volume for p in positions if p.type == mt5.ORDER_TYPE_BUY)
    short_vol = sum(p.volume for p in positions if p.type == mt5.ORDER_TYPE_SELL)
    total_vol = long_vol + short_vol
    unrealized = sum(p.profit for p in positions)

    # Calculate average holding time
    now = datetime.now().timestamp()
    holding_times = [(now - p.time) / 3600 for p in positions]  # Hours
    avg_holding = np.mean(holding_times) if holding_times else 0

    return {
        'count': len(positions),
        'total_volume': total_vol,
        'long_exposure': long_vol,
        'short_exposure': short_vol,
        'net_exposure': long_vol - short_vol,
        'avg_holding_time': avg_holding,
        'unrealized_pnl': unrealized
    }

def analyze_trades_performance():
    """Analyze historical trade performance"""
    try:
        with open(TRADES_LOG_FILE, 'r') as f:
            trades = json.load(f)
    except:
        return None

    if not trades:
        return None

    # Extract returns
    returns = []
    equity_curve = [10000]  # Start with $10k

    for trade in trades:
        if 'current_pnl' in trade and trade.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']:
            ret = trade['current_pnl'] / 100  # Convert % to decimal
            returns.append(ret)
            equity_curve.append(equity_curve[-1] * (1 + ret))

    if len(returns) < 2:
        return None

    returns_array = np.array(returns)
    equity_array = np.array(equity_curve)

    # Calculate metrics
    total_return = (equity_curve[-1] / equity_curve[0]) - 1
    avg_return = returns_array.mean()
    volatility = returns_array.std()
    sharpe = calculate_sharpe_ratio(returns_array)
    sortino = calculate_sortino_ratio(returns_array)
    max_dd = calculate_max_drawdown(equity_array)
    calmar = calculate_calmar_ratio(returns_array, max_dd)
    var_95 = calculate_var(returns_array, 0.95)
    cvar_95 = calculate_cvar(returns_array, 0.95)

    # Win rate
    wins = len([r for r in returns if r > 0])
    losses = len([r for r in returns if r < 0])
    win_rate = wins / len(returns) if len(returns) > 0 else 0

    # Profit factor
    gross_profit = sum([r for r in returns if r > 0])
    gross_loss = abs(sum([r for r in returns if r < 0]))
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')

    # Average win/loss
    avg_win = np.mean([r for r in returns if r > 0]) if wins > 0 else 0
    avg_loss = np.mean([r for r in returns if r < 0]) if losses > 0 else 0

    # Expectancy
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    return {
        'total_trades': len(returns),
        'total_return': total_return * 100,
        'avg_return': avg_return * 100,
        'volatility': volatility * 100,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_dd * 100,
        'calmar_ratio': calmar,
        'var_95': var_95 * 100,
        'cvar_95': cvar_95 * 100,
        'win_rate': win_rate * 100,
        'profit_factor': profit_factor,
        'avg_win': avg_win * 100,
        'avg_loss': avg_loss * 100,
        'expectancy': expectancy * 100,
        'wins': wins,
        'losses': losses
    }

def format_quant_report():
    """Format institutional quantitative report"""
    now = datetime.now()
    account = get_account_metrics()
    positions = get_position_analytics()
    performance = analyze_trades_performance()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background-color: #0a0a0a;
            color: #00ff00;
            margin: 0;
            padding: 20px;
            font-size: 12px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: #1a1a1a;
            border: 2px solid #00ff00;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #00ff00;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            letter-spacing: 3px;
        }}
        .timestamp {{
            color: #00aa00;
            margin-top: 5px;
        }}
        .section {{
            margin: 20px 0;
            border: 1px solid #00aa00;
            padding: 15px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            text-decoration: underline;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .metric {{
            background: #0d0d0d;
            padding: 10px;
            border-left: 3px solid #00ff00;
        }}
        .metric-label {{
            font-size: 10px;
            color: #00aa00;
        }}
        .metric-value {{
            font-size: 18px;
            font-weight: bold;
            margin-top: 5px;
        }}
        .positive {{ color: #00ff00; }}
        .negative {{ color: #ff0000; }}
        .neutral {{ color: #ffff00; }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .table td {{
            padding: 8px;
            border-bottom: 1px solid #00aa00;
        }}
        .table td:first-child {{
            color: #00aa00;
            width: 40%;
        }}
        .greek {{
            color: #00ffff;
            font-style: italic;
        }}
        .alert {{
            background: #331100;
            border-left: 5px solid #ff6600;
            padding: 10px;
            margin: 10px 0;
            color: #ff6600;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 2px solid #00ff00;
            color: #00aa00;
            font-size: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>QUANTITATIVE PERFORMANCE REPORT</h1>
            <div class="timestamp">
                {now.strftime('%Y-%m-%d %H:%M:%S UTC')} | CLASSIFICATION: CONFIDENTIAL
            </div>
        </div>

        <!-- ACCOUNT METRICS -->
        <div class="section">
            <div class="section-title">§1. ACCOUNT METRICS</div>
            <div class="metric-grid">
                <div class="metric">
                    <div class="metric-label">NAV (Net Asset Value)</div>
                    <div class="metric-value">${account['equity']:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">AUM (Cash Balance)</div>
                    <div class="metric-value">${account['balance']:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Unrealized P&L</div>
                    <div class="metric-value {'positive' if account['profit'] > 0 else 'negative' if account['profit'] < 0 else 'neutral'}">
                        ${account['profit']:+,.2f}
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">Margin Utilization</div>
                    <div class="metric-value">${account['margin']:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Available Capital</div>
                    <div class="metric-value">${account['margin_free']:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Leverage Ratio</div>
                    <div class="metric-value">{account['margin_level']:.2f}%</div>
                </div>
            </div>
        </div>

        <!-- PORTFOLIO EXPOSURE -->
        <div class="section">
            <div class="section-title">§2. PORTFOLIO EXPOSURE ANALYSIS</div>
            <table class="table">
                <tr>
                    <td>Open Positions (n)</td>
                    <td>{positions['count']}</td>
                </tr>
                <tr>
                    <td>Total Volume (Σ lots)</td>
                    <td>{positions['total_volume']:.2f}</td>
                </tr>
                <tr>
                    <td>Long Exposure (β<sub>L</sub>)</td>
                    <td class="positive">{positions['long_exposure']:.2f} lots</td>
                </tr>
                <tr>
                    <td>Short Exposure (β<sub>S</sub>)</td>
                    <td class="negative">{positions['short_exposure']:.2f} lots</td>
                </tr>
                <tr>
                    <td>Net Exposure (β<sub>net</sub>)</td>
                    <td class="{'positive' if positions['net_exposure'] > 0 else 'negative' if positions['net_exposure'] < 0 else 'neutral'}">
                        {positions['net_exposure']:+.2f} lots
                    </td>
                </tr>
                <tr>
                    <td>Avg Holding Period (τ)</td>
                    <td>{positions['avg_holding_time']:.1f} hours</td>
                </tr>
                <tr>
                    <td>Mark-to-Market P&L</td>
                    <td class="{'positive' if positions['unrealized_pnl'] > 0 else 'negative' if positions['unrealized_pnl'] < 0 else 'neutral'}">
                        ${positions['unrealized_pnl']:+,.2f}
                    </td>
                </tr>
            </table>
        </div>
"""

    # Performance analytics (if we have trade history)
    if performance:
        html += f"""
        <!-- STATISTICAL PERFORMANCE METRICS -->
        <div class="section">
            <div class="section-title">§3. RISK-ADJUSTED PERFORMANCE METRICS</div>

            <div class="metric-grid">
                <div class="metric">
                    <div class="metric-label">Total Return (R<sub>total</sub>)</div>
                    <div class="metric-value {'positive' if performance['total_return'] > 0 else 'negative'}">
                        {performance['total_return']:+.2f}%
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">Average Return (μ)</div>
                    <div class="metric-value {'positive' if performance['avg_return'] > 0 else 'negative'}">
                        {performance['avg_return']:+.3f}%
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">Volatility (σ)</div>
                    <div class="metric-value neutral">{performance['volatility']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label greek">Sharpe Ratio (S<sub>R</sub>)</div>
                    <div class="metric-value {'positive' if performance['sharpe_ratio'] > 1 else 'neutral' if performance['sharpe_ratio'] > 0 else 'negative'}">
                        {performance['sharpe_ratio']:.3f}
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label greek">Sortino Ratio (S<sub>o</sub>)</div>
                    <div class="metric-value {'positive' if performance['sortino_ratio'] > 1 else 'neutral' if performance['sortino_ratio'] > 0 else 'negative'}">
                        {performance['sortino_ratio']:.3f}
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">Calmar Ratio (C<sub>R</sub>)</div>
                    <div class="metric-value {'positive' if performance['calmar_ratio'] > 1 else 'neutral' if performance['calmar_ratio'] > 0 else 'negative'}">
                        {performance['calmar_ratio']:.3f}
                    </div>
                </div>
            </table>
        </div>

        <!-- RISK METRICS -->
        <div class="section">
            <div class="section-title">§4. RISK ANALYTICS</div>
            <table class="table">
                <tr>
                    <td>Maximum Drawdown (MDD)</td>
                    <td class="negative">{performance['max_drawdown']:.2f}%</td>
                </tr>
                <tr>
                    <td>Value at Risk (VaR<sub>95</sub>)</td>
                    <td class="negative">{performance['var_95']:.3f}%</td>
                </tr>
                <tr>
                    <td>Conditional VaR (CVaR<sub>95</sub>)</td>
                    <td class="negative">{performance['cvar_95']:.3f}%</td>
                </tr>
                <tr>
                    <td>Profit Factor (PF)</td>
                    <td class="{'positive' if performance['profit_factor'] > 1.5 else 'neutral' if performance['profit_factor'] > 1 else 'negative'}">
                        {performance['profit_factor']:.3f}
                    </td>
                </tr>
                <tr>
                    <td>Mathematical Expectancy (E[X])</td>
                    <td class="{'positive' if performance['expectancy'] > 0 else 'negative'}">
                        {performance['expectancy']:+.3f}%
                    </td>
                </tr>
            </table>
        </div>

        <!-- TRADE STATISTICS -->
        <div class="section">
            <div class="section-title">§5. EXECUTION STATISTICS</div>
            <table class="table">
                <tr>
                    <td>Total Trades Executed (N)</td>
                    <td>{performance['total_trades']}</td>
                </tr>
                <tr>
                    <td>Winning Trades (W)</td>
                    <td class="positive">{performance['wins']}</td>
                </tr>
                <tr>
                    <td>Losing Trades (L)</td>
                    <td class="negative">{performance['losses']}</td>
                </tr>
                <tr>
                    <td>Win Rate (P<sub>win</sub>)</td>
                    <td class="{'positive' if performance['win_rate'] > 50 else 'neutral' if performance['win_rate'] > 40 else 'negative'}">
                        {performance['win_rate']:.1f}%
                    </td>
                </tr>
                <tr>
                    <td>Average Win (μ<sub>W</sub>)</td>
                    <td class="positive">+{performance['avg_win']:.3f}%</td>
                </tr>
                <tr>
                    <td>Average Loss (μ<sub>L</sub>)</td>
                    <td class="negative">{performance['avg_loss']:.3f}%</td>
                </tr>
                <tr>
                    <td>Risk-Reward Ratio (R:R)</td>
                    <td>{abs(performance['avg_win'] / performance['avg_loss']):.2f}:1</td>
                </tr>
            </table>
        </div>
"""

        # Add alerts if needed
        if performance['sharpe_ratio'] < 0:
            html += """
        <div class="alert">
            ⚠ ALERT: Sharpe Ratio negative. Risk-adjusted returns below risk-free rate.
            Recommendation: Review strategy parameters or reduce position sizing.
        </div>
"""

        if performance['max_drawdown'] < -20:
            html += f"""
        <div class="alert">
            ⚠ ALERT: Maximum drawdown exceeds -20% ({performance['max_drawdown']:.1f}%).
            Recommendation: Implement stricter risk controls and position limits.
        </div>
"""

    html += f"""
        <!-- SYSTEM STATUS -->
        <div class="section">
            <div class="section-title">§6. SYSTEM STATUS</div>
            <table class="table">
                <tr>
                    <td>Trading Engine</td>
                    <td class="positive">ACTIVE</td>
                </tr>
                <tr>
                    <td>Risk Management</td>
                    <td class="positive">ENABLED</td>
                </tr>
                <tr>
                    <td>Position Limit</td>
                    <td>5 concurrent</td>
                </tr>
                <tr>
                    <td>Risk per Trade (ρ)</td>
                    <td>1.00%</td>
                </tr>
                <tr>
                    <td>Daily Loss Limit</td>
                    <td class="negative">-5.00%</td>
                </tr>
                <tr>
                    <td>Scan Frequency</td>
                    <td>600s (10 min)</td>
                </tr>
                <tr>
                    <td>Strategies Deployed</td>
                    <td>6 algos</td>
                </tr>
            </table>
        </div>

        <div class="footer">
            PROPRIETARY & CONFIDENTIAL<br>
            PropShop Quantitative Trading System | Model: Multi-Strategy Alpha<br>
            Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} | Next Update: +1h<br>
            © 2025 All Rights Reserved
        </div>
    </div>
</body>
</html>
"""

    return html

# Main execution
print("="*80)
print("GENERATING QUANTITATIVE PERFORMANCE REPORT")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

print("\nCollecting account metrics...")
account = get_account_metrics()
print(f"Balance: ${account['balance']:,.2f} | Equity: ${account['equity']:,.2f}")

print("\nAnalyzing portfolio exposure...")
positions = get_position_analytics()
print(f"Open positions: {positions['count']} | Net exposure: {positions['net_exposure']:+.2f} lots")

print("\nCalculating risk-adjusted metrics...")
performance = analyze_trades_performance()
if performance:
    print(f"Sharpe Ratio: {performance['sharpe_ratio']:.3f}")
    print(f"Win Rate: {performance['win_rate']:.1f}%")
    print(f"Max Drawdown: {performance['max_drawdown']:.2f}%")

print("\nFormatting report...")
html_report = format_quant_report()

print(f"\nSending quantitative report to {EMAIL_TO}...")
subject = f"Quant Report | Sharpe: {performance['sharpe_ratio']:.2f} | P&L: ${account['profit']:+,.2f}" if performance else f"Quant Report | Account: ${account['equity']:,.2f}"

if send_email(subject, html_report):
    print("[SUCCESS] Quantitative report sent!")
else:
    print("[FAILED] Email not sent")

mt5.shutdown()
print("\n[DONE]")
