"""
COMMAND: ta_report
Complete Technical Analysis Report with patterns, levels, and signals
"""

import sys
sys.path.append('..')

from core.mt5_service import *
from core.email_service import send_email
from core.analysis import *
from core.config import *
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

def detect_chart_patterns(df):
    """Detect common chart patterns"""
    patterns = []

    # Get last 50 candles for pattern detection
    recent = df.tail(50)

    # Double Top/Bottom detection
    highs_idx = argrelextrema(recent['high'].values, np.greater, order=5)[0]
    lows_idx = argrelextrema(recent['low'].values, np.less, order=5)[0]

    if len(highs_idx) >= 2:
        last_two_highs = highs_idx[-2:]
        high1 = recent.iloc[last_two_highs[0]]['high']
        high2 = recent.iloc[last_two_highs[1]]['high']

        if abs(high1 - high2) / high1 < 0.02:  # Within 2%
            patterns.append(('DOUBLE TOP', 'Bearish reversal pattern detected', 'warning'))

    if len(lows_idx) >= 2:
        last_two_lows = lows_idx[-2:]
        low1 = recent.iloc[last_two_lows[0]]['low']
        low2 = recent.iloc[last_two_lows[1]]['low']

        if abs(low1 - low2) / low1 < 0.02:  # Within 2%
            patterns.append(('DOUBLE BOTTOM', 'Bullish reversal pattern detected', 'success'))

    # Head and Shoulders (simplified)
    if len(highs_idx) >= 3:
        last_three_highs = highs_idx[-3:]
        h1 = recent.iloc[last_three_highs[0]]['high']
        h2 = recent.iloc[last_three_highs[1]]['high']
        h3 = recent.iloc[last_three_highs[2]]['high']

        if h2 > h1 and h2 > h3 and abs(h1 - h3) / h1 < 0.015:
            patterns.append(('HEAD & SHOULDERS', 'Strong bearish reversal', 'critical'))

    # Triangle patterns (convergence)
    if len(df) >= 20:
        recent_20 = df.tail(20)
        high_trend = np.polyfit(range(len(recent_20)), recent_20['high'].values, 1)[0]
        low_trend = np.polyfit(range(len(recent_20)), recent_20['low'].values, 1)[0]

        if abs(high_trend) < 0.001 and abs(low_trend) < 0.001:
            patterns.append(('SYMMETRICAL TRIANGLE', 'Consolidation - breakout imminent', 'info'))
        elif high_trend < 0 and low_trend > 0:
            patterns.append(('DESCENDING TRIANGLE', 'Bearish continuation likely', 'warning'))
        elif high_trend > 0 and low_trend < 0:
            patterns.append(('ASCENDING TRIANGLE', 'Bullish continuation likely', 'success'))

    return patterns

def find_support_resistance(df):
    """Find key support and resistance levels"""
    # Get swing highs and lows
    highs_idx = argrelextrema(df['high'].values, np.greater, order=5)[0]
    lows_idx = argrelextrema(df['low'].values, np.less, order=5)[0]

    resistance_levels = df.iloc[highs_idx]['high'].values
    support_levels = df.iloc[lows_idx]['low'].values

    # Cluster nearby levels
    def cluster_levels(levels, threshold=0.002):
        if len(levels) == 0:
            return []

        sorted_levels = np.sort(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < threshold:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]

        clusters.append(np.mean(current_cluster))
        return clusters

    resistance = cluster_levels(resistance_levels)
    support = cluster_levels(support_levels)

    return support, resistance

def calculate_fibonacci_levels(df):
    """Calculate Fibonacci retracement levels"""
    # Find recent swing high and low
    recent_50 = df.tail(50)

    swing_high = recent_50['high'].max()
    swing_low = recent_50['low'].min()

    diff = swing_high - swing_low

    fib_levels = {
        '0.0% (Low)': swing_low,
        '23.6%': swing_low + 0.236 * diff,
        '38.2%': swing_low + 0.382 * diff,
        '50.0%': swing_low + 0.5 * diff,
        '61.8%': swing_low + 0.618 * diff,
        '78.6%': swing_low + 0.786 * diff,
        '100% (High)': swing_high,
    }

    return fib_levels, swing_high, swing_low

