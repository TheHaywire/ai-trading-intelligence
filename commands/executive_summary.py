"""
MASTER EXECUTIVE SUMMARY
One powerful daily briefing combining insights from all reports
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import *
from core.mt5_service import init_mt5, get_positions, get_account_info, get_symbol_data
from core.analysis import calculate_indicators, detect_trend
from core.email_service import send_email
import MetaTrader5 as mt5


def get_executive_kpis(account, positions):
    """Calculate executive-level KPIs"""

    # Account metrics
    balance = account.balance
    equity = account.equity
    profit = account.profit
    drawdown_pct = (profit / balance) * 100

    # Position metrics
    num_positions = len(positions) if positions else 0

    winners = [p for p in positions if p.profit > 0] if positions else []
    losers = [p for p in positions if p.profit <= 0] if positions else []

    total_winners_pnl = sum(p.profit for p in winners)
    total_losers_pnl = sum(p.profit for p in losers)

    win_rate = (len(winners) / num_positions * 100) if num_positions > 0 else 0

    # Average winner/loser
    avg_winner = total_winners_pnl / len(winners) if winners else 0
    avg_loser = total_losers_pnl / len(losers) if losers else 0

    # Profit factor
    profit_factor = abs(total_winners_pnl / total_losers_pnl) if total_losers_pnl != 0 else 0

    # Largest positions
    largest_winner = max(winners, key=lambda p: p.profit) if winners else None
    largest_loser = min(losers, key=lambda p: p.profit) if losers else None

    # Risk metrics
    position_limit_utilization = (num_positions / MAX_POSITIONS) * 100

    # Calculate exposure by category
    exposure_by_category = {}
    if positions:
        for pos in positions:
            category = 'METALS' if pos.symbol in METALS else \
                      'FOREX' if pos.symbol in FOREX_MAJORS + FOREX_CROSSES else \
                      'CRYPTO' if pos.symbol in CRYPTO else \
                      'INDICES' if pos.symbol in INDICES else 'OTHER'

            if category not in exposure_by_category:
                exposure_by_category[category] = 0
            exposure_by_category[category] += abs(pos.profit)

    return {
        'balance': balance,
        'equity': equity,
        'profit': profit,
        'drawdown_pct': drawdown_pct,
        'num_positions': num_positions,
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': win_rate,
        'total_winners_pnl': total_winners_pnl,
        'total_losers_pnl': total_losers_pnl,
        'avg_winner': avg_winner,
        'avg_loser': avg_loser,
        'profit_factor': profit_factor,
        'largest_winner': largest_winner,
        'largest_loser': largest_loser,
        'position_limit_utilization': position_limit_utilization,
        'exposure_by_category': exposure_by_category
    }


def identify_critical_actions(kpis, positions):
    """Identify top priority actions"""
    actions = []

    # Critical drawdown
    if kpis['drawdown_pct'] < -10:
        actions.append({
            'priority': 'CRITICAL',
            'category': 'RISK',
            'action': 'REDUCE DRAWDOWN',
            'description': f"Account at {kpis['drawdown_pct']:.1f}% drawdown. Close worst losers immediately.",
            'impact': 'HIGH'
        })
    elif kpis['drawdown_pct'] < -5:
        actions.append({
            'priority': 'HIGH',
            'category': 'RISK',
            'action': 'MONITOR DRAWDOWN',
            'description': f"Account at {kpis['drawdown_pct']:.1f}% drawdown. Review risk exposure.",
            'impact': 'MEDIUM'
        })

    # Position limit
    if kpis['num_positions'] > MAX_POSITIONS:
        actions.append({
            'priority': 'CRITICAL',
            'category': 'RISK',
            'action': 'REDUCE POSITIONS',
            'description': f"{kpis['num_positions']} positions open (max {MAX_POSITIONS}). Close {kpis['num_positions'] - MAX_POSITIONS} positions.",
            'impact': 'HIGH'
        })

    # Low win rate
    if kpis['win_rate'] < 40:
        actions.append({
            'priority': 'HIGH',
            'category': 'STRATEGY',
            'action': 'IMPROVE WIN RATE',
            'description': f"Win rate at {kpis['win_rate']:.1f}%. Review entry criteria and stop losses.",
            'impact': 'MEDIUM'
        })

    # Poor profit factor
    if kpis['profit_factor'] < 1.0:
        actions.append({
            'priority': 'HIGH',
            'category': 'STRATEGY',
            'action': 'IMPROVE PROFIT FACTOR',
            'description': f"Profit factor at {kpis['profit_factor']:.2f}. Losers outpacing winners.",
            'impact': 'HIGH'
        })

    # Large unrealized losses
    if kpis['largest_loser'] and kpis['largest_loser'].profit < -10000:
        actions.append({
            'priority': 'HIGH',
            'category': 'POSITION',
            'action': 'CLOSE LARGE LOSER',
            'description': f"{kpis['largest_loser'].symbol} losing ${abs(kpis['largest_loser'].profit):,.0f}. Consider closing.",
            'impact': 'HIGH'
        })

    # Large unrealized winners
    if kpis['largest_winner'] and kpis['largest_winner'].profit > 10000:
        actions.append({
            'priority': 'MEDIUM',
            'category': 'POSITION',
            'action': 'TAKE PROFIT',
            'description': f"{kpis['largest_winner'].symbol} up ${kpis['largest_winner'].profit:,.0f}. Consider taking partial profit.",
            'impact': 'MEDIUM'
        })

    # Analyze counter-trend positions
    if positions:
        counter_trend_losers = []
        for pos in positions:
            if pos.profit < -1000:
                df = get_symbol_data(pos.symbol, count=200)
                if df is not None:
                    df = calculate_indicators(df)
                    trend, trend_score = detect_trend(df)

                    position_type = 'LONG' if pos.type == 0 else 'SHORT'

                    # Check if counter-trend
                    if (position_type == 'LONG' and trend_score < -5) or \
                       (position_type == 'SHORT' and trend_score > 5):
                        counter_trend_losers.append({
                            'symbol': pos.symbol,
                            'type': position_type,
                            'profit': pos.profit,
                            'trend': trend
                        })

        if len(counter_trend_losers) > 0:
            actions.append({
                'priority': 'HIGH',
                'category': 'STRATEGY',
                'action': 'CLOSE COUNTER-TREND POSITIONS',
                'description': f"{len(counter_trend_losers)} losing positions are counter-trend. Close immediately.",
                'impact': 'HIGH',
                'details': counter_trend_losers
            })

    # Sort by priority
    priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    actions.sort(key=lambda x: priority_order[x['priority']])

    return actions


def get_market_opportunities():
    """Scan for top market opportunities"""
    opportunities = []

    # Scan top symbols
    for symbol in ALL_SYMBOLS[:10]:
        df = get_symbol_data(symbol, count=200)
        if df is None:
            continue

        df = calculate_indicators(df)
        trend, trend_score = detect_trend(df)

        latest = df.iloc[-1]
        rsi = latest['RSI']
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']

        # Look for strong setups
        if trend_score > 7 and rsi < 50 and macd > macd_signal:
            opportunities.append({
                'symbol': symbol,
                'direction': 'LONG',
                'reason': f'Strong uptrend with healthy pullback (RSI {rsi:.0f})',
                'confidence': 85,
                'trend': trend
            })
        elif trend_score < -7 and rsi > 50 and macd < macd_signal:
            opportunities.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'reason': f'Strong downtrend with bearish momentum (RSI {rsi:.0f})',
                'confidence': 85,
                'trend': trend
            })

    # Sort by confidence
    opportunities.sort(key=lambda x: x['confidence'], reverse=True)

    return opportunities[:5]


def get_daily_highlights(kpis, positions):
    """Generate daily highlights"""
    highlights = []

    # Performance highlight
    if kpis['profit'] > 0:
        highlights.append({
            'type': 'POSITIVE',
            'icon': '📈',
            'message': f"Portfolio up ${kpis['profit']:,.2f} today ({kpis['drawdown_pct']:+.1f}%)"
        })
    else:
        highlights.append({
            'type': 'NEGATIVE',
            'icon': '📉',
            'message': f"Portfolio down ${abs(kpis['profit']):,.2f} today ({kpis['drawdown_pct']:.1f}%)"
        })

    # Win rate highlight
    if kpis['win_rate'] >= 50:
        highlights.append({
            'type': 'POSITIVE',
            'icon': '🎯',
            'message': f"Win rate at {kpis['win_rate']:.0f}% ({kpis['winners']} winners, {kpis['losers']} losers)"
        })
    else:
        highlights.append({
            'type': 'NEGATIVE',
            'icon': '⚠️',
            'message': f"Win rate low at {kpis['win_rate']:.0f}% ({kpis['winners']} winners, {kpis['losers']} losers)"
        })

    # Profit factor highlight
    if kpis['profit_factor'] > 1.5:
        highlights.append({
            'type': 'POSITIVE',
            'icon': '💰',
            'message': f"Profit factor excellent at {kpis['profit_factor']:.2f}x"
        })
    elif kpis['profit_factor'] > 1.0:
        highlights.append({
            'type': 'NEUTRAL',
            'icon': '📊',
            'message': f"Profit factor at {kpis['profit_factor']:.2f}x"
        })
    else:
        highlights.append({
            'type': 'NEGATIVE',
            'icon': '🚨',
            'message': f"Profit factor poor at {kpis['profit_factor']:.2f}x - losers outpacing winners"
        })

    # Position highlight
    if kpis['num_positions'] > MAX_POSITIONS:
        highlights.append({
            'type': 'NEGATIVE',
            'icon': '⚠️',
            'message': f"{kpis['num_positions']} positions open - {kpis['num_positions'] - MAX_POSITIONS} over limit"
        })
    else:
        highlights.append({
            'type': 'NEUTRAL',
            'icon': '📍',
            'message': f"{kpis['num_positions']}/{MAX_POSITIONS} positions open ({kpis['position_limit_utilization']:.0f}% utilization)"
        })

    return highlights


def generate_executive_html_report(kpis, actions, opportunities, highlights):
    """Generate executive summary HTML report"""

    # KPI Cards
    kpi_cards = f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Portfolio Value</div>
            <div class="kpi-value">${kpis['equity']:,.2f}</div>
            <div class="kpi-change" style="color: {'#10b981' if kpis['profit'] > 0 else '#ef4444'};">
                ${kpis['profit']:+,.2f} ({kpis['drawdown_pct']:+.1f}%)
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Win Rate</div>
            <div class="kpi-value" style="color: {'#10b981' if kpis['win_rate'] >= 50 else '#ef4444'};">
                {kpis['win_rate']:.1f}%
            </div>
            <div class="kpi-change" style="color: #a0aec0;">
                {kpis['winners']}W / {kpis['losers']}L
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Profit Factor</div>
            <div class="kpi-value" style="color: {'#10b981' if kpis['profit_factor'] > 1 else '#ef4444'};">
                {kpis['profit_factor']:.2f}x
            </div>
            <div class="kpi-change" style="color: #a0aec0;">
                {'Winners ahead' if kpis['profit_factor'] > 1 else 'Losers ahead'}
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Open Positions</div>
            <div class="kpi-value" style="color: {'#ef4444' if kpis['num_positions'] > MAX_POSITIONS else '#10b981'};">
                {kpis['num_positions']}
            </div>
            <div class="kpi-change" style="color: #a0aec0;">
                {kpis['position_limit_utilization']:.0f}% capacity
            </div>
        </div>
    </div>
    """

    # Daily Highlights
    highlights_html = ""
    for h in highlights:
        color = '#10b981' if h['type'] == 'POSITIVE' else '#ef4444' if h['type'] == 'NEGATIVE' else '#3b82f6'
        highlights_html += f"""
        <div style="padding: 12px; margin-bottom: 8px; background: rgba(45, 55, 72, 0.5); border-left: 4px solid {color}; border-radius: 4px;">
            <span style="font-size: 18px; margin-right: 8px;">{h['icon']}</span>
            <span style="color: #e2e8f0;">{h['message']}</span>
        </div>
        """

    # Critical Actions
    actions_html = ""
    for action in actions[:5]:  # Top 5
        priority_colors = {
            'CRITICAL': '#ef4444',
            'HIGH': '#f59e0b',
            'MEDIUM': '#3b82f6',
            'LOW': '#a0aec0'
        }
        color = priority_colors[action['priority']]

        actions_html += f"""
        <tr style="background: rgba(45, 55, 72, 0.3);">
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <span style="background: {color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">
                    {action['priority']}
                </span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <span style="color: #a0aec0; font-size: 11px;">{action['category']}</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <strong style="color: #e2e8f0;">{action['action']}</strong><br>
                <span style="color: #a0aec0; font-size: 12px;">{action['description']}</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <span style="color: {color};">{action['impact']}</span>
            </td>
        </tr>
        """

    # Market Opportunities
    opportunities_html = ""
    for opp in opportunities:
        color = '#10b981' if opp['direction'] == 'LONG' else '#ef4444'
        opportunities_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <strong>{opp['symbol']}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {color}; font-weight: bold;">
                {opp['direction']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; font-size: 12px;">
                {opp['reason']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #fbbf24;">
                {opp['confidence']}%
            </td>
        </tr>
        """

    if not opportunities_html:
        opportunities_html = '<tr><td colspan="4" style="padding: 20px; text-align: center; color: #a0aec0;">No high-confidence opportunities at this time</td></tr>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: #1a202c;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.4);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
                padding: 50px 40px;
                text-align: center;
                color: white;
                position: relative;
                overflow: hidden;
            }}
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="rgba(255,255,255,0.05)" d="M0,96L48,112C96,128,192,160,288,160C384,160,480,128,576,122.7C672,117,768,139,864,144C960,149,1056,139,1152,122.7C1248,107,1344,85,1392,74.7L1440,64L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>') no-repeat bottom;
                background-size: cover;
            }}
            .header h1 {{
                margin: 0;
                font-size: 42px;
                font-weight: bold;
                position: relative;
                z-index: 1;
            }}
            .header .subtitle {{
                color: rgba(255,255,255,0.8);
                margin-top: 10px;
                font-size: 16px;
                position: relative;
                z-index: 1;
            }}
            .timestamp {{
                color: rgba(255,255,255,0.7);
                margin-top: 15px;
                font-size: 14px;
                position: relative;
                z-index: 1;
            }}
            .content {{
                padding: 40px;
                color: #e2e8f0;
            }}
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }}
            .kpi-card {{
                background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                padding: 28px;
                border-radius: 12px;
                border-left: 4px solid #3b82f6;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            }}
            .kpi-card:hover {{
                transform: translateY(-4px);
            }}
            .kpi-label {{
                color: #a0aec0;
                font-size: 13px;
                margin-bottom: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .kpi-value {{
                font-size: 32px;
                font-weight: bold;
                color: #e2e8f0;
                margin-bottom: 8px;
            }}
            .kpi-change {{
                font-size: 14px;
                font-weight: 500;
            }}
            .section {{
                background: #2d3748;
                padding: 28px;
                border-radius: 12px;
                margin-bottom: 24px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .section-title {{
                font-size: 22px;
                font-weight: bold;
                margin-bottom: 20px;
                color: #e2e8f0;
                border-bottom: 3px solid #3b82f6;
                padding-bottom: 12px;
                display: flex;
                align-items: center;
            }}
            .section-title::before {{
                content: '';
                display: inline-block;
                width: 6px;
                height: 24px;
                background: #3b82f6;
                margin-right: 12px;
                border-radius: 3px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th {{
                text-align: left;
                padding: 14px 12px;
                background: #1a202c;
                color: #a0aec0;
                font-weight: 600;
                border-bottom: 2px solid #3b82f6;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 MASTER EXECUTIVE SUMMARY</h1>
                <div class="subtitle">Your Daily Trading Intelligence Briefing</div>
                <div class="timestamp">{datetime.now().strftime('%A, %B %d, %Y • %H:%M:%S')}</div>
            </div>

            <div class="content">
                <!-- Executive KPIs -->
                {kpi_cards}

                <!-- Daily Highlights -->
                <div class="section">
                    <div class="section-title">🎯 TODAY'S HIGHLIGHTS</div>
                    {highlights_html}
                </div>

                <!-- Critical Actions -->
                <div class="section">
                    <div class="section-title">🚨 PRIORITY ACTIONS</div>
                    <table>
                        <tr>
                            <th style="width: 15%;">Priority</th>
                            <th style="width: 15%;">Category</th>
                            <th style="width: 55%;">Action Required</th>
                            <th style="width: 15%;">Impact</th>
                        </tr>
                        {actions_html}
                    </table>
                </div>

                <!-- Market Opportunities -->
                <div class="section">
                    <div class="section-title">💎 MARKET OPPORTUNITIES</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Direction</th>
                            <th>Reason</th>
                            <th>Confidence</th>
                        </tr>
                        {opportunities_html}
                    </table>
                </div>

                <!-- Footer -->
                <div style="margin-top: 40px; padding-top: 24px; border-top: 2px solid #2d3748; text-align: center; color: #a0aec0; font-size: 13px;">
                    <p style="margin: 8px 0;">
                        <strong style="color: #3b82f6;">Available Reports:</strong>
                        python trade.py digest | ai | signals | risk | perf | ta
                    </p>
                    <p style="margin: 8px 0;">
                        Generated by PropShop Trading Intelligence System
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def run():
    """Main execution"""
    print("="*80)
    print("MASTER EXECUTIVE SUMMARY")
    print("="*80)
    print()

    if not init_mt5():
        print("[ERROR] Failed to initialize MT5")
        return

    account = get_account_info()
    positions = get_positions()

    print("[1/5] Calculating executive KPIs...")
    kpis = get_executive_kpis(account, positions)

    print("[2/5] Identifying critical actions...")
    actions = identify_critical_actions(kpis, positions)

    print("[3/5] Scanning market opportunities...")
    opportunities = get_market_opportunities()

    print("[4/5] Generating daily highlights...")
    highlights = get_daily_highlights(kpis, positions)

    print("[5/5] Creating executive summary report...")
    html_report = generate_executive_html_report(kpis, actions, opportunities, highlights)

    # Send email
    print("\nSending master executive summary to email...")
    subject = f"📊 Executive Summary - {datetime.now().strftime('%Y-%m-%d')}"

    if send_email(subject, html_report):
        print("[SUCCESS] Executive summary sent!")
    else:
        print("[ERROR] Failed to send email")

    # Print summary
    print("\n" + "="*80)
    print("EXECUTIVE SUMMARY")
    print("="*80)

    print(f"\nPORTFOLIO: ${kpis['equity']:,.2f} ({kpis['drawdown_pct']:+.1f}%)")
    print(f"WIN RATE: {kpis['win_rate']:.1f}% ({kpis['winners']}W / {kpis['losers']}L)")
    print(f"PROFIT FACTOR: {kpis['profit_factor']:.2f}x")
    print(f"POSITIONS: {kpis['num_positions']}/{MAX_POSITIONS}")

    print(f"\nTOP {min(3, len(actions))} PRIORITY ACTIONS:")
    for i, action in enumerate(actions[:3], 1):
        print(f"  {i}. [{action['priority']}] {action['action']}")
        print(f"     {action['description']}")

    print(f"\nTOP {min(3, len(opportunities))} OPPORTUNITIES:")
    for i, opp in enumerate(opportunities[:3], 1):
        print(f"  {i}. {opp['symbol']} {opp['direction']} - {opp['reason']} ({opp['confidence']}%)")

    print("\n[DONE]\n")


if __name__ == "__main__":
    run()
