"""
COMMAND: risk
Complete Risk Management Dashboard - VaR, Stress Tests, Heat Maps, Portfolio Analytics
"""

import sys
sys.path.append('..')

from core.mt5_service import *
from core.email_service import send_email
from core.analysis import *
from core.config import *
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import json

def calculate_var(returns, confidence=0.95):
    """Calculate Value at Risk"""
    if len(returns) < 2:
        return 0
    return np.percentile(returns, (1 - confidence) * 100)

def calculate_cvar(returns, confidence=0.95):
    """Calculate Conditional VaR (Expected Shortfall)"""
    if len(returns) < 2:
        return 0
    var = calculate_var(returns, confidence)
    return returns[returns <= var].mean()

def stress_test_portfolio(positions, account_balance, scenarios):
    """Run stress tests on portfolio"""
    results = []

    for scenario_name, price_changes in scenarios.items():
        total_impact = 0
        position_impacts = []

        for pos in positions:
            if pos.symbol in price_changes:
                price_change_pct = price_changes[pos.symbol]
                current_value = pos.volume * pos.price_current

                if pos.type == mt5.ORDER_TYPE_BUY:  # LONG
                    impact = current_value * price_change_pct
                else:  # SHORT
                    impact = current_value * (-price_change_pct)

                total_impact += impact
                position_impacts.append({
                    'symbol': pos.symbol,
                    'type': 'LONG' if pos.type == 0 else 'SHORT',
                    'impact': impact
                })

        impact_pct = (total_impact / account_balance) * 100

        results.append({
            'scenario': scenario_name,
            'total_impact': total_impact,
            'impact_pct': impact_pct,
            'position_impacts': position_impacts
        })

    return results

def calculate_portfolio_greeks(positions):
    """Calculate portfolio Greeks (simplified)"""
    total_delta = 0
    total_exposure = 0

    for pos in positions:
        position_value = pos.volume * pos.price_current

        # Delta: direction exposure
        if pos.type == mt5.ORDER_TYPE_BUY:
            delta = position_value
        else:
            delta = -position_value

        total_delta += delta
        total_exposure += abs(position_value)

    return {
        'net_delta': total_delta,
        'total_exposure': total_exposure,
        'delta_pct': (total_delta / total_exposure * 100) if total_exposure > 0 else 0
    }

def analyze_concentration_risk(positions):
    """Analyze portfolio concentration"""
    if not positions:
        return {}

    # By symbol
    symbol_exposure = {}
    total_value = sum(abs(p.volume * p.price_current) for p in positions)

    for pos in positions:
        value = abs(pos.volume * pos.price_current)
        if pos.symbol not in symbol_exposure:
            symbol_exposure[pos.symbol] = 0
        symbol_exposure[pos.symbol] += value

    # By category
    category_exposure = {
        'Metals': 0,
        'Forex': 0,
        'Crypto': 0,
        'Indices': 0,
        'Commodities': 0
    }

    for pos in positions:
        value = abs(pos.volume * pos.price_current)
        if pos.symbol in ['GOLD', 'SILVER', 'XPDUSD', 'XPTUSD']:
            category_exposure['Metals'] += value
        elif 'USD' in pos.symbol or pos.symbol in ['EURGBP', 'EURJPY', 'GBPJPY']:
            category_exposure['Forex'] += value
        elif pos.symbol in ['BTCUSD', 'ETHUSD', 'XRPUSD']:
            category_exposure['Crypto'] += value
        elif 'Cash' in pos.symbol:
            category_exposure['Indices'] += value
        elif pos.symbol in ['USOUSD', 'UKOUSD']:
            category_exposure['Commodities'] += value

    # Calculate percentages
    symbol_pct = {k: (v/total_value*100) for k, v in symbol_exposure.items()}
    category_pct = {k: (v/total_value*100) for k, v in category_exposure.items() if v > 0}

    return {
        'symbol_exposure': symbol_pct,
        'category_exposure': category_pct,
        'largest_position': max(symbol_pct.items(), key=lambda x: x[1]) if symbol_pct else ('None', 0),
        'herfindahl_index': sum(p**2 for p in symbol_pct.values()) / 100  # Concentration measure
    }

