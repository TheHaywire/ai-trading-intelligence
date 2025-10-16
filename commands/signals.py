"""
REAL-TIME SIGNALS & ALERTS SYSTEM
Comprehensive market signals and position monitoring with instant updates
"""

import sys
import os
from datetime import datetime
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import *
from core.mt5_service import init_mt5, get_positions, get_account_info, get_symbol_data
from core.analysis import calculate_indicators, detect_trend
from core.email_service import send_email
import MetaTrader5 as mt5


def detect_entry_signals():
    """Detect new trade entry signals across all symbols"""
    signals = []

    print("Scanning for entry signals across all markets...")

    for symbol in ALL_SYMBOLS[:15]:  # Scan top 15 for speed
        df = get_symbol_data(symbol, count=200)
        if df is None:
            continue

        df = calculate_indicators(df)
        trend, trend_score = detect_trend(df)

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        price = latest['close']
        rsi = latest['RSI']
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']
        stoch_k = latest['Stoch_K']
        stoch_d = latest['Stoch_D']
        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        bb_upper = latest['BB_Upper']
        bb_lower = latest['BB_Lower']

        # BULLISH SIGNALS
        if trend_score > 0:  # Uptrend
            # MACD Bullish Crossover
            if prev['MACD'] <= prev['MACD_Signal'] and macd > macd_signal:
                signals.append({
                    'symbol': symbol,
                    'type': 'LONG',
                    'signal': 'MACD Bullish Crossover',
                    'confidence': 85,
                    'price': price,
                    'rsi': rsi,
                    'trend': trend,
                    'reason': f"MACD crossed above signal in {trend}"
                })

            # RSI Oversold Bounce
            elif rsi < 35 and rsi > prev['RSI']:
                signals.append({
                    'symbol': symbol,
                    'type': 'LONG',
                    'signal': 'RSI Oversold Bounce',
                    'confidence': 80,
                    'price': price,
                    'rsi': rsi,
                    'trend': trend,
                    'reason': f"RSI bouncing from oversold in {trend}"
                })

            # Stochastic Golden Cross
            elif prev['Stoch_K'] <= prev['Stoch_D'] and stoch_k > stoch_d and stoch_k < 80:
                signals.append({
                    'symbol': symbol,
                    'type': 'LONG',
                    'signal': 'Stochastic Golden Cross',
                    'confidence': 75,
                    'price': price,
                    'rsi': rsi,
                    'trend': trend,
                    'reason': f"Stochastic K crossed above D in {trend}"
                })

            # Bollinger Band Bounce
            elif price <= bb_lower * 1.005 and price > prev['close']:
                signals.append({
                    'symbol': symbol,
                    'type': 'LONG',
                    'signal': 'Bollinger Band Bounce',
                    'confidence': 70,
                    'price': price,
                    'rsi': rsi,
                    'trend': trend,
                    'reason': f"Price bouncing off lower BB in {trend}"
                })

        # BEARISH SIGNALS
        elif trend_score < 0:  # Downtrend
            # MACD Bearish Crossover
            if prev['MACD'] >= prev['MACD_Signal'] and macd < macd_signal:
                signals.append({
                    'symbol': symbol,
                    'type': 'SHORT',
                    'signal': 'MACD Bearish Crossover',
                    'confidence': 85,
                    'price': price,
                    'rsi': rsi,
                    'trend': trend,
                    'reason': f"MACD crossed below signal in {trend}"
                })

            # RSI Overbought Rejection
            elif rsi > 65 and rsi < prev['RSI']:
                signals.append({
                    'symbol': symbol,
                    'type': 'SHORT',
                    'signal': 'RSI Overbought Rejection',
                    'confidence': 80,
                    'price': price,
                    'rsi': rsi,
                    'trend': trend,
                    'reason': f"RSI rejecting from overbought in {trend}"
                })

            # Stochastic Death Cross
            elif prev['Stoch_K'] >= prev['Stoch_D'] and stoch_k < stoch_d and stoch_k > 20:
                signals.append({
                    'symbol': symbol,
                    'type': 'SHORT',
                    'signal': 'Stochastic Death Cross',
                    'confidence': 75,
                    'price': price,
                    'rsi': rsi,
                    'trend': trend,
                    'reason': f"Stochastic K crossed below D in {trend}"
                })

    # Sort by confidence
    signals.sort(key=lambda x: x['confidence'], reverse=True)

    return signals