def analyze_momentum(df):
    """Analyze momentum indicators"""
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signals = []

    # RSI
    rsi = latest['RSI']
    if rsi > 70:
        signals.append(('RSI Overbought', f'RSI at {rsi:.1f} - potential reversal', 'warning'))
    elif rsi < 30:
        signals.append(('RSI Oversold', f'RSI at {rsi:.1f} - potential bounce', 'success'))

    # MACD
    if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
        signals.append(('MACD Bullish Cross', 'Fresh bullish momentum', 'success'))
    elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
        signals.append(('MACD Bearish Cross', 'Fresh bearish momentum', 'warning'))

    # Stochastic
    if latest['Stoch_K'] > 80:
        signals.append(('Stochastic Overbought', f'Stoch at {latest["Stoch_K"]:.1f}', 'warning'))
    elif latest['Stoch_K'] < 20:
        signals.append(('Stochastic Oversold', f'Stoch at {latest["Stoch_K"]:.1f}', 'success'))

    # Bollinger Bands
    if latest['close'] > latest['BB_Upper']:
        signals.append(('Above BB Upper', 'Price extended - watch for reversal', 'warning'))
    elif latest['close'] < latest['BB_Lower']:
        signals.append(('Below BB Lower', 'Price oversold - bounce likely', 'success'))

    return signals

def multi_timeframe_analysis(symbol):
    """Analyze symbol across multiple timeframes"""
    timeframes = {
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
        'D1': mt5.TIMEFRAME_D1
    }

    mtf_analysis = {}

    for name, tf in timeframes.items():
        df = get_symbol_data(symbol, timeframe=tf, count=300)
        if df is not None:
            df = calculate_indicators(df)
            trend, score = detect_trend(df)
            latest = df.iloc[-1]

            mtf_analysis[name] = {
                'trend': trend,
                'trend_score': score,
                'rsi': latest['RSI'],
                'macd_signal': 'BULLISH' if latest['MACD'] > latest['MACD_Signal'] else 'BEARISH'
            }

    # Determine alignment
    if mtf_analysis:
        trends = [v['trend_score'] for v in mtf_analysis.values()]
        if all(t > 0 for t in trends):
            alignment = 'FULLY ALIGNED BULLISH'
        elif all(t < 0 for t in trends):
            alignment = 'FULLY ALIGNED BEARISH'
        else:
            alignment = 'MIXED - NO CLEAR DIRECTION'
    else:
        alignment = 'N/A'

    return mtf_analysis, alignment

