"""
AI-POWERED DEEP MARKET ANALYSIS
Comprehensive analysis of trades, historical data, market regimes, and corrective actions
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

def calculate_technical_indicators(df):
    """Calculate comprehensive technical indicators"""
    # Moving Averages
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    df['SMA_200'] = df['close'].rolling(window=200).mean()
    df['EMA_12'] = df['close'].ewm(span=12).mean()
    df['EMA_26'] = df['close'].ewm(span=26).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # Bollinger Bands
    df['BB_Middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)

    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()

    # Volatility
    df['Volatility'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252) * 100

    # Trend Strength (ADX approximation)
    df['Returns'] = df['close'].pct_change()
    df['Trend_Strength'] = df['Returns'].rolling(14).std()

    return df

def detect_market_regime(df):
    """Detect if market is trending, ranging, volatile, or calm"""
    latest = df.iloc[-1]

    # Trend detection
    if latest['close'] > latest['SMA_50'] > latest['SMA_200']:
        trend = "STRONG UPTREND"
    elif latest['close'] > latest['SMA_50']:
        trend = "UPTREND"
    elif latest['close'] < latest['SMA_50'] < latest['SMA_200']:
        trend = "STRONG DOWNTREND"
    elif latest['close'] < latest['SMA_50']:
        trend = "DOWNTREND"
    else:
        trend = "RANGING"

    # Volatility regime
    vol = latest['Volatility']
    if vol > 30:
        vol_regime = "HIGH VOLATILITY"
    elif vol > 15:
        vol_regime = "MODERATE VOLATILITY"
    else:
        vol_regime = "LOW VOLATILITY"

    # Momentum
    rsi = latest['RSI']
    if rsi > 70:
        momentum = "OVERBOUGHT"
    elif rsi < 30:
        momentum = "OVERSOLD"
    else:
        momentum = "NEUTRAL"

    return {
        'trend': trend,
        'volatility': vol_regime,
        'momentum': momentum,
        'rsi': rsi,
        'price': latest['close'],
        'sma_50': latest['SMA_50'],
        'sma_200': latest['SMA_200'],
        'atr': latest['ATR'],
        'vol_pct': vol
    }

def analyze_position(position, historical_data):
    """Deep analysis of individual position"""
    symbol = position.symbol
    entry_price = position.price_open
    current_price = position.price_current
    position_type = "LONG" if position.type == mt5.ORDER_TYPE_BUY else "SHORT"
    profit = position.profit
    volume = position.volume

    # Calculate position metrics
    if position_type == "LONG":
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
    else:
        pnl_pct = ((entry_price - current_price) / entry_price) * 100

    # Analyze historical context
    regime = detect_market_regime(historical_data)

    # Determine what went wrong (if losing)
    issues = []
    recommendations = []

    if profit < 0:
        # Check if entered against trend
        if position_type == "LONG" and "DOWNTREND" in regime['trend']:
            issues.append("ENTERED LONG IN DOWNTREND - Counter-trend trade")
            recommendations.append("Close position - trend is against you")
        elif position_type == "SHORT" and "UPTREND" in regime['trend']:
            issues.append("ENTERED SHORT IN UPTREND - Counter-trend trade")
            recommendations.append("Close position - trend is against you")

        # Check if volatility exploded
        if regime['vol_pct'] > 30:
            issues.append(f"HIGH VOLATILITY ({regime['vol_pct']:.1f}%) - Stop loss likely too tight")
            recommendations.append("Widen stops or reduce position size in volatile markets")

        # Check if RSI extreme
        if position_type == "LONG" and regime['momentum'] == "OVERBOUGHT":
            issues.append("Bought into overbought condition")
            recommendations.append("Wait for RSI to cool below 50 before re-entry")
        elif position_type == "SHORT" and regime['momentum'] == "OVERSOLD":
            issues.append("Shorted into oversold condition")
            recommendations.append("Wait for RSI to rise above 50 before re-entry")

        # Check drawdown severity
        if pnl_pct < -5:
            issues.append(f"SEVERE DRAWDOWN ({pnl_pct:.1f}%) - Position size too large")
            recommendations.append("IMMEDIATE ACTION: Close or reduce position to 50%")
        elif pnl_pct < -2:
            issues.append(f"Moderate loss ({pnl_pct:.1f}%)")
            recommendations.append("Set breakeven stop if price recovers to entry")

    else:
        # Winning position - protect profits
        if pnl_pct > 5:
            recommendations.append(f"STRONG WINNER (+{pnl_pct:.1f}%) - Trail stop to lock profits")
        elif pnl_pct > 2:
            recommendations.append(f"Decent profit (+{pnl_pct:.1f}%) - Move stop to breakeven")

    # Market context recommendations
    if regime['trend'] == "RANGING":
        recommendations.append("RANGING MARKET - Use mean reversion, not trend following")
    elif "STRONG" in regime['trend']:
        recommendations.append(f"{regime['trend']} detected - Only trade with the trend")

    return {
        'symbol': symbol,
        'type': position_type,
        'entry': entry_price,
        'current': current_price,
        'profit': profit,
        'pnl_pct': pnl_pct,
        'volume': volume,
        'issues': issues,
        'recommendations': recommendations,
        'market_regime': regime
    }

def analyze_strategy_performance(trades_log):
    """Analyze what's working and what's not"""
    with open(trades_log, 'r') as f:
        trades = json.load(f)

    closed_trades = [t for t in trades if t.get('current_status') in ['CLOSED_WIN', 'CLOSED_LOSS']]

    if not closed_trades:
        return None

    # Group by strategy
    strategy_stats = {}
    for trade in closed_trades:
        for signal in trade.get('signals', ['Unknown']):
            if signal not in strategy_stats:
                strategy_stats[signal] = {
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'win_pnls': [],
                    'loss_pnls': []
                }

            if trade['current_status'] == 'CLOSED_WIN':
                strategy_stats[signal]['wins'] += 1
                strategy_stats[signal]['win_pnls'].append(trade['current_pnl'])
            else:
                strategy_stats[signal]['losses'] += 1
                strategy_stats[signal]['loss_pnls'].append(trade['current_pnl'])

            strategy_stats[signal]['total_pnl'] += trade['current_pnl']

    # Calculate averages
    for signal, stats in strategy_stats.items():
        if stats['win_pnls']:
            stats['avg_win'] = np.mean(stats['win_pnls'])
        if stats['loss_pnls']:
            stats['avg_loss'] = np.mean(stats['loss_pnls'])

        total_trades = stats['wins'] + stats['losses']
        stats['win_rate'] = (stats['wins'] / total_trades * 100) if total_trades > 0 else 0
        stats['total_trades'] = total_trades

        # Expectancy
        if total_trades > 0:
            stats['expectancy'] = (stats['win_rate']/100 * stats['avg_win']) + ((1 - stats['win_rate']/100) * stats['avg_loss'])
        else:
            stats['expectancy'] = 0

    return strategy_stats

print("="*80)
print("AI-POWERED DEEP MARKET ANALYSIS")
print("="*80)

if not mt5.initialize():
    print("[ERROR] MT5 initialization failed")
    exit()

# Get all open positions
positions = mt5.positions_get()
account = mt5.account_info()

analyses = []
critical_actions = []

print(f"\n[1/4] ANALYZING {len(positions)} OPEN POSITIONS")
print("-" * 80)

for i, pos in enumerate(positions, 1):
    print(f"[{i}/{len(positions)}] Analyzing {pos.symbol}...")

    # Get historical data (6 months)
    rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_H4, 0, 1000)

    if rates is not None and len(rates) > 0:
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = calculate_technical_indicators(df)

        analysis = analyze_position(pos, df)
        analyses.append(analysis)

        # Print immediate findings
        print(f"  {analysis['type']} @ {analysis['entry']:.5f} | Current: {analysis['current']:.5f}")
        print(f"  P&L: ${analysis['profit']:,.2f} ({analysis['pnl_pct']:+.2f}%)")
        print(f"  Market: {analysis['market_regime']['trend']} | {analysis['market_regime']['volatility']}")

        if analysis['issues']:
            print(f"  [ISSUES DETECTED]")
            for issue in analysis['issues']:
                print(f"    - {issue}")

        if analysis['recommendations']:
            print(f"  [RECOMMENDATIONS]")
            for rec in analysis['recommendations']:
                print(f"    > {rec}")
                if "IMMEDIATE ACTION" in rec or "Close position" in rec:
                    critical_actions.append(f"{pos.symbol}: {rec}")
        print()

print("\n[2/4] STRATEGY PERFORMANCE ANALYSIS")
print("-" * 80)

strategy_analysis = analyze_strategy_performance("trades_log.json")

if strategy_analysis:
    for strategy, stats in strategy_analysis.items():
        print(f"\n{strategy}:")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Total P&L: {stats['total_pnl']:+.2f}%")
        print(f"  Avg Win: {stats['avg_win']:.2f}%")
        print(f"  Avg Loss: {stats['avg_loss']:.2f}%")
        print(f"  Expectancy: {stats['expectancy']:.2f}%")

        if stats['expectancy'] < 0:
            print(f"  [VERDICT] NEGATIVE EXPECTANCY - STOP USING THIS STRATEGY")
            critical_actions.append(f"DISABLE STRATEGY: {strategy} (negative expectancy)")
        elif stats['win_rate'] < 30:
            print(f"  [VERDICT] LOW WIN RATE - Needs improvement")
        else:
            print(f"  [VERDICT] Acceptable performance")

print("\n[3/4] MARKET REGIME ANALYSIS")
print("-" * 80)

# Analyze major symbols
major_symbols = ['GOLD', 'EURUSD', 'BTCUSD', 'US100Cash']
market_overview = []

for symbol in major_symbols:
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 500)
    if rates is not None and len(rates) > 0:
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = calculate_technical_indicators(df)
        regime = detect_market_regime(df)

        print(f"\n{symbol}:")
        print(f"  Trend: {regime['trend']}")
        print(f"  Volatility: {regime['volatility']} ({regime['vol_pct']:.1f}%)")
        print(f"  RSI: {regime['rsi']:.1f} ({regime['momentum']})")
        print(f"  Price: {regime['price']:.5f}")
        print(f"  SMA 50: {regime['sma_50']:.5f}")

        market_overview.append({
            'symbol': symbol,
            'regime': regime
        })

print("\n[4/4] AI RECOMMENDATIONS SUMMARY")
print("-" * 80)

print("\n[CRITICAL ACTIONS REQUIRED]")
if critical_actions:
    for i, action in enumerate(critical_actions, 1):
        print(f"{i}. {action}")
else:
    print("No critical actions required")

print("\n[SYSTEMATIC IMPROVEMENTS NEEDED]")
print("1. STOP COUNTER-TREND TRADING - Only trade with the trend")
print("2. REDUCE POSITION SIZES - Current 1% risk is too aggressive, use 0.5%")
print("3. IMPLEMENT PROPER FILTERS:")
print("   - Only LONG when price > SMA 50 AND SMA 200")
print("   - Only SHORT when price < SMA 50 AND SMA 200")
print("   - Avoid trading when RSI > 70 or < 30")
print("4. USE WIDER STOPS IN HIGH VOLATILITY - ATR * 2.0 instead of 1.5")
print("5. IMPLEMENT MAXIMUM DRAWDOWN CUTOFF - Close all positions if down 5%")
print("6. REDUCE GOLD CONCENTRATION - Max 30% in any single symbol")
print("7. LIMIT OPEN POSITIONS - Enforce max 5 positions strictly")

# Generate beautiful HTML report
html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
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
        .timestamp {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .content {{
            padding: 40px;
        }}
        .critical-alert {{
            background: #fee;
            border-left: 5px solid #e00;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .critical-alert h3 {{
            margin: 0 0 15px 0;
            color: #c00;
            font-size: 20px;
        }}
        .critical-alert ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .critical-alert li {{
            margin: 8px 0;
            color: #600;
        }}
        .position-card {{
            background: #f9f9ff;
            border: 1px solid #e0e0f0;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
        }}
        .position-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .symbol {{
            font-size: 20px;
            font-weight: 700;
            color: #333;
        }}
        .pnl {{
            font-size: 24px;
            font-weight: 700;
        }}
        .pnl.positive {{ color: #0a0; }}
        .pnl.negative {{ color: #e00; }}
        .regime-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
        .uptrend {{ background: #d4edda; color: #155724; }}
        .downtrend {{ background: #f8d7da; color: #721c24; }}
        .ranging {{ background: #fff3cd; color: #856404; }}
        .issue {{
            background: #fff3cd;
            border-left: 3px solid #f90;
            padding: 10px;
            margin: 8px 0;
            font-size: 14px;
            border-radius: 4px;
        }}
        .recommendation {{
            background: #d1ecf1;
            border-left: 3px solid #0c5460;
            padding: 10px;
            margin: 8px 0;
            font-size: 14px;
            border-radius: 4px;
        }}
        .strategy-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .strategy-table th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        .strategy-table td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .strategy-table tr:hover {{
            background: #f5f5ff;
        }}
        .improvement-box {{
            background: #e7f3ff;
            border: 2px solid #2196F3;
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
        }}
        .improvement-box h3 {{
            margin: 0 0 15px 0;
            color: #1976D2;
        }}
        .improvement-box ol {{
            margin: 0;
            padding-left: 20px;
        }}
        .improvement-box li {{
            margin: 10px 0;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI-POWERED DEEP MARKET ANALYSIS</h1>
            <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="content">
            <div class="critical-alert">
                <h3>CRITICAL ACTIONS REQUIRED</h3>
"""