def detect_exit_signals():
    """Detect exit signals for current positions"""
    positions = get_positions()

    if not positions:
        return []

    exit_signals = []

    print("Checking exit signals for open positions...")

    for pos in positions:
        df = get_symbol_data(pos.symbol, count=200)
        if df is None:
            continue

        df = calculate_indicators(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        price = latest['close']
        rsi = latest['RSI']
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']
        stoch_k = latest['Stoch_K']
        stoch_d = latest['Stoch_D']

        position_type = 'LONG' if pos.type == 0 else 'SHORT'

        # EXIT SIGNALS FOR LONG POSITIONS
        if position_type == 'LONG':
            # MACD Bearish Crossover
            if prev['MACD'] >= prev['MACD_Signal'] and macd < macd_signal:
                exit_signals.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'signal': 'MACD Bearish Crossover',
                    'urgency': 'HIGH',
                    'profit': pos.profit,
                    'reason': 'MACD crossed below signal - momentum turning negative'
                })

            # RSI Overbought
            elif rsi > 75:
                exit_signals.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'signal': 'RSI Extreme Overbought',
                    'urgency': 'MEDIUM',
                    'profit': pos.profit,
                    'reason': f'RSI at {rsi:.1f} - potential reversal zone'
                })

            # Stochastic Death Cross
            elif prev['Stoch_K'] >= prev['Stoch_D'] and stoch_k < stoch_d and stoch_k > 80:
                exit_signals.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'signal': 'Stochastic Death Cross',
                    'urgency': 'MEDIUM',
                    'profit': pos.profit,
                    'reason': 'Stochastic K crossed below D from overbought'
                })

        # EXIT SIGNALS FOR SHORT POSITIONS
        else:
            # MACD Bullish Crossover
            if prev['MACD'] <= prev['MACD_Signal'] and macd > macd_signal:
                exit_signals.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'signal': 'MACD Bullish Crossover',
                    'urgency': 'HIGH',
                    'profit': pos.profit,
                    'reason': 'MACD crossed above signal - momentum turning positive'
                })

            # RSI Oversold
            elif rsi < 25:
                exit_signals.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'signal': 'RSI Extreme Oversold',
                    'urgency': 'MEDIUM',
                    'profit': pos.profit,
                    'reason': f'RSI at {rsi:.1f} - potential reversal zone'
                })

            # Stochastic Golden Cross
            elif prev['Stoch_K'] <= prev['Stoch_D'] and stoch_k > stoch_d and stoch_k < 20:
                exit_signals.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'signal': 'Stochastic Golden Cross',
                    'urgency': 'MEDIUM',
                    'profit': pos.profit,
                    'reason': 'Stochastic K crossed above D from oversold'
                })

    return exit_signals


def detect_position_alerts():
    """Detect alerts for position risk management"""
    positions = get_positions()

    if not positions:
        return []

    alerts = []

    print("Checking position risk alerts...")

    for pos in positions:
        position_value = pos.volume * pos.price_current
        profit_pct = (pos.profit / position_value) * 100

        # Large Loss Alert
        if pos.profit < -10000:
            alerts.append({
                'symbol': pos.symbol,
                'type': 'LARGE LOSS',
                'severity': 'CRITICAL',
                'profit': pos.profit,
                'profit_pct': profit_pct,
                'message': f'Position losing ${abs(pos.profit):,.2f} ({profit_pct:.1f}%) - Consider closing'
            })

        # Large Unrealized Profit
        elif pos.profit > 5000:
            alerts.append({
                'symbol': pos.symbol,
                'type': 'TAKE PROFIT',
                'severity': 'INFO',
                'profit': pos.profit,
                'profit_pct': profit_pct,
                'message': f'Position up ${pos.profit:,.2f} ({profit_pct:.1f}%) - Consider taking profit'
            })

        # Moderate Loss
        elif pos.profit < -3000:
            alerts.append({
                'symbol': pos.symbol,
                'type': 'MODERATE LOSS',
                'severity': 'WARNING',
                'profit': pos.profit,
                'profit_pct': profit_pct,
                'message': f'Position down ${abs(pos.profit):,.2f} ({profit_pct:.1f}%)'
            })

    return alerts