def run():
    if not init_mt5():
        return

    print("="*80)
    print("GENERATING TECHNICAL ANALYSIS REPORT")
    print("="*80)

    # Get positions and watchlist
    positions = get_positions()
    position_symbols = list(set([p.symbol for p in positions])) if positions else []

    # Add major symbols to watchlist
    watchlist = ['GOLD', 'SILVER', 'EURUSD', 'GBPUSD', 'BTCUSD', 'US100Cash']
    all_symbols = list(set(position_symbols + watchlist))

    print(f"\nAnalyzing {len(all_symbols)} symbols...")

    analyses = {}

    for i, symbol in enumerate(all_symbols, 1):
        print(f"[{i}/{len(all_symbols)}] {symbol}...")

        # Get data
        df = get_symbol_data(symbol, count=500)
        if df is None:
            continue

        df = calculate_indicators(df)

        # Run all analyses
        trend, score = detect_trend(df)
        patterns = detect_chart_patterns(df)
        support, resistance = find_support_resistance(df)
        fib_levels, swing_high, swing_low = calculate_fibonacci_levels(df)
        momentum_signals = analyze_momentum(df)
        mtf, alignment = multi_timeframe_analysis(symbol)

        latest = df.iloc[-1]
        current_price = latest['close']

        # Find nearest levels
        nearest_support = [s for s in support if s < current_price]
        nearest_resistance = [r for r in resistance if r > current_price]

        nearest_support_val = max(nearest_support) if nearest_support else None
        nearest_resistance_val = min(nearest_resistance) if nearest_resistance else None

        analyses[symbol] = {
            'price': current_price,
            'trend': trend,
            'trend_score': score,
            'patterns': patterns,
            'support': nearest_support_val,
            'resistance': nearest_resistance_val,
            'fib_levels': fib_levels,
            'swing_high': swing_high,
            'swing_low': swing_low,
            'momentum_signals': momentum_signals,
            'mtf': mtf,
            'alignment': alignment,
            'rsi': latest['RSI'],
            'macd': latest['MACD'],
            'atr': latest['ATR'],
            'volatility': latest['Volatility'],
            'in_position': symbol in position_symbols
        }

    print("\nGenerating email report...")

    # Build HTML email
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
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 36px;
                font-weight: 700;
            }}
            .content {{
                padding: 40px;
            }}
            .symbol-card {{
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }}
            .symbol-card.in-position {{
                border-left: 5px solid #6366f1;
                background: #f8f9ff;
            }}
            .symbol-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 2px solid #f3f4f6;
            }}
            .symbol-name {{
                font-size: 28px;
                font-weight: 700;
                color: #1f2937;
            }}
            .price {{
                font-size: 24px;
                font-weight: 600;
                color: #6366f1;
            }}
            .badge {{
                display: inline-block;
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                margin-right: 8px;
            }}
            .badge.uptrend {{ background: #d1fae5; color: #065f46; }}
            .badge.downtrend {{ background: #fee2e2; color: #991b1b; }}
            .badge.ranging {{ background: #fef3c7; color: #92400e; }}
            .badge.in-position {{ background: #dbeafe; color: #1e40af; }}
            .grid-3 {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .info-box {{
                background: #f9fafb;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #6366f1;
            }}
            .info-box h4 {{
                margin: 0 0 12px 0;
                font-size: 14px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .info-box .value {{
                font-size: 20px;
                font-weight: 700;
                color: #1f2937;
            }}
            .pattern-alert {{
                padding: 15px 20px;
                border-radius: 8px;
                margin: 10px 0;
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .pattern-alert.success {{
                background: #d1fae5;
                border-left: 4px solid #10b981;
            }}
            .pattern-alert.warning {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
            }}
            .pattern-alert.critical {{
                background: #fee2e2;
                border-left: 4px solid #ef4444;
            }}
            .pattern-alert.info {{
                background: #dbeafe;
                border-left: 4px solid #3b82f6;
            }}
            .level-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            .level-table td {{
                padding: 12px;
                border-bottom: 1px solid #f3f4f6;
            }}
            .level-table td:first-child {{
                font-weight: 600;
                color: #6b7280;
                width: 40%;
            }}
            .level-table td:last-child {{
                text-align: right;
                font-weight: 600;
            }}
            .mtf-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            .mtf-card {{
                background: #f9fafb;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }}
            .mtf-card .tf-label {{
                font-size: 12px;
                color: #9ca3af;
                margin-bottom: 8px;
            }}
            .mtf-card .tf-trend {{
                font-size: 16px;
                font-weight: 700;
                margin: 5px 0;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: 700;
                color: #374151;
                margin: 25px 0 15px 0;
                padding-bottom: 8px;
                border-bottom: 2px solid #e5e7eb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>TECHNICAL ANALYSIS REPORT</h1>
                <div style="font-size: 16px; opacity: 0.95; margin-top: 10px;">
                    {datetime.now().strftime('%A, %B %d, %Y at %H:%M')}
                </div>
                <div style="font-size: 14px; opacity: 0.9; margin-top: 5px;">
                    Analyzing {len(all_symbols)} symbols | Patterns, Levels, Signals
                </div>
            </div>

            <div class="content">
"""

    # Generate cards for each symbol
    for symbol, data in analyses.items():
        card_class = 'in-position' if data['in_position'] else ''

        trend_class = 'uptrend' if data['trend_score'] > 0 else 'downtrend' if data['trend_score'] < 0 else 'ranging'

        html += f"""
                <div class="symbol-card {card_class}">
                    <div class="symbol-header">
                        <div>
                            <span class="symbol-name">{symbol}</span>
                            <div style="margin-top: 8px;">
                                <span class="badge {trend_class}">{data['trend']}</span>
                                {f'<span class="badge in-position">IN POSITION</span>' if data['in_position'] else ''}
                            </div>
                        </div>
                        <div class="price">${data['price']:.5f}</div>
                    </div>
"""

        # Multi-Timeframe Analysis
        if data['mtf']:
            html += f"""
                    <div class="section-title">Multi-Timeframe Analysis</div>
                    <div style="text-align: center; font-size: 16px; font-weight: 600; color: {'#10b981' if 'BULLISH' in data['alignment'] else '#ef4444' if 'BEARISH' in data['alignment'] else '#f59e0b'}; margin-bottom: 15px;">
                        {data['alignment']}
                    </div>
                    <div class="mtf-grid">
"""
            for tf, tfdata in data['mtf'].items():
                trend_color = '#10b981' if tfdata['trend_score'] > 0 else '#ef4444' if tfdata['trend_score'] < 0 else '#f59e0b'
                html += f"""
                        <div class="mtf-card">
                            <div class="tf-label">{tf} Timeframe</div>
                            <div class="tf-trend" style="color: {trend_color};">{tfdata['trend']}</div>
                            <div style="font-size: 13px; color: #6b7280; margin-top: 5px;">
                                RSI: {tfdata['rsi']:.1f} | {tfdata['macd_signal']}
                            </div>
                        </div>
"""
            html += "</div>"

        # Key Levels
        html += '<div class="section-title">Key Levels</div><div class="grid-3">'

        # Support/Resistance
        html += '<div class="info-box">'
        html += '<h4>Support & Resistance</h4>'
        if data['resistance']:
            dist_r = ((data['resistance'] - data['price']) / data['price']) * 100
            html += f'<div>R: <strong>{data["resistance"]:.5f}</strong> <span style="color: #ef4444;">(+{dist_r:.2f}%)</span></div>'
        if data['support']:
            dist_s = ((data['price'] - data['support']) / data['price']) * 100
            html += f'<div>S: <strong>{data["support"]:.5f}</strong> <span style="color: #10b981;">(-{dist_s:.2f}%)</span></div>'
        html += '</div>'

        # Swing Points
        html += '<div class="info-box">'
        html += '<h4>Recent Swing Points</h4>'
        html += f'<div>High: <strong>{data["swing_high"]:.5f}</strong></div>'
        html += f'<div>Low: <strong>{data["swing_low"]:.5f}</strong></div>'
        swing_range = ((data['swing_high'] - data['swing_low']) / data['swing_low']) * 100
        html += f'<div style="color: #6b7280; font-size: 13px; margin-top: 5px;">Range: {swing_range:.2f}%</div>'
        html += '</div>'

        # Volatility
        html += '<div class="info-box">'
        html += '<h4>Volatility Metrics</h4>'
        html += f'<div>ATR: <strong>{data["atr"]:.5f}</strong></div>'
        html += f'<div>Volatility: <strong>{data["volatility"]:.1f}%</strong></div>'
        html += '</div>'

        html += '</div>'

        # Fibonacci Levels
        html += '<div class="section-title">Fibonacci Retracement</div>'
        html += '<table class="level-table">'
        for level_name, level_value in data['fib_levels'].items():
            distance = ((level_value - data['price']) / data['price']) * 100
            color = '#10b981' if distance < 0 else '#ef4444'
            html += f'<tr><td>{level_name}</td><td style="color: {color};">{level_value:.5f} ({distance:+.2f}%)</td></tr>'
        html += '</table>'

        # Chart Patterns
        if data['patterns']:
            html += '<div class="section-title">Chart Patterns Detected</div>'
            for pattern_name, pattern_desc, severity in data['patterns']:
                html += f"""
                    <div class="pattern-alert {severity}">
                        <div>
                            <strong>{pattern_name}</strong>
                            <div style="font-size: 13px; margin-top: 4px;">{pattern_desc}</div>
                        </div>
                    </div>
"""

        # Momentum Signals
        if data['momentum_signals']:
            html += '<div class="section-title">Momentum Indicators</div>'
            for signal_name, signal_desc, severity in data['momentum_signals']:
                html += f"""
                    <div class="pattern-alert {severity}">
                        <div>
                            <strong>{signal_name}</strong>
                            <div style="font-size: 13px; margin-top: 4px;">{signal_desc}</div>
                        </div>
                    </div>
"""

        html += '</div>'  # Close symbol-card

    html += """
            </div>
        </div>
    </body>
    </html>
    """

    print("\nSending TA report to email...")
    if send_email("TECHNICAL ANALYSIS REPORT", html):
        print("[SUCCESS] TA report sent!")
    else:
        print("[FAILED] Email not sent")

    shutdown_mt5()
    print("\n[DONE]")

if __name__ == "__main__":
    run()
