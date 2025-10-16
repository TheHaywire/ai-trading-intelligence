"""
AI/ML TRADING INTELLIGENCE SYSTEM
Machine learning predictions, pattern recognition, and intelligent forecasting
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import argrelextrema
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import *
from core.mt5_service import init_mt5, get_positions, get_account_info, get_symbol_data
from core.analysis import calculate_indicators, detect_trend
from core.email_service import send_email
import MetaTrader5 as mt5


def prepare_ml_features(df):
    """Prepare features for ML models"""
    features = pd.DataFrame()

    # Price-based features
    features['returns'] = df['close'].pct_change()
    features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    features['price_momentum'] = df['close'] / df['close'].shift(10) - 1

    # Volatility features
    features['volatility'] = df['close'].pct_change().rolling(20).std()
    features['atr_normalized'] = df['ATR'] / df['close']

    # Trend features
    features['sma_distance'] = (df['close'] - df['SMA_50']) / df['SMA_50']
    features['ema_distance'] = (df['close'] - df['EMA_12']) / df['EMA_12']
    features['sma_slope'] = df['SMA_50'].pct_change(5)

    # Momentum indicators
    features['rsi'] = df['RSI']
    features['rsi_change'] = df['RSI'].diff()
    features['macd'] = df['MACD']
    features['macd_signal'] = df['MACD_Signal']
    features['macd_histogram'] = df['MACD'] - df['MACD_Signal']

    # Volume (if available)
    if 'tick_volume' in df.columns:
        features['volume'] = df['tick_volume']
        features['volume_sma'] = df['tick_volume'].rolling(20).mean()
        features['volume_ratio'] = df['tick_volume'] / features['volume_sma']

    # Bollinger Bands
    features['bb_width'] = (df['BB_Upper'] - df['BB_Lower']) / df['close']
    features['bb_position'] = (df['close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])

    # Stochastic
    features['stoch_k'] = df['Stoch_K']
    features['stoch_d'] = df['Stoch_D']

    # Higher timeframe context
    features['high_5'] = df['high'].rolling(5).max()
    features['low_5'] = df['low'].rolling(5).min()
    features['range_5'] = features['high_5'] - features['low_5']

    # Drop NaN
    features = features.fillna(method='ffill').fillna(0)

    return features


def predict_direction_ml(df, symbol):
    """Use ML to predict price direction"""
    try:
        # Prepare features
        features = prepare_ml_features(df)

        # Create target (1 if price goes up in next 5 bars, 0 otherwise)
        target = (df['close'].shift(-5) > df['close']).astype(int)

        # Remove last 5 rows (no target available)
        features = features[:-5]
        target = target[:-5]

        # Split into train/test
        train_size = int(len(features) * 0.8)
        X_train = features[:train_size]
        y_train = target[:train_size]
        X_test = features[train_size:]
        y_test = target[train_size:]

        # Train model
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)

        # Get accuracy
        train_accuracy = model.score(X_train, y_train)
        test_accuracy = model.score(X_test, y_test)

        # Predict current direction
        current_features = features.iloc[-1:].fillna(0)
        prediction_proba = model.predict_proba(current_features)[0]

        up_probability = prediction_proba[1] * 100
        down_probability = prediction_proba[0] * 100

        # Feature importance
        feature_importance = dict(zip(features.columns, model.feature_importances_))
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            'symbol': symbol,
            'prediction': 'UP' if up_probability > down_probability else 'DOWN',
            'up_probability': up_probability,
            'down_probability': down_probability,
            'confidence': max(up_probability, down_probability),
            'train_accuracy': train_accuracy * 100,
            'test_accuracy': test_accuracy * 100,
            'top_features': top_features,
            'model_quality': 'EXCELLENT' if test_accuracy > 0.6 else 'GOOD' if test_accuracy > 0.55 else 'FAIR'
        }

    except Exception as e:
        return None


def predict_price_target_ml(df, symbol):
    """Use ML to predict price target"""
    try:
        # Prepare features
        features = prepare_ml_features(df)

        # Create target (price change in next 5 bars)
        target = df['close'].shift(-5) - df['close']

        # Remove last 5 rows
        features = features[:-5]
        target = target[:-5]

        # Split
        train_size = int(len(features) * 0.8)
        X_train = features[:train_size]
        y_train = target[:train_size]
        X_test = features[train_size:]
        y_test = target[train_size:]

        # Train model
        model = GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X_train, y_train)

        # Get R² score
        train_r2 = model.score(X_train, y_train)
        test_r2 = model.score(X_test, y_test)

        # Predict current price change
        current_features = features.iloc[-1:].fillna(0)
        predicted_change = model.predict(current_features)[0]

        current_price = df['close'].iloc[-1]
        predicted_price = current_price + predicted_change
        predicted_change_pct = (predicted_change / current_price) * 100

        return {
            'symbol': symbol,
            'current_price': current_price,
            'predicted_price': predicted_price,
            'predicted_change': predicted_change,
            'predicted_change_pct': predicted_change_pct,
            'train_r2': train_r2,
            'test_r2': test_r2,
            'model_quality': 'EXCELLENT' if test_r2 > 0.3 else 'GOOD' if test_r2 > 0.15 else 'FAIR'
        }

    except Exception as e:
        return None


def detect_complex_patterns_ml(df, symbol):
    """Use statistical analysis to detect complex patterns"""
    patterns = []

    latest = df.iloc[-1]
    current_price = latest['close']

    # Pattern 1: Mean Reversion Setup
    z_score = (current_price - df['close'].rolling(50).mean().iloc[-1]) / df['close'].rolling(50).std().iloc[-1]

    if z_score < -2:
        patterns.append({
            'pattern': 'Mean Reversion - Oversold',
            'type': 'BULLISH',
            'strength': min(abs(z_score) * 20, 100),
            'description': f'Price {abs(z_score):.1f} std dev below 50-period mean'
        })
    elif z_score > 2:
        patterns.append({
            'pattern': 'Mean Reversion - Overbought',
            'type': 'BEARISH',
            'strength': min(abs(z_score) * 20, 100),
            'description': f'Price {abs(z_score):.1f} std dev above 50-period mean'
        })

    # Pattern 2: Momentum Breakout
    recent_volatility = df['close'].pct_change().tail(20).std()
    avg_volatility = df['close'].pct_change().std()

    if recent_volatility > avg_volatility * 1.5:
        price_change = (current_price - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
        if abs(price_change) > 2:
            patterns.append({
                'pattern': 'Momentum Breakout',
                'type': 'BULLISH' if price_change > 0 else 'BEARISH',
                'strength': min(abs(price_change) * 10, 100),
                'description': f'High volatility breakout ({abs(price_change):.1f}% move)'
            })

    # Pattern 3: Trend Exhaustion
    recent_returns = df['close'].pct_change().tail(20)
    if len(recent_returns) >= 20:
        consecutive_up = 0
        consecutive_down = 0

        for ret in recent_returns:
            if ret > 0:
                consecutive_up += 1
                consecutive_down = 0
            elif ret < 0:
                consecutive_down += 1
                consecutive_up = 0

        if consecutive_up >= 8:
            patterns.append({
                'pattern': 'Trend Exhaustion',
                'type': 'BEARISH',
                'strength': 70,
                'description': f'{consecutive_up} consecutive up bars - potential reversal'
            })
        elif consecutive_down >= 8:
            patterns.append({
                'pattern': 'Trend Exhaustion',
                'type': 'BULLISH',
                'strength': 70,
                'description': f'{consecutive_down} consecutive down bars - potential reversal'
            })

    # Pattern 4: Volume Spike (if available)
    if 'tick_volume' in df.columns:
        avg_volume = df['tick_volume'].rolling(50).mean().iloc[-1]
        current_volume = df['tick_volume'].iloc[-1]

        if current_volume > avg_volume * 2:
            price_change = (current_price - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
            patterns.append({
                'pattern': 'Volume Spike',
                'type': 'BULLISH' if price_change > 0 else 'BEARISH',
                'strength': min((current_volume / avg_volume) * 25, 100),
                'description': f'Volume {(current_volume/avg_volume):.1f}x average'
            })

    return patterns


def calculate_win_probability(position, df):
    """Calculate win probability for a position using ML"""
    try:
        position_type = 'LONG' if position.type == 0 else 'SHORT'

        # Get current technical state
        latest = df.iloc[-1]

        # Calculate factors
        factors = {}

        # Trend alignment
        sma_50 = latest['SMA_50']
        sma_200 = latest['SMA_200']
        price = latest['close']

        if position_type == 'LONG':
            factors['trend_alignment'] = 1 if (price > sma_50 and sma_50 > sma_200) else 0
        else:
            factors['trend_alignment'] = 1 if (price < sma_50 and sma_50 < sma_200) else 0

        # RSI position
        rsi = latest['RSI']
        if position_type == 'LONG':
            factors['rsi_favorable'] = 1 if rsi < 60 else 0
        else:
            factors['rsi_favorable'] = 1 if rsi > 40 else 0

        # MACD alignment
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']

        if position_type == 'LONG':
            factors['macd_favorable'] = 1 if macd > macd_signal else 0
        else:
            factors['macd_favorable'] = 1 if macd < macd_signal else 0

        # Recent momentum
        momentum = (price - df['close'].iloc[-10]) / df['close'].iloc[-10] * 100

        if position_type == 'LONG':
            factors['momentum_favorable'] = 1 if momentum > 0 else 0
        else:
            factors['momentum_favorable'] = 1 if momentum < 0 else 0

        # Calculate weighted probability
        weights = {
            'trend_alignment': 0.35,
            'rsi_favorable': 0.20,
            'macd_favorable': 0.25,
            'momentum_favorable': 0.20
        }

        win_probability = sum(factors[k] * weights[k] for k in factors) * 100

        # Adjust based on current P&L
        position_value = position.volume * position.price_current
        profit_pct = (position.profit / position_value) * 100

        # If already profitable, boost probability
        if position.profit > 0:
            win_probability = min(win_probability * 1.2, 95)

        return {
            'win_probability': win_probability,
            'factors': factors,
            'recommendation': 'HOLD' if win_probability > 50 else 'CLOSE',
            'confidence': 'HIGH' if win_probability > 70 or win_probability < 30 else 'MEDIUM'
        }

    except Exception as e:
        return None


def score_trade_quality(position, df):
    """Score the quality of a trade setup"""
    try:
        position_type = 'LONG' if position.type == 0 else 'SHORT'

        latest = df.iloc[-1]
        score = 0
        reasons = []

        # Factor 1: Trend alignment (30 points)
        trend, trend_score = detect_trend(df)
        if position_type == 'LONG' and trend_score > 5:
            score += 30
            reasons.append(f"Strong uptrend ({trend})")
        elif position_type == 'SHORT' and trend_score < -5:
            score += 30
            reasons.append(f"Strong downtrend ({trend})")
        elif position_type == 'LONG' and trend_score > 0:
            score += 15
            reasons.append(f"Weak uptrend ({trend})")
        elif position_type == 'SHORT' and trend_score < 0:
            score += 15
            reasons.append(f"Weak downtrend ({trend})")
        else:
            reasons.append(f"Against trend ({trend})")

        # Factor 2: Entry timing (25 points)
        rsi = latest['RSI']
        if position_type == 'LONG' and 40 < rsi < 60:
            score += 25
            reasons.append(f"Good entry RSI ({rsi:.1f})")
        elif position_type == 'SHORT' and 40 < rsi < 60:
            score += 25
            reasons.append(f"Good entry RSI ({rsi:.1f})")
        elif position_type == 'LONG' and rsi < 40:
            score += 15
            reasons.append(f"Oversold entry ({rsi:.1f})")
        elif position_type == 'SHORT' and rsi > 60:
            score += 15
            reasons.append(f"Overbought entry ({rsi:.1f})")

        # Factor 3: Momentum (20 points)
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']

        if position_type == 'LONG' and macd > macd_signal:
            score += 20
            reasons.append("Bullish MACD")
        elif position_type == 'SHORT' and macd < macd_signal:
            score += 20
            reasons.append("Bearish MACD")

        # Factor 4: Volatility (15 points)
        atr_pct = (latest['ATR'] / latest['close']) * 100
        if 1 < atr_pct < 3:
            score += 15
            reasons.append(f"Healthy volatility ({atr_pct:.2f}%)")
        elif atr_pct < 1:
            score += 8
            reasons.append(f"Low volatility ({atr_pct:.2f}%)")

        # Factor 5: Risk/Reward (10 points)
        profit_pct = (position.profit / (position.volume * position.price_current)) * 100
        if profit_pct > 2:
            score += 10
            reasons.append(f"Strong profit ({profit_pct:.1f}%)")
        elif profit_pct > 0:
            score += 5
            reasons.append(f"Small profit ({profit_pct:.1f}%)")

        # Quality rating
        if score >= 80:
            quality = "EXCELLENT"
        elif score >= 60:
            quality = "GOOD"
        elif score >= 40:
            quality = "FAIR"
        else:
            quality = "POOR"

        return {
            'score': score,
            'quality': quality,
            'reasons': reasons
        }

    except Exception as e:
        return None


def analyze_positions_with_ai():
    """Analyze all positions with AI/ML"""
    positions = get_positions()

    if not positions:
        return []

    results = []

    print("Analyzing positions with AI/ML...")

    for pos in positions:
        df = get_symbol_data(pos.symbol, count=500)
        if df is None:
            continue

        df = calculate_indicators(df)

        # ML Direction prediction
        direction_pred = predict_direction_ml(df, pos.symbol)

        # ML Price target
        price_pred = predict_price_target_ml(df, pos.symbol)

        # Win probability
        win_prob = calculate_win_probability(pos, df)

        # Trade quality
        quality = score_trade_quality(pos, df)

        # Pattern detection
        patterns = detect_complex_patterns_ml(df, pos.symbol)

        results.append({
            'symbol': pos.symbol,
            'type': 'LONG' if pos.type == 0 else 'SHORT',
            'profit': pos.profit,
            'direction_prediction': direction_pred,
            'price_prediction': price_pred,
            'win_probability': win_prob,
            'trade_quality': quality,
            'patterns': patterns
        })

    return results


def generate_ai_html_report(ai_analysis, account):
    """Generate beautiful HTML report with AI analysis"""

    # Position Analysis
    positions_html = ""
    for analysis in ai_analysis:
        profit_color = "#10b981" if analysis['profit'] > 0 else "#ef4444"

        # Direction prediction
        dir_pred = analysis['direction_prediction']
        dir_color = "#10b981" if dir_pred and dir_pred['prediction'] == 'UP' else "#ef4444"

        # Win probability
        win_prob = analysis['win_probability']
        win_color = "#10b981" if win_prob and win_prob['win_probability'] > 50 else "#ef4444"

        # Trade quality
        quality = analysis['trade_quality']
        quality_colors = {
            'EXCELLENT': '#10b981',
            'GOOD': '#3b82f6',
            'FAIR': '#fbbf24',
            'POOR': '#ef4444'
        }
        quality_color = quality_colors.get(quality['quality'] if quality else 'FAIR', '#fbbf24')

        # Patterns
        patterns_html = ""
        if analysis['patterns']:
            for pattern in analysis['patterns'][:2]:
                pat_color = "#10b981" if pattern['type'] == 'BULLISH' else "#ef4444"
                patterns_html += f'<span style="color: {pat_color}; font-size: 11px;">• {pattern["pattern"]}</span><br>'
        else:
            patterns_html = '<span style="color: #a0aec0; font-size: 11px;">No patterns detected</span>'

        positions_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <strong>{analysis['symbol']}</strong><br>
                <span style="font-size: 11px; color: #a0aec0;">{analysis['type']}</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; color: {profit_color}; font-weight: bold;">
                ${analysis['profit']:+,.2f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <span style="color: {dir_color}; font-weight: bold;">{dir_pred['prediction'] if dir_pred else 'N/A'}</span><br>
                <span style="font-size: 11px; color: #a0aec0;">{dir_pred['confidence']:.1f}% conf.</span> if dir_pred else ''
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <span style="color: {win_color}; font-weight: bold;">{win_prob['win_probability']:.1f}%</span><br>
                <span style="font-size: 11px; color: #a0aec0;">{win_prob['recommendation'] if win_prob else 'N/A'}</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748;">
                <span style="color: {quality_color}; font-weight: bold;">{quality['quality'] if quality else 'N/A'}</span><br>
                <span style="font-size: 11px; color: #a0aec0;">{quality['score']}/100</span> if quality else ''
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2d3748; font-size: 11px;">
                {patterns_html}
            </td>
        </tr>
        """

    # Summary stats
    total_positions = len(ai_analysis)
    high_win_prob = len([a for a in ai_analysis if a['win_probability'] and a['win_probability']['win_probability'] > 60])
    excellent_quality = len([a for a in ai_analysis if a['trade_quality'] and a['trade_quality']['quality'] == 'EXCELLENT'])
    poor_quality = len([a for a in ai_analysis if a['trade_quality'] and a['trade_quality']['quality'] == 'POOR'])

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
                <h1>🤖 AI/ML TRADING INTELLIGENCE</h1>
                <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>

            <div class="content">
                <!-- KPI Dashboard -->
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">Total Positions</div>
                        <div class="kpi-value">{total_positions}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">High Win Probability</div>
                        <div class="kpi-value" style="color: #10b981;">{high_win_prob}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Excellent Quality</div>
                        <div class="kpi-value" style="color: #10b981;">{excellent_quality}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Poor Quality</div>
                        <div class="kpi-value" style="color: #ef4444;">{poor_quality}</div>
                    </div>
                </div>

                <!-- AI Position Analysis -->
                <div class="section">
                    <div class="section-title">🤖 AI-POWERED POSITION ANALYSIS</div>
                    <table>
                        <tr>
                            <th>Symbol</th>
                            <th>P&L</th>
                            <th>ML Prediction</th>
                            <th>Win Probability</th>
                            <th>Trade Quality</th>
                            <th>Patterns</th>
                        </tr>
                        {positions_html}
                    </table>
                </div>

                <!-- AI Insights -->
                <div class="section">
                    <div class="section-title">💡 KEY AI INSIGHTS</div>
                    <div style="padding: 16px; background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; border-radius: 8px; margin-bottom: 12px;">
                        <strong style="color: #ef4444;">⚠️ {poor_quality} positions have POOR trade quality</strong><br>
                        <span style="color: #e2e8f0;">These positions are against trend or have unfavorable technical setup. Consider closing.</span>
                    </div>

                    <div style="padding: 16px; background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; border-radius: 8px; margin-bottom: 12px;">
                        <strong style="color: #10b981;">✓ {high_win_prob} positions have >60% win probability</strong><br>
                        <span style="color: #e2e8f0;">These positions have favorable technical conditions. Consider letting them run.</span>
                    </div>

                    <div style="padding: 16px; background: rgba(59, 130, 246, 0.1); border-left: 4px solid #3b82f6; border-radius: 8px;">
                        <strong style="color: #3b82f6;">🎯 ML models are analyzing {total_positions} positions</strong><br>
                        <span style="color: #e2e8f0;">Using Random Forest & Gradient Boosting for predictions. Accuracy varies by market condition.</span>
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
    print("AI/ML TRADING INTELLIGENCE SYSTEM")
    print("="*80)
    print()

    if not init_mt5():
        print("[ERROR] Failed to initialize MT5")
        return

    account = get_account_info()

    print("[1/3] Running AI/ML analysis on all positions...")
    ai_analysis = analyze_positions_with_ai()

    if not ai_analysis:
        print("[WARNING] No positions to analyze")
        return

    print(f"[2/3] Generating AI intelligence report...")
    html_report = generate_ai_html_report(ai_analysis, account)

    print("[3/3] Sending AI intelligence report to email...")
    subject = f"🤖 AI/ML Intelligence - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    if send_email(subject, html_report):
        print("[SUCCESS] AI intelligence report sent!")
    else:
        print("[ERROR] Failed to send email")

    # Print summary
    print("\n" + "="*80)
    print("AI ANALYSIS SUMMARY")
    print("="*80)

    for analysis in ai_analysis:
        print(f"\n{analysis['symbol']} ({analysis['type']}) - P&L: ${analysis['profit']:+,.2f}")

        if analysis['direction_prediction']:
            dir_pred = analysis['direction_prediction']
            print(f"  ML Prediction: {dir_pred['prediction']} ({dir_pred['confidence']:.1f}% confidence)")

        if analysis['win_probability']:
            win_prob = analysis['win_probability']
            print(f"  Win Probability: {win_prob['win_probability']:.1f}% - {win_prob['recommendation']}")

        if analysis['trade_quality']:
            quality = analysis['trade_quality']
            print(f"  Trade Quality: {quality['quality']} ({quality['score']}/100)")
            print(f"    Reasons: {', '.join(quality['reasons'][:3])}")

    print("\n[DONE]\n")


if __name__ == "__main__":
    run()
