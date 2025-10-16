"""
PERFORMANCE ATTRIBUTION ANALYSIS
Shows exactly which strategies and assets are making/losing money
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import *
from core.mt5_service import init_mt5, get_positions, get_account_info
from core.email_service import send_email
import MetaTrader5 as mt5


def categorize_asset(symbol):
    """Categorize asset by type"""
    if symbol in METALS:
        return 'METALS'
    elif symbol in FOREX_MAJORS:
        return 'FOREX_MAJORS'
    elif symbol in FOREX_CROSSES:
        return 'FOREX_CROSSES'
    elif symbol in CRYPTO:
        return 'CRYPTO'
    elif symbol in INDICES:
        return 'INDICES'
    elif symbol in COMMODITIES:
        return 'COMMODITIES'
    else:
        return 'OTHER'


def get_historical_deals(days=30):
    """Get historical deals for performance attribution"""
    from_date = datetime.now() - timedelta(days=days)

    deals = mt5.history_deals_get(from_date, datetime.now())

    if deals is None or len(deals) == 0:
        return []

    return [d._asdict() for d in deals]


def analyze_performance_by_category():
    """Analyze P&L by asset category"""
    positions = get_positions()

    if not positions:
        return {}

    category_pnl = {}
    category_counts = {}
    category_positions = {}

    for pos in positions:
        category = categorize_asset(pos.symbol)

        if category not in category_pnl:
            category_pnl[category] = 0
            category_counts[category] = 0
            category_positions[category] = []

        category_pnl[category] += pos.profit
        category_counts[category] += 1
        category_positions[category].append({
            'symbol': pos.symbol,
            'type': 'LONG' if pos.type == 0 else 'SHORT',
            'profit': pos.profit,
            'volume': pos.volume,
            'entry': pos.price_open,
            'current': pos.price_current
        })

    # Calculate percentages
    total_pnl = sum(category_pnl.values())

    results = []
    for category in sorted(category_pnl.keys()):
        pnl = category_pnl[category]
        count = category_counts[category]
        pct_of_total = (pnl / total_pnl * 100) if total_pnl != 0 else 0

        results.append({
            'category': category,
            'pnl': pnl,
            'count': count,
            'avg_pnl': pnl / count if count > 0 else 0,
            'pct_of_total': pct_of_total,
            'positions': category_positions[category]
        })

    # Sort by P&L
    results.sort(key=lambda x: x['pnl'], reverse=True)

    return results


def analyze_performance_by_direction():
    """Analyze LONG vs SHORT performance"""
    positions = get_positions()

    if not positions:
        return {}

    long_pnl = 0
    short_pnl = 0
    long_count = 0
    short_count = 0

    long_positions = []
    short_positions = []

    for pos in positions:
        if pos.type == 0:  # LONG
            long_pnl += pos.profit
            long_count += 1
            long_positions.append({
                'symbol': pos.symbol,
                'profit': pos.profit,
                'entry': pos.price_open,
                'current': pos.price_current
            })
        else:  # SHORT
            short_pnl += pos.profit
            short_count += 1
            short_positions.append({
                'symbol': pos.symbol,
                'profit': pos.profit,
                'entry': pos.price_open,
                'current': pos.price_current
            })

    return {
        'LONG': {
            'pnl': long_pnl,
            'count': long_count,
            'avg': long_pnl / long_count if long_count > 0 else 0,
            'positions': long_positions
        },
        'SHORT': {
            'pnl': short_pnl,
            'count': short_count,
            'avg': short_pnl / short_count if short_count > 0 else 0,
            'positions': short_positions
        }
    }


def analyze_winners_vs_losers():
    """Analyze winning vs losing positions"""
    positions = get_positions()

    if not positions:
        return {}

    winners = []
    losers = []

    for pos in positions:
        pos_data = {
            'symbol': pos.symbol,
            'type': 'LONG' if pos.type == 0 else 'SHORT',
            'profit': pos.profit,
            'profit_pct': (pos.profit / (pos.volume * pos.price_open)) * 100,
            'entry': pos.price_open,
            'current': pos.price_current,
            'volume': pos.volume
        }

        if pos.profit > 0:
            winners.append(pos_data)
        else:
            losers.append(pos_data)

    # Sort by profit
    winners.sort(key=lambda x: x['profit'], reverse=True)
    losers.sort(key=lambda x: x['profit'])

    total_winners_pnl = sum(w['profit'] for w in winners)
    total_losers_pnl = sum(l['profit'] for l in losers)

    return {
        'winners': winners,
        'losers': losers,
        'winner_count': len(winners),
        'loser_count': len(losers),
        'total_winners_pnl': total_winners_pnl,
        'total_losers_pnl': total_losers_pnl,
        'win_rate': (len(winners) / len(positions) * 100) if positions else 0
    }


def analyze_position_ages():
    """Analyze how long positions have been open"""
    positions = get_positions()

    if not positions:
        return []

    now = datetime.now()
    position_ages = []

    for pos in positions:
        age_seconds = (now.timestamp() - pos.time)
        age_days = age_seconds / 86400
        age_hours = age_seconds / 3600

        position_ages.append({
            'symbol': pos.symbol,
            'type': 'LONG' if pos.type == 0 else 'SHORT',
            'profit': pos.profit,
            'age_days': age_days,
            'age_hours': age_hours,
            'open_time': datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M')
        })

    # Sort by age
    position_ages.sort(key=lambda x: x['age_days'], reverse=True)

    return position_ages


def generate_html_report(category_analysis, direction_analysis, winners_losers, position_ages, account):
    """Generate beautiful HTML report"""

    # Top Winners & Losers
    top_winners_html = ""
    for winner in winners_losers['winners'][:5]:
        top_winners_html += f"""
        <tr style="background: rgba(16, 185, 129, 0.05);">
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #10b981;">
                {winner['symbol']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {winner['type']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #10b981; font-weight: bold;">
                ${winner['profit']:+,.2f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #10b981;">
                {winner['profit_pct']:+.2f}%
            </td>
        </tr>
        """

    top_losers_html = ""
    for loser in winners_losers['losers'][:5]:
        top_losers_html += f"""
        <tr style="background: rgba(239, 68, 68, 0.05);">
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #ef4444;">
                {loser['symbol']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {loser['type']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #ef4444; font-weight: bold;">
                ${loser['profit']:+,.2f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #ef4444;">
                {loser['profit_pct']:+.2f}%
            </td>
        </tr>
        """

    # Category Performance
    category_html = ""
    for cat in category_analysis:
        color = "#10b981" if cat['pnl'] > 0 else "#ef4444"
        bg_color = "rgba(16, 185, 129, 0.05)" if cat['pnl'] > 0 else "rgba(239, 68, 68, 0.05)"

        category_html += f"""
        <tr style="background: {bg_color};">
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; font-weight: bold;">
                {cat['category']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {color}; font-weight: bold;">
                ${cat['pnl']:+,.2f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {cat['count']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {color};">
                ${cat['avg_pnl']:+,.2f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {color};">
                {cat['pct_of_total']:+.1f}%
            </td>
        </tr>
        """

    # Direction Performance
    long_data = direction_analysis['LONG']
    short_data = direction_analysis['SHORT']

    long_color = "#10b981" if long_data['pnl'] > 0 else "#ef4444"
    short_color = "#10b981" if short_data['pnl'] > 0 else "#ef4444"

    # Oldest Positions
    oldest_html = ""
    for pos in position_ages[:10]:
        color = "#10b981" if pos['profit'] > 0 else "#ef4444"

        oldest_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {pos['symbol']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {pos['type']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {pos['age_days']:.1f} days
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {pos['open_time']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {color}; font-weight: bold;">
                ${pos['profit']:+,.2f}
            </td>
        </tr>
        """

    # Win Rate Gauge
    win_rate = winners_losers['win_rate']
    win_rate_color = "#10b981" if win_rate >= 50 else "#ef4444" if win_rate < 40 else "#f59e0b"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: #1a202c;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px;
                text-align: center;
                color: white;
            }}
            .header h1 {{
                margin: 0;
                font-size: 36px;
                font-weight: bold;
            }}
            .timestamp {{
                color: rgba(255,255,255,0.8);
                margin-top: 10px;
                font-size: 14px;
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
                background: #2d3748;
                padding: 24px;
                border-radius: 12px;
                border-left: 4px solid #667eea;
            }}
            .kpi-label {{
                color: #a0aec0;
                font-size: 14px;
                margin-bottom: 8px;
            }}
            .kpi-value {{
                font-size: 28px;
                font-weight: bold;
                color: #e2e8f0;
            }}
            .section {{
                background: #2d3748;
                padding: 24px;
                border-radius: 12px;
                margin-bottom: 24px;
            }}
            .section-title {{
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 20px;
                color: #e2e8f0;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th {{
                text-align: left;
                padding: 12px;
                background: #1a202c;
                color: #a0aec0;
                font-weight: 600;
                border-bottom: 2px solid #667eea;
            }}
            .alert {{
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 16px;
                border-left: 4px solid;
            }}
            .alert-warning {{
                background: rgba(251, 191, 36, 0.1);
                border-color: #fbbf24;
                color: #fbbf24;
            }}
            .alert-danger {{
                background: rgba(239, 68, 68, 0.1);
                border-color: #ef4444;
                color: #ef4444;
            }}
            .alert-success {{
                background: rgba(16, 185, 129, 0.1);
                border-color: #10b981;
                color: #10b981;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 PERFORMANCE ATTRIBUTION ANALYSIS</h1>
                <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>

            <div class="content">
                <!-- KPI Dashboard -->
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">Total P&L</div>
                        <div class="kpi-value" style="color: {'#10b981' if account.profit > 0 else '#ef4444'}">
                            ${account.profit:+,.2f}
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Win Rate</div>
                        <div class="kpi-value" style="color: {win_rate_color}">
                            {win_rate:.1f}%
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Winners / Losers</div>
                        <div class="kpi-value">
                            {winners_losers['winner_count']} / {winners_losers['loser_count']}
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Open Positions</div>
                        <div class="kpi-value">
                            {winners_losers['winner_count'] + winners_losers['loser_count']}
                        </div>
                    </div>
                </div>

                <!-- LONG vs SHORT Performance -->
                <div class="section">
                    <div class="section-title">🎯 LONG vs SHORT Performance</div>
                    <table>
                        <tr>
                            <th>Direction</th>
                            <th>P&L</th>
                            <th>Count</th>
                            <th>Average P&L</th>
                        </tr>
                        <tr style="background: rgba(16, 185, 129, 0.05);">
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748; font-weight: bold;">
                                LONG
                            </td>
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {long_color}; font-weight: bold;">
                                ${long_data['pnl']:+,.2f}
                            </td>
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                                {long_data['count']}
                            </td>
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {long_color};">
                                ${long_data['avg']:+,.2f}
                            </td>
                        </tr>
                        <tr style="background: rgba(239, 68, 68, 0.05);">
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748; font-weight: bold;">
                                SHORT
                            </td>
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {short_color}; font-weight: bold;">
                                ${short_data['pnl']:+,.2f}
                            </td>
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                                {short_data['count']}
                            </td>
                            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {short_color};">
                                ${short_data['avg']:+,.2f}
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- Performance by Asset Category -->
                <div class="section">
                    <div class="section-title">📈 Performance by Asset Category</div>
                    <table>
                        <tr>
                            <th>Category</th>
                            <th>Total P&L</th>
                            <th>Count</th>
                            <th>Avg P&L</th>
                            <th>% of Total</th>
                        </tr>
                        {category_html}
                    </table>
                </div>

                <!-- Top Winners -->
                <div class="section">
                    <div class="section-title">🏆 TOP 5 WINNERS</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>P&L</th>
                            <th>Return %</th>
                        </tr>
                        {top_winners_html}
                    </table>
                </div>

                <!-- Top Losers -->
                <div class="section">
                    <div class="section-title">❌ TOP 5 LOSERS</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>P&L</th>
                            <th>Return %</th>
                        </tr>
                        {top_losers_html}
                    </table>
                </div>

                <!-- Oldest Positions -->
                <div class="section">
                    <div class="section-title">⏰ OLDEST POSITIONS (Potential Dead Weight)</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>Age</th>
                            <th>Opened</th>
                            <th>P&L</th>
                        </tr>
                        {oldest_html}
                    </table>
                </div>

                <!-- Key Insights -->
                <div class="section">
                    <div class="section-title">💡 KEY INSIGHTS</div>
                    {'<div class="alert alert-danger">⚠️ Win rate below 40% - Your strategy selection needs improvement</div>' if win_rate < 40 else ''}
                    {'<div class="alert alert-warning">⚠️ Win rate below 50% - Consider improving entry timing</div>' if 40 <= win_rate < 50 else ''}
                    {'<div class="alert alert-success">✓ Win rate above 50% - Good strategy selection</div>' if win_rate >= 50 else ''}

                    {'<div class="alert alert-danger">⚠️ SHORT positions losing significantly - Avoid counter-trend shorts</div>' if short_data['pnl'] < -5000 else ''}
                    {'<div class="alert alert-danger">⚠️ LONG positions losing significantly - Market may be in downtrend</div>' if long_data['pnl'] < -5000 else ''}

                    {'<div class="alert alert-warning">⚠️ Multiple positions over 7 days old - Consider closing dead weight</div>' if len([p for p in position_ages if p['age_days'] > 7]) > 3 else ''}

                    <div class="alert alert-warning">
                        💰 Winners total: ${winners_losers['total_winners_pnl']:,.2f}<br>
                        💸 Losers total: ${winners_losers['total_losers_pnl']:,.2f}<br>
                        📊 Ratio: {abs(winners_losers['total_winners_pnl'] / winners_losers['total_losers_pnl']):.2f}x {'(Winners outpacing losers)' if winners_losers['total_winners_pnl'] > abs(winners_losers['total_losers_pnl']) else '(Losers outpacing winners - CUT LOSSES!)'}
                    </div>
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
    print("PERFORMANCE ATTRIBUTION ANALYSIS")
    print("="*80)
    print()

    if not init_mt5():
        print("[ERROR] Failed to initialize MT5")
        return

    account = get_account_info()

    print("[1/5] Analyzing performance by asset category...")
    category_analysis = analyze_performance_by_category()

    print("[2/5] Analyzing LONG vs SHORT performance...")
    direction_analysis = analyze_performance_by_direction()

    print("[3/5] Analyzing winners vs losers...")
    winners_losers = analyze_winners_vs_losers()

    print("[4/5] Analyzing position ages...")
    position_ages = analyze_position_ages()

    print("[5/5] Generating performance attribution report...")
    html_report = generate_html_report(
        category_analysis,
        direction_analysis,
        winners_losers,
        position_ages,
        account
    )

    # Send email
    print("\nSending performance attribution report to email...")
    subject = f"📊 Performance Attribution - {datetime.now().strftime('%Y-%m-%d')}"

    if send_email(subject, html_report):
        print("[SUCCESS] Performance attribution report sent!")
    else:
        print("[ERROR] Failed to send email")

    # Print summary to console
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)

    print(f"\n{'CATEGORY':<20} {'P&L':>15} {'COUNT':>10} {'AVG P&L':>15}")
    print("-"*80)
    for cat in category_analysis:
        print(f"{cat['category']:<20} ${cat['pnl']:>14,.2f} {cat['count']:>10} ${cat['avg_pnl']:>14,.2f}")

    print(f"\n\n{'DIRECTION':<20} {'P&L':>15} {'COUNT':>10} {'AVG P&L':>15}")
    print("-"*80)
    long_data = direction_analysis['LONG']
    short_data = direction_analysis['SHORT']
    print(f"{'LONG':<20} ${long_data['pnl']:>14,.2f} {long_data['count']:>10} ${long_data['avg']:>14,.2f}")
    print(f"{'SHORT':<20} ${short_data['pnl']:>14,.2f} {short_data['count']:>10} ${short_data['avg']:>14,.2f}")

    print(f"\n\nWIN RATE: {winners_losers['win_rate']:.1f}%")
    print(f"Winners: {winners_losers['winner_count']} (${winners_losers['total_winners_pnl']:,.2f})")
    print(f"Losers: {winners_losers['loser_count']} (${winners_losers['total_losers_pnl']:,.2f})")

    print("\n[DONE]\n")


if __name__ == "__main__":
    run()