def detect_support_resistance_levels():
    """Detect key support/resistance levels for active positions"""
    positions = get_positions()

    if not positions:
        return []

    levels = []

    print("Calculating key support/resistance levels...")

    for pos in positions[:5]:  # Top 5 positions
        df = get_symbol_data(pos.symbol, count=500)
        if df is None:
            continue

        df = calculate_indicators(df)
        latest = df.iloc[-1]

        current_price = latest['close']

        # Calculate swing highs and lows
        recent_data = df.tail(100)

        highs = recent_data.nlargest(5, 'high')['high'].values
        lows = recent_data.nsmallest(5, 'low')['low'].values

        # Find nearest resistance (for LONG) or support (for SHORT)
        position_type = 'LONG' if pos.type == 0 else 'SHORT'

        if position_type == 'LONG':
            # Find resistance above current price
            resistance_levels = [h for h in highs if h > current_price]
            if resistance_levels:
                nearest_resistance = min(resistance_levels)
                distance_pct = ((nearest_resistance - current_price) / current_price) * 100

                levels.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'level_type': 'RESISTANCE',
                    'level': nearest_resistance,
                    'current': current_price,
                    'distance_pct': distance_pct,
                    'message': f'Nearest resistance at {nearest_resistance:.5f} ({distance_pct:+.2f}%)'
                })
        else:
            # Find support below current price
            support_levels = [l for l in lows if l < current_price]
            if support_levels:
                nearest_support = max(support_levels)
                distance_pct = ((nearest_support - current_price) / current_price) * 100

                levels.append({
                    'symbol': pos.symbol,
                    'type': position_type,
                    'level_type': 'SUPPORT',
                    'level': nearest_support,
                    'current': current_price,
                    'distance_pct': distance_pct,
                    'message': f'Nearest support at {nearest_support:.5f} ({distance_pct:+.2f}%)'
                })

    return levels


def detect_account_alerts(account):
    """Detect account-level risk alerts"""
    alerts = []

    # Calculate drawdown
    drawdown_pct = (account.profit / account.balance) * 100

    # Drawdown Alerts
    if drawdown_pct < -10:
        alerts.append({
            'type': 'CRITICAL DRAWDOWN',
            'severity': 'CRITICAL',
            'value': drawdown_pct,
            'message': f'Account in {drawdown_pct:.1f}% drawdown - EMERGENCY ACTION NEEDED'
        })
    elif drawdown_pct < -5:
        alerts.append({
            'type': 'HIGH DRAWDOWN',
            'severity': 'WARNING',
            'value': drawdown_pct,
            'message': f'Account in {drawdown_pct:.1f}% drawdown - Review positions'
        })

    # Position Count Alert
    positions = get_positions()
    if positions and len(positions) > MAX_POSITIONS:
        alerts.append({
            'type': 'POSITION LIMIT',
            'severity': 'WARNING',
            'value': len(positions),
            'message': f'{len(positions)} positions open (max {MAX_POSITIONS}) - Overexposed'
        })

    return alerts