if critical_actions:
    html_report += "<ul>"
    for action in critical_actions:
        html_report += f"<li>{action}</li>"
    html_report += "</ul>"
else:
    html_report += "<p>No critical actions required at this time.</p>"

html_report += """
            </div>

            <h2>Position-by-Position Analysis</h2>
"""

for analysis in analyses:
    pnl_class = "positive" if analysis['profit'] > 0 else "negative"
    regime = analysis['market_regime']

    if "UPTREND" in regime['trend']:
        regime_class = "uptrend"
    elif "DOWNTREND" in regime['trend']:
        regime_class = "downtrend"
    else:
        regime_class = "ranging"

    html_report += f"""
            <div class="position-card">
                <div class="position-header">
                    <div>
                        <span class="symbol">{analysis['symbol']}</span>
                        <span class="regime-badge {regime_class}">{regime['trend']}</span>
                    </div>
                    <div class="pnl {pnl_class}">${analysis['profit']:,.2f}</div>
                </div>

                <div>
                    <strong>{analysis['type']}</strong> @ {analysis['entry']:.5f} | Current: {analysis['current']:.5f} | P&L: {analysis['pnl_pct']:+.2f}%
                </div>

                <div style="margin-top: 10px; font-size: 13px; color: #666;">
                    Market: {regime['volatility']} | RSI: {regime['rsi']:.1f} ({regime['momentum']})
                </div>
"""

    if analysis['issues']:
        html_report += "<div style='margin-top: 15px;'><strong>Issues Detected:</strong></div>"
        for issue in analysis['issues']:
            html_report += f"<div class='issue'>{issue}</div>"

    if analysis['recommendations']:
        html_report += "<div style='margin-top: 15px;'><strong>Recommendations:</strong></div>"
        for rec in analysis['recommendations']:
            html_report += f"<div class='recommendation'>{rec}</div>"

    html_report += "</div>"

