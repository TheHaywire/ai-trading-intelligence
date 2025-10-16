"""
COMMAND: daily_digest
Complete daily quant report with EVERYTHING a professional quant needs
"""

import sys
sys.path.append('..')

from core.mt5_service import *
from core.email_service import send_email
from core.analysis import *
from core.config import *
from datetime import datetime, timedelta
import json
import numpy as np
import pandas as pd

def calculate_portfolio_metrics():
    """Calculate comprehensive portfolio metrics"""
    account = get_account_info()
    positions = get_positions()

    # Load trade history
    try:
        with open('trades_log.json', 'r') as f:
            trades = json.load(f)
        closed_trades = [t for t in trades if t.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']]
    except:
        closed_trades = []

    # Portfolio metrics
    total_exposure = sum(p.volume * p.price_current for p in positions) if positions else 0
    leverage = total_exposure / account.equity if account.equity > 0 else 0

    # Calculate returns
    if closed_trades:
        returns = np.array([t['current_pnl']/100 for t in closed_trades])

        # Sharpe Ratio (annualized)
        sharpe = np.sqrt(252) * (returns.mean() / returns.std()) if returns.std() != 0 else 0

        # Sortino Ratio (downside deviation only)
        downside = returns[returns < 0]
        sortino = np.sqrt(252) * (returns.mean() / downside.std()) if len(downside) > 0 and downside.std() != 0 else 0

        # Max Drawdown
        equity_curve = [10000]
        for ret in returns:
            equity_curve.append(equity_curve[-1] * (1 + ret))
        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - cummax) / cummax
        max_dd = drawdown.min() * 100

        # Win Rate
        wins = len([t for t in closed_trades if t['current_status'] == 'CLOSED_WIN'])
        win_rate = wins / len(closed_trades) * 100

        # Profit Factor
        gross_profit = sum(t['current_pnl'] for t in closed_trades if t['current_pnl'] > 0)
        gross_loss = abs(sum(t['current_pnl'] for t in closed_trades if t['current_pnl'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

        # Expectancy
        avg_win = np.mean([t['current_pnl'] for t in closed_trades if t['current_pnl'] > 0]) if wins > 0 else 0
        avg_loss = np.mean([t['current_pnl'] for t in closed_trades if t['current_pnl'] < 0]) if len(closed_trades) - wins > 0 else 0
        expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)

        # Calmar Ratio
        calmar = (returns.mean() * 252) / abs(max_dd) if max_dd != 0 else 0

    else:
        sharpe = sortino = max_dd = win_rate = profit_factor = expectancy = calmar = 0

    return {
        'sharpe': sharpe,
        'sortino': sortino,
        'max_dd': max_dd,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'expectancy': expectancy,
        'calmar': calmar,
        'leverage': leverage,
        'closed_trades': len(closed_trades),
        'total_pnl': sum(t['current_pnl'] for t in closed_trades) if closed_trades else 0
    }

def get_position_breakdown():
    """Analyze position breakdown by category"""
    positions = get_positions()
    if not positions:
        return {}

    breakdown = {
        'metals': [],
        'forex': [],
        'crypto': [],
        'indices': [],
        'commodities': []
    }

    for p in positions:
        category = None
        if p.symbol in ['GOLD', 'SILVER', 'XPDUSD', 'XPTUSD']:
            category = 'metals'
        elif 'USD' in p.symbol or p.symbol in ['EURGBP', 'EURJPY', 'GBPJPY']:
            category = 'forex'
        elif p.symbol in ['BTCUSD', 'ETHUSD', 'XRPUSD']:
            category = 'crypto'
        elif 'Cash' in p.symbol:
            category = 'indices'
        elif p.symbol in ['USOUSD', 'UKOUSD']:
            category = 'commodities'

        if category:
            breakdown[category].append({
                'symbol': p.symbol,
                'type': 'LONG' if p.type == 0 else 'SHORT',
                'profit': p.profit,
                'volume': p.volume
            })

    return breakdown

def get_market_correlations():
    """Calculate correlations between major symbols"""
    symbols = ['GOLD', 'EURUSD', 'BTCUSD', 'US100Cash']

    data = {}
    for symbol in symbols:
        df = get_symbol_data(symbol, count=100)
        if df is not None:
            data[symbol] = df['close'].pct_change().dropna()

    if len(data) >= 2:
        # Create correlation matrix
        df_combined = pd.DataFrame(data)
        corr_matrix = df_combined.corr()
        return corr_matrix
    return None

def run():
    if not init_mt5():
        return

    print("="*80)
    print("GENERATING COMPREHENSIVE DAILY QUANT DIGEST")
    print("="*80)

    # Get all data
    account = get_account_info()
    positions = get_positions()
    metrics = calculate_portfolio_metrics()
    breakdown = get_position_breakdown()

    # Market overview
    print("\n[1/5] Analyzing market conditions...")
    major_symbols = ['GOLD', 'SILVER', 'EURUSD', 'GBPUSD', 'BTCUSD', 'US100Cash']
    market_conditions = []

    for symbol in major_symbols:
        df = get_symbol_data(symbol, count=300)
        if df is not None:
            df = calculate_indicators(df)
            trend, score = detect_trend(df)
            latest = df.iloc[-1]

            market_conditions.append({
                'symbol': symbol,
                'price': latest['close'],
                'trend': trend,
                'trend_score': score,
                'rsi': latest['RSI'],
                'volatility': latest['Volatility'],
                'atr': latest['ATR']
            })

    # Generate HTML
    print("[2/5] Calculating correlations...")
    corr_matrix = get_market_correlations()

    print("[3/5] Analyzing positions...")

    print("[4/5] Compiling metrics...")

    print("[5/5] Generating email report...")

    # Build comprehensive HTML email
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Inter', -apple-system, sans-serif;
                background: #f5f7fa;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 32px;
                font-weight: 700;
            }}
            .header .date {{
                font-size: 16px;
                opacity: 0.9;
            }}
            .dashboard {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                padding: 40px;
                background: #f8f9fa;
            }}
            .metric-card {{
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                text-align: center;
            }}
            .metric-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
                font-weight: 600;
            }}
            .metric-value {{
                font-size: 28px;
                font-weight: 700;
                color: #333;
            }}
            .metric-value.positive {{ color: #10b981; }}
            .metric-value.negative {{ color: #ef4444; }}
            .metric-value.neutral {{ color: #667eea; }}
            .content {{
                padding: 40px;
            }}
            .section {{
                margin-bottom: 50px;
            }}
            .section h2 {{
                color: #1e293b;
                font-size: 24px;
                margin: 0 0 20px 0;
                padding-bottom: 12px;
                border-bottom: 3px solid #667eea;
            }}
            .grid-2 {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            table th {{
                background: #f8f9fa;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                font-size: 13px;
                color: #64748b;
                border-bottom: 2px solid #e2e8f0;
            }}
            table td {{
                padding: 12px;
                border-bottom: 1px solid #f1f5f9;
                font-size: 14px;
            }}
            table tr:hover {{
                background: #fafbfc;
            }}
            .position-card {{
                background: #f8f9fa;
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 12px;
                border-left: 4px solid #cbd5e1;
            }}
            .position-card.profit {{
                border-left-color: #10b981;
                background: #ecfdf5;
            }}
            .position-card.loss {{
                border-left-color: #ef4444;
                background: #fef2f2;
            }}
            .corr-matrix {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 2px;
                margin: 20px 0;
            }}
            .corr-cell {{
                padding: 12px;
                text-align: center;
                font-size: 12px;
                font-weight: 600;
                border-radius: 4px;
            }}
            .alert-box {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .alert-box.critical {{
                background: #fee2e2;
                border-left-color: #dc2626;
            }}
            .alert-box.success {{
                background: #d1fae5;
                border-left-color: #10b981;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .badge.long {{ background: #d1fae5; color: #065f46; }}
            .badge.short {{ background: #fee2e2; color: #991b1b; }}
            .badge.uptrend {{ background: #dbeafe; color: #1e40af; }}
            .badge.downtrend {{ background: #fee2e2; color: #991b1b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>DAILY QUANT DIGEST</h1>
                <div class="date">{datetime.now().strftime('%A, %B %d, %Y')}</div>
            </div>

            <!-- KPI Dashboard -->
            <div class="dashboard">
                <div class="metric-card">
                    <div class="metric-label">Portfolio Value</div>
                    <div class="metric-value neutral">${account.equity:,.0f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Daily P&L</div>
                    <div class="metric-value {'positive' if account.profit > 0 else 'negative'}">${account.profit:+,.0f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value {'positive' if metrics['sharpe'] > 1 else 'negative'}">{metrics['sharpe']:.2f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value negative">{metrics['max_dd']:.2f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value {'positive' if metrics['win_rate'] > 50 else 'negative'}">{metrics['win_rate']:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Profit Factor</div>
                    <div class="metric-value {'positive' if metrics['profit_factor'] > 1 else 'negative'}">{metrics['profit_factor']:.2f}</div>
                </div>
            </div>

            <div class="content">
"""

    # Risk Alerts
    alerts = []
    if account.profit < account.balance * -0.05:
        alerts.append(('critical', 'Daily Loss Limit Approached', f'Current loss ${account.profit:,.0f} approaching -5% limit'))
    if len(positions) if positions else 0 > MAX_POSITIONS:
        alerts.append(('critical', 'Position Limit Exceeded', f'{len(positions)} positions open (limit: {MAX_POSITIONS})'))
    if metrics['sharpe'] < 0:
        alerts.append(('critical', 'Negative Sharpe Ratio', 'Risk-adjusted returns are negative - strategy review needed'))
    if metrics['win_rate'] < 40 and metrics['closed_trades'] >= 5:
        alerts.append(('critical', 'Low Win Rate', f'Only {metrics["win_rate"]:.1f}% of trades are winners'))

    if alerts:
        html += '<div class="section"><h2>Risk Alerts</h2>'
        for severity, title, msg in alerts:
            html += f'<div class="alert-box {severity}"><strong>{title}:</strong> {msg}</div>'
        html += '</div>'
    else:
        html += '<div class="section"><div class="alert-box success"><strong>All Systems Green:</strong> No critical alerts detected</div></div>'

    # Performance Metrics
    html += f"""
                <div class="section">
                    <h2>Performance Metrics</h2>
                    <div class="grid-2">
                        <table>
                            <tr><th colspan="2">Risk-Adjusted Returns</th></tr>
                            <tr><td>Sharpe Ratio</td><td><strong>{metrics['sharpe']:.3f}</strong></td></tr>
                            <tr><td>Sortino Ratio</td><td><strong>{metrics['sortino']:.3f}</strong></td></tr>
                            <tr><td>Calmar Ratio</td><td><strong>{metrics['calmar']:.3f}</strong></td></tr>
                        </table>
                        <table>
                            <tr><th colspan="2">Trading Statistics</th></tr>
                            <tr><td>Total Trades</td><td><strong>{metrics['closed_trades']}</strong></td></tr>
                            <tr><td>Win Rate</td><td><strong>{metrics['win_rate']:.1f}%</strong></td></tr>
                            <tr><td>Profit Factor</td><td><strong>{metrics['profit_factor']:.2f}</strong></td></tr>
                            <tr><td>Expectancy</td><td><strong>{metrics['expectancy']:.2f}%</strong></td></tr>
                        </table>
                    </div>
                </div>
"""

    # Current Positions
    if positions:
        html += '<div class="section"><h2>Open Positions</h2>'

        for category, pos_list in breakdown.items():
            if pos_list:
                html += f'<h3 style="color: #64748b; font-size: 14px; text-transform: uppercase; margin-top: 20px;">{category.title()}</h3>'
                for p in pos_list:
                    card_class = 'profit' if p['profit'] > 0 else 'loss'
                    html += f"""
                    <div class="position-card {card_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>{p['symbol']}</strong>
                                <span class="badge {'long' if p['type'] == 'LONG' else 'short'}">{p['type']}</span>
                                <span style="margin-left: 10px; color: #64748b;">{p['volume']} lots</span>
                            </div>
                            <div style="font-size: 18px; font-weight: 700; color: {'#10b981' if p['profit'] > 0 else '#ef4444'};">
                                ${p['profit']:+,.0f}
                            </div>
                        </div>
                    </div>
                    """
        html += '</div>'

    # Market Conditions
    html += '<div class="section"><h2>Market Conditions</h2><table>'
    html += '<tr><th>Symbol</th><th>Price</th><th>Trend</th><th>RSI</th><th>Volatility</th></tr>'

    for mkt in market_conditions:
        trend_class = 'uptrend' if mkt['trend_score'] > 0 else 'downtrend' if mkt['trend_score'] < 0 else ''
        html += f"""
        <tr>
            <td><strong>{mkt['symbol']}</strong></td>
            <td>{mkt['price']:.5f}</td>
            <td><span class="badge {trend_class}">{mkt['trend']}</span></td>
            <td>{mkt['rsi']:.1f}</td>
            <td>{mkt['volatility']:.1f}%</td>
        </tr>
        """
    html += '</table></div>'

    # Correlation Matrix
    if corr_matrix is not None:
        html += '<div class="section"><h2>Asset Correlations</h2>'
        html += '<p style="color: #64748b; font-size: 14px;">Understanding how assets move together helps manage portfolio risk</p>'
        html += '<table>'
        html += '<tr><th></th>'
        for col in corr_matrix.columns:
            html += f'<th>{col}</th>'
        html += '</tr>'

        for idx in corr_matrix.index:
            html += f'<tr><td><strong>{idx}</strong></td>'
            for col in corr_matrix.columns:
                val = corr_matrix.loc[idx, col]
                color = f'rgb({int(255*(1-val))}, {int(255*val)}, 100)' if val >= 0 else f'rgb(255, {int(255*(1+val))}, {int(255*(1+val))})'
                html += f'<td style="background: {color}; text-align: center; font-weight: 600;">{val:.2f}</td>'
            html += '</tr>'
        html += '</table></div>'

    # Footer
    html += f"""
                <div class="section">
                    <h2>System Status</h2>
                    <table>
                        <tr><td>Leverage</td><td><strong>{metrics['leverage']:.2f}x</strong></td></tr>
                        <tr><td>Open Positions</td><td><strong>{len(positions) if positions else 0} / {MAX_POSITIONS}</strong></td></tr>
                        <tr><td>Risk Per Trade</td><td><strong>{RISK_PER_TRADE*100}%</strong></td></tr>
                        <tr><td>ATR Stop Multiplier</td><td><strong>{ATR_STOP_MULTIPLIER}x</strong></td></tr>
                    </table>
                </div>

                <div style="text-align: center; padding: 30px; color: #94a3b8; font-size: 13px;">
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>PropShop Trading System | Institutional Grade Analytics</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    print("\nSending comprehensive digest to email...")
    if send_email("DAILY QUANT DIGEST", html):
        print("[SUCCESS] Complete digest sent!")
    else:
        print("[FAILED] Email not sent")

    shutdown_mt5()
    print("\n[DONE]")

if __name__ == "__main__":
    run()