def generate_signals_html_report(entry_signals, exit_signals, position_alerts, account_alerts, support_resistance, account):
    """Generate beautiful HTML report with all signals and alerts"""

    # Entry Signals
    entry_html = ""
    for sig in entry_signals[:10]:  # Top 10
        color = "#10b981" if sig['type'] == 'LONG' else "#ef4444"
        entry_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <strong>{sig['symbol']}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {color}; font-weight: bold;">
                {sig['type']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {sig['signal']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: #fbbf24;">
                {sig['confidence']}%
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {sig['price']:.5f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; font-size: 12px;">
                {sig['reason']}
            </td>
        </tr>
        """

    if not entry_signals:
        entry_html = '<tr><td colspan="6" style="padding: 20px; text-align: center; color: #a0aec0;">No entry signals detected</td></tr>'

    # Exit Signals
    exit_html = ""
    for sig in exit_signals:
        urgency_color = "#ef4444" if sig['urgency'] == 'HIGH' else "#fbbf24"
        profit_color = "#10b981" if sig['profit'] > 0 else "#ef4444"

        exit_html += f"""
        <tr style="background: rgba(239, 68, 68, 0.05);">
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <strong>{sig['symbol']}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {sig['type']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {sig['signal']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {urgency_color}; font-weight: bold;">
                {sig['urgency']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {profit_color};">
                ${sig['profit']:+,.2f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; font-size: 12px;">
                {sig['reason']}
            </td>
        </tr>
        """

    if not exit_signals:
        exit_html = '<tr><td colspan="6" style="padding: 20px; text-align: center; color: #10b981;">No exit signals - All positions looking good</td></tr>'

    # Position Alerts
    position_alerts_html = ""
    for alert in position_alerts:
        severity_colors = {
            'CRITICAL': '#ef4444',
            'WARNING': '#fbbf24',
            'INFO': '#10b981'
        }
        color = severity_colors.get(alert['severity'], '#a0aec0')

        position_alerts_html += f"""
        <div class="alert" style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid {color}; padding: 16px; margin-bottom: 12px; border-radius: 8px;">
            <strong style="color: {color};">[{alert['severity']}] {alert['symbol']} - {alert['type']}</strong><br>
            <span style="color: #e2e8f0;">{alert['message']}</span>
        </div>
        """

    if not position_alerts:
        position_alerts_html = '<div style="padding: 20px; text-align: center; color: #10b981;">All positions within acceptable risk parameters</div>'

    # Account Alerts
    account_alerts_html = ""
    for alert in account_alerts:
        severity_colors = {
            'CRITICAL': '#ef4444',
            'WARNING': '#fbbf24',
            'INFO': '#10b981'
        }
        color = severity_colors.get(alert['severity'], '#a0aec0')

        account_alerts_html += f"""
        <div class="alert" style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid {color}; padding: 16px; margin-bottom: 12px; border-radius: 8px;">
            <strong style="color: {color};">[{alert['severity']}] {alert['type']}</strong><br>
            <span style="color: #e2e8f0;">{alert['message']}</span>
        </div>
        """

    if not account_alerts:
        account_alerts_html = '<div style="padding: 20px; text-align: center; color: #10b981;">Account health looking good</div>'

    # Support/Resistance Levels
    levels_html = ""
    for level in support_resistance:
        color = "#10b981" if level['type'] == 'LONG' else "#ef4444"

        levels_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {level['symbol']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {color};">
                {level['type']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {level['level_type']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {level['level']:.5f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                {level['current']:.5f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {'#10b981' if level['distance_pct'] > 0 else '#ef4444'};">
                {level['distance_pct']:+.2f}%
            </td>
        </tr>
        """

    if not levels_html:
        levels_html = '<tr><td colspan="6" style="padding: 20px; text-align: center; color: #a0aec0;">No key levels identified</td></tr>'

    # Summary Stats
    total_entry_signals = len(entry_signals)
    total_exit_signals = len(exit_signals)
    critical_alerts = len([a for a in position_alerts + account_alerts if a['severity'] == 'CRITICAL'])
    warning_alerts = len([a for a in position_alerts + account_alerts if a['severity'] == 'WARNING'])

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
                max-width: 1400px;
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
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 REAL-TIME SIGNALS & ALERTS</h1>
                <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>

            <div class="content">
                <!-- KPI Dashboard -->
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">Entry Signals</div>
                        <div class="kpi-value" style="color: #10b981;">
                            {total_entry_signals}
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Exit Signals</div>
                        <div class="kpi-value" style="color: #ef4444;">
                            {total_exit_signals}
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Critical Alerts</div>
                        <div class="kpi-value" style="color: #ef4444;">
                            {critical_alerts}
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Warnings</div>
                        <div class="kpi-value" style="color: #fbbf24;">
                            {warning_alerts}
                        </div>
                    </div>
                </div>

                <!-- Account Alerts -->
                <div class="section">
                    <div class="section-title">🚨 ACCOUNT ALERTS</div>
                    {account_alerts_html}
                </div>

                <!-- Position Alerts -->
                <div class="section">
                    <div class="section-title">⚠️ POSITION ALERTS</div>
                    {position_alerts_html}
                </div>

                <!-- Exit Signals -->
                <div class="section">
                    <div class="section-title">🚪 EXIT SIGNALS (Close Positions)</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>Signal</th>
                            <th>Urgency</th>
                            <th>P&L</th>
                            <th>Reason</th>
                        </tr>
                        {exit_html}
                    </table>
                </div>

                <!-- Entry Signals -->
                <div class="section">
                    <div class="section-title">🎯 ENTRY SIGNALS (New Opportunities)</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>Signal</th>
                            <th>Confidence</th>
                            <th>Price</th>
                            <th>Reason</th>
                        </tr>
                        {entry_html}
                    </table>
                </div>

                <!-- Support/Resistance Levels -->
                <div class="section">
                    <div class="section-title">📊 KEY SUPPORT/RESISTANCE LEVELS</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>Position Type</th>
                            <th>Level Type</th>
                            <th>Level</th>
                            <th>Current Price</th>
                            <th>Distance</th>
                        </tr>
                        {levels_html}
                    </table>
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
    print("REAL-TIME SIGNALS & ALERTS SYSTEM")
    print("="*80)
    print()

    if not init_mt5():
        print("[ERROR] Failed to initialize MT5")
        return

    account = get_account_info()

    print("[1/6] Detecting entry signals...")
    entry_signals = detect_entry_signals()

    print(f"[2/6] Detecting exit signals...")
    exit_signals = detect_exit_signals()

    print("[3/6] Checking position alerts...")
    position_alerts = detect_position_alerts()

    print("[4/6] Checking account alerts...")
    account_alerts = detect_account_alerts(account)

    print("[5/6] Calculating support/resistance levels...")
    support_resistance = detect_support_resistance_levels()

    print("[6/6] Generating signals report...")
    html_report = generate_signals_html_report(
        entry_signals,
        exit_signals,
        position_alerts,
        account_alerts,
        support_resistance,
        account
    )

    # Send email
    print("\nSending signals & alerts report to email...")
    subject = f"🎯 Signals & Alerts - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    if send_email(subject, html_report):
        print("[SUCCESS] Signals & alerts report sent!")
    else:
        print("[ERROR] Failed to send email")

    # Print summary to console
    print("\n" + "="*80)
    print("SIGNALS SUMMARY")
    print("="*80)

    print(f"\nENTRY SIGNALS: {len(entry_signals)}")
    if entry_signals:
        for sig in entry_signals[:5]:
            print(f"  • {sig['symbol']} {sig['type']} - {sig['signal']} ({sig['confidence']}% confidence)")

    print(f"\nEXIT SIGNALS: {len(exit_signals)}")
    if exit_signals:
        for sig in exit_signals:
            print(f"  • {sig['symbol']} {sig['type']} - {sig['signal']} [{sig['urgency']}] (P&L: ${sig['profit']:+,.2f})")

    print(f"\nALERTS: {len(position_alerts) + len(account_alerts)}")
    for alert in account_alerts:
        print(f"  • [{alert['severity']}] {alert['type']}: {alert['message']}")
    for alert in position_alerts:
        print(f"  • [{alert['severity']}] {alert['symbol']} - {alert['message']}")

    print("\n[DONE]\n")


if __name__ == "__main__":
    run()