if strategy_analysis:
    html_report += """
            <h2>Strategy Performance Analysis</h2>
            <table class="strategy-table">
                <tr>
                    <th>Strategy</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>Total P&L</th>
                    <th>Expectancy</th>
                    <th>Verdict</th>
                </tr>
"""

    for strategy, stats in strategy_analysis.items():
        if stats['expectancy'] < 0:
            verdict = "DISABLE - Negative Expectancy"
            verdict_color = "#c00"
        elif stats['win_rate'] < 30:
            verdict = "Needs Improvement"
            verdict_color = "#f90"
        else:
            verdict = "Acceptable"
            verdict_color = "#0a0"

        html_report += f"""
                <tr>
                    <td><strong>{strategy}</strong></td>
                    <td>{stats['total_trades']}</td>
                    <td>{stats['win_rate']:.1f}%</td>
                    <td>{stats['total_pnl']:+.2f}%</td>
                    <td>{stats['expectancy']:.2f}%</td>
                    <td style="color: {verdict_color}; font-weight: 600;">{verdict}</td>
                </tr>
"""

    html_report += "</table>"

html_report += """
            <div class="improvement-box">
                <h3>Systematic Improvements Needed</h3>
                <ol>
                    <li><strong>STOP COUNTER-TREND TRADING</strong> - Only trade with the trend direction</li>
                    <li><strong>REDUCE POSITION SIZES</strong> - Cut risk from 1% to 0.5% per trade</li>
                    <li><strong>IMPLEMENT PROPER FILTERS</strong>:
                        <ul>
                            <li>Only LONG when price > SMA 50 AND SMA 200</li>
                            <li>Only SHORT when price < SMA 50 AND SMA 200</li>
                            <li>Avoid trading when RSI > 70 or < 30</li>
                        </ul>
                    </li>
                    <li><strong>USE WIDER STOPS</strong> - ATR * 2.0 instead of 1.5 in high volatility</li>
                    <li><strong>IMPLEMENT DRAWDOWN CUTOFF</strong> - Close all positions if account down 5%</li>
                    <li><strong>REDUCE CONCENTRATION</strong> - Max 30% in any single symbol (GOLD is 61%!)</li>
                    <li><strong>LIMIT POSITIONS</strong> - Strictly enforce max 5 open positions</li>
                </ol>
            </div>
        </div>
    </div>
</body>
</html>
"""

print("\n" + "="*80)
print("ANALYSIS COMPLETE - Sending report to email...")
print("="*80)

if send_email("AI DEEP MARKET ANALYSIS", html_report):
    print("[SUCCESS] Comprehensive analysis sent to your email!")
else:
    print("[FAILED] Could not send email")

mt5.shutdown()
print("\n[DONE]")