def calculate_optimal_position_size(account_balance, risk_pct, win_rate, avg_win, avg_loss):
    """Kelly Criterion for optimal position sizing"""
    if avg_loss == 0 or win_rate == 0:
        return 0

    # Kelly formula: f = (p*b - q) / b
    # where p = win rate, q = 1-p, b = avg_win/avg_loss
    p = win_rate / 100
    q = 1 - p
    b = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    kelly = (p * b - q) / b if b != 0 else 0

    # Use fractional Kelly (safer)
    fractional_kelly = kelly * 0.25  # 25% of full Kelly

    # Ensure within reasonable bounds
    fractional_kelly = max(0, min(fractional_kelly, 0.1))  # Max 10% per position

    return fractional_kelly

def run():
    if not init_mt5():
        return

    print("="*80)
    print("RISK MANAGEMENT DASHBOARD")
    print("="*80)

    account = get_account_info()
    positions = get_positions()

    # Load trade history
    try:
        with open('trades_log.json', 'r') as f:
            trades = json.load(f)
        closed_trades = [t for t in trades if t.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']]
    except:
        closed_trades = []

    print(f"\n[1/6] Calculating Value at Risk...")

    # VaR Calculation
    if closed_trades:
        returns = np.array([t['current_pnl']/100 for t in closed_trades])

        var_95 = calculate_var(returns, 0.95)
        var_99 = calculate_var(returns, 0.99)
        cvar_95 = calculate_cvar(returns, 0.95)

        var_95_dollar = account.balance * var_95
        var_99_dollar = account.balance * var_99
        cvar_95_dollar = account.balance * cvar_95
    else:
        var_95 = var_99 = cvar_95 = 0
        var_95_dollar = var_99_dollar = cvar_95_dollar = 0

    print(f"[2/6] Running stress tests...")

    # Stress Test Scenarios
    scenarios = {
        'Gold Crash -10%': {'GOLD': -0.10, 'SILVER': -0.08, 'XPDUSD': -0.07},
        'Gold Rally +10%': {'GOLD': 0.10, 'SILVER': 0.08, 'XPDUSD': 0.07},
        'Market Crash -20%': {
            'US100Cash': -0.20, 'US500Cash': -0.20, 'BTCUSD': -0.30,
            'GOLD': 0.05, 'EURUSD': 0.02
        },
        'Dollar Spike +5%': {
            'EURUSD': -0.05, 'GBPUSD': -0.05, 'AUDUSD': -0.05,
            'GOLD': -0.03, 'BTCUSD': -0.04
        },
        'Risk-On Rally': {
            'US100Cash': 0.10, 'BTCUSD': 0.15, 'ETHUSD': 0.20,
            'GOLD': -0.02, 'EURUSD': 0.03
        }
    }

    stress_results = stress_test_portfolio(positions if positions else [], account.balance, scenarios) if positions else []

    print(f"[3/6] Calculating portfolio Greeks...")
    greeks = calculate_portfolio_greeks(positions) if positions else {'net_delta': 0, 'total_exposure': 0, 'delta_pct': 0}

    print(f"[4/6] Analyzing concentration risk...")
    concentration = analyze_concentration_risk(positions) if positions else {}

    print(f"[5/6] Calculating optimal position sizing...")

    # Calculate optimal sizing
    if closed_trades:
        wins = [t for t in closed_trades if t['current_status'] == 'CLOSED_WIN']
        losses = [t for t in closed_trades if t['current_status'] == 'CLOSED_LOSS']

        win_rate = (len(wins) / len(closed_trades)) * 100
        avg_win = np.mean([t['current_pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['current_pnl'] for t in losses]) if losses else 0

        kelly_size = calculate_optimal_position_size(account.balance, RISK_PER_TRADE, win_rate, avg_win, avg_loss)
        kelly_size_pct = kelly_size * 100
    else:
        win_rate = avg_win = avg_loss = kelly_size_pct = 0

    print(f"[6/6] Generating risk report...")

    # Generate HTML Report
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Inter', -apple-system, sans-serif;
                background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 36px;
                font-weight: 700;
            }}
            .alert-banner {{
                background: #fef3c7;
                border-left: 5px solid #f59e0b;
                padding: 20px;
                margin: 0;
                text-align: center;
                font-weight: 600;
                color: #92400e;
            }}
            .alert-banner.critical {{
                background: #fee2e2;
                border-left-color: #dc2626;
                color: #991b1b;
            }}
            .content {{
                padding: 40px;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .metric-card {{
                background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
                padding: 25px;
                border-radius: 12px;
                border-left: 5px solid #6366f1;
            }}
            .metric-card.danger {{
                border-left-color: #dc2626;
            }}
            .metric-label {{
                font-size: 13px;
                color: #6b7280;
                text-transform: uppercase;
                font-weight: 600;
                margin-bottom: 10px;
            }}
            .metric-value {{
                font-size: 32px;
                font-weight: 700;
                color: #1f2937;
            }}
            .metric-value.danger {{ color: #dc2626; }}
            .metric-value.success {{ color: #10b981; }}
            .section {{
                margin: 40px 0;
            }}
            .section h2 {{
                color: #1f2937;
                font-size: 24px;
                margin: 0 0 20px 0;
                padding-bottom: 12px;
                border-bottom: 3px solid #dc2626;
            }}
            .stress-result {{
                background: #f9fafb;
                padding: 20px;
                border-radius: 12px;
                margin: 15px 0;
                border-left: 5px solid #6b7280;
            }}
            .stress-result.severe {{
                border-left-color: #dc2626;
                background: #fef2f2;
            }}
            .stress-result.positive {{
                border-left-color: #10b981;
                background: #f0fdf4;
            }}
            .heat-map {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .heat-cell {{
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                color: white;
                font-weight: 600;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            table th {{
                background: #f1f5f9;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                color: #475569;
                border-bottom: 2px solid #e2e8f0;
            }}
            table td {{
                padding: 15px;
                border-bottom: 1px solid #f1f5f9;
            }}
            .recommendation-box {{
                background: #dbeafe;
                border-left: 5px solid #2563eb;
                padding: 25px;
                border-radius: 8px;
                margin: 25px 0;
            }}
            .recommendation-box h3 {{
                margin: 0 0 15px 0;
                color: #1e40af;
            }}
            .recommendation-box ul {{
                margin: 0;
                padding-left: 20px;
            }}
            .recommendation-box li {{
                margin: 10px 0;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>RISK MANAGEMENT DASHBOARD</h1>
                <div style="font-size: 16px; opacity: 0.95; margin-top: 10px;">
                    {datetime.now().strftime('%A, %B %d, %Y')}
                </div>
            </div>
"""

    # Alert Banner
    current_drawdown = ((account.equity - account.balance) / account.balance) * 100
    if abs(current_drawdown) > 5:
        html += f"""
            <div class="alert-banner critical">
                CRITICAL: Current Drawdown {current_drawdown:.2f}% exceeds -5% risk limit!
            </div>
"""
    elif abs(current_drawdown) > 3:
        html += f"""
            <div class="alert-banner">
                WARNING: Current Drawdown {current_drawdown:.2f}% approaching risk limit
            </div>
"""

    html += """
            <div class="content">
                <div class="section">
                    <h2>Value at Risk (VaR)</h2>
                    <div class="metrics-grid">
"""

    # VaR Metrics
    html += f"""
                        <div class="metric-card danger">
                            <div class="metric-label">VaR 95%</div>
                            <div class="metric-value danger">${var_95_dollar:,.0f}</div>
                            <div style="font-size: 14px; color: #6b7280; margin-top: 8px;">
                                {var_95*100:.2f}% of portfolio
                            </div>
                        </div>
                        <div class="metric-card danger">
                            <div class="metric-label">VaR 99%</div>
                            <div class="metric-value danger">${var_99_dollar:,.0f}</div>
                            <div style="font-size: 14px; color: #6b7280; margin-top: 8px;">
                                {var_99*100:.2f}% of portfolio
                            </div>
                        </div>
                        <div class="metric-card danger">
                            <div class="metric-label">CVaR 95%</div>
                            <div class="metric-value danger">${cvar_95_dollar:,.0f}</div>
                            <div style="font-size: 14px; color: #6b7280; margin-top: 8px;">
                                Expected loss if VaR breached
                            </div>
                        </div>
"""

    html += """
                    </div>
                    <p style="color: #6b7280; font-size: 14px;">
                        VaR 95%: There's a 5% chance you could lose this much or more in a single day.
                        CVaR: Average loss if that 5% scenario happens.
                    </p>
                </div>
"""

    # Portfolio Greeks
    html += f"""
                <div class="section">
                    <h2>Portfolio Greeks</h2>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">Net Delta</div>
                            <div class="metric-value">${greeks['net_delta']:,.0f}</div>
                            <div style="font-size: 14px; color: #6b7280; margin-top: 8px;">
                                Directional exposure
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Total Exposure</div>
                            <div class="metric-value">${greeks['total_exposure']:,.0f}</div>
                            <div style="font-size: 14px; color: #6b7280; margin-top: 8px;">
                                Absolute position value
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Delta %</div>
                            <div class="metric-value {'success' if abs(greeks['delta_pct']) < 20 else 'danger'}">{greeks['delta_pct']:+.1f}%</div>
                            <div style="font-size: 14px; color: #6b7280; margin-top: 8px;">
                                Net directional bias
                            </div>
                        </div>
                    </div>
                </div>
"""

    # Stress Tests
    html += """
                <div class="section">
                    <h2>Stress Test Results</h2>
                    <p style="color: #6b7280; margin-bottom: 20px;">What happens to your portfolio in extreme scenarios:</p>
"""

    for result in stress_results:
        severity_class = 'severe' if result['impact_pct'] < -5 else 'positive' if result['impact_pct'] > 5 else ''
        html += f"""
                    <div class="stress-result {severity_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <strong style="font-size: 18px;">{result['scenario']}</strong>
                            <div>
                                <span style="font-size: 24px; font-weight: 700; color: {'#dc2626' if result['impact_pct'] < 0 else '#10b981'};">
                                    ${result['total_impact']:+,.0f}
                                </span>
                                <span style="font-size: 16px; color: #6b7280; margin-left: 10px;">
                                    ({result['impact_pct']:+.2f}%)
                                </span>
                            </div>
                        </div>
"""
        if result['position_impacts']:
            html += '<div style="font-size: 13px; color: #6b7280;"><strong>Top Impacted Positions:</strong><br>'
            for pos in sorted(result['position_impacts'], key=lambda x: abs(x['impact']), reverse=True)[:3]:
                html += f"{pos['symbol']} {pos['type']}: ${pos['impact']:+,.0f}<br>"
            html += '</div>'

        html += '</div>'

    # Concentration Risk
    if concentration:
        html += """
                <div class="section">
                    <h2>Concentration Risk</h2>
"""

        # By Symbol
        html += '<h3 style="font-size: 16px; color: #6b7280; margin: 20px 0 15px 0;">Exposure by Symbol:</h3>'
        html += '<div class="heat-map">'

        for symbol, pct in sorted(concentration['symbol_exposure'].items(), key=lambda x: x[1], reverse=True):
            # Color based on concentration
            if pct > 30:
                bg_color = '#dc2626'
            elif pct > 20:
                bg_color = '#f59e0b'
            elif pct > 10:
                bg_color = '#3b82f6'
            else:
                bg_color = '#10b981'

            html += f"""
                <div class="heat-cell" style="background: {bg_color};">
                    <div style="font-size: 16px; font-weight: 700;">{symbol}</div>
                    <div style="font-size: 24px; margin-top: 5px;">{pct:.1f}%</div>
                </div>
"""
        html += '</div>'

        # By Category
        if concentration['category_exposure']:
            html += '<h3 style="font-size: 16px; color: #6b7280; margin: 30px 0 15px 0;">Exposure by Asset Class:</h3>'
            html += '<table><tr><th>Category</th><th>Exposure %</th></tr>'

            for category, pct in sorted(concentration['category_exposure'].items(), key=lambda x: x[1], reverse=True):
                html += f'<tr><td><strong>{category}</strong></td><td style="font-size: 18px; font-weight: 600;">{pct:.1f}%</td></tr>'

            html += '</table>'

        # Concentration Warning
        largest_sym, largest_pct = concentration['largest_position']
        if largest_pct > 30:
            html += f"""
                <div style="background: #fee2e2; border-left: 5px solid #dc2626; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    <strong style="color: #991b1b;">HIGH CONCENTRATION RISK:</strong>
                    <span style="color: #6b7280;"> {largest_sym} represents {largest_pct:.1f}% of your portfolio (limit: 30%)</span>
                </div>
"""

    html += '</div>'

    # Optimal Position Sizing
    html += f"""
                <div class="section">
                    <h2>Optimal Position Sizing (Kelly Criterion)</h2>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">Current Risk per Trade</div>
                            <div class="metric-value">{RISK_PER_TRADE*100:.1f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Kelly Optimal Size</div>
                            <div class="metric-value {'success' if kelly_size_pct < RISK_PER_TRADE*100 else 'danger'}">{kelly_size_pct:.2f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value">{win_rate:.1f}%</div>
                        </div>
                    </div>
"""

    if kelly_size_pct < RISK_PER_TRADE * 100:
        html += f"""
                    <div style="background: #fef3c7; border-left: 5px solid #f59e0b; padding: 20px; border-radius: 8px; margin-top: 20px;">
                        <strong>RECOMMENDATION:</strong> Your current position size ({RISK_PER_TRADE*100}%) exceeds Kelly optimal ({kelly_size_pct:.2f}%).
                        Consider reducing to improve risk-adjusted returns.
                    </div>
"""

    html += '</div>'

    # Recommendations
    html += """
                <div class="recommendation-box">
                    <h3>Risk Management Recommendations</h3>
                    <ul>
"""

    recommendations = []

    if abs(current_drawdown) > 5:
        recommendations.append("URGENT: Close losing positions immediately - drawdown exceeds limit")

    if concentration and concentration['largest_position'][1] > 30:
        recommendations.append(f"Reduce {concentration['largest_position'][0]} exposure to below 30%")

    if kelly_size_pct < RISK_PER_TRADE * 100:
        recommendations.append(f"Reduce position sizing from {RISK_PER_TRADE*100}% to {kelly_size_pct:.2f}% per trade")

    if greeks['delta_pct'] > 50 or greeks['delta_pct'] < -50:
        recommendations.append(f"Portfolio heavily directional ({greeks['delta_pct']:+.1f}%) - consider hedging")

    if any(r['impact_pct'] < -10 for r in stress_results):
        recommendations.append("High vulnerability to stress scenarios - diversify or reduce exposure")

    if not recommendations:
        recommendations.append("Risk levels within acceptable parameters - continue monitoring")

    for rec in recommendations:
        html += f'<li>{rec}</li>'

    html += """
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    print("\nSending risk dashboard to email...")
    if send_email("RISK MANAGEMENT DASHBOARD", html):
        print("[SUCCESS] Risk dashboard sent!")
    else:
        print("[FAILED] Email not sent")

    shutdown_mt5()
    print("\n[DONE]")

if __name__ == "__main__":
    run()
