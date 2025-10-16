"""
SYMBOL DECISION CARDS
One card per symbol with deep analysis and clear TRADE/NO TRADE decision
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
from core.realtime_intelligence import get_realtime_intelligence, finnhub, gemini_ai
import MetaTrader5 as mt5


def get_multi_timeframe_context(symbol):
    """Get multi-timeframe analysis for context"""
    timeframes = {
        'M15': (mt5.TIMEFRAME_M15, '15min'),
        'H1': (mt5.TIMEFRAME_H1, '1H'),
        'H4': (mt5.TIMEFRAME_H4, '4H'),
        'D1': (mt5.TIMEFRAME_D1, 'Daily')
    }

    mtf_context = {}
    for name, (tf, display) in timeframes.items():
        df = get_symbol_data(symbol, timeframe=tf, count=100)
        if df is not None:
            df = calculate_indicators(df)
            trend, trend_score = detect_trend(df)
            latest = df.iloc[-1]

            mtf_context[name] = {
                'display': display,
                'trend': trend,
                'trend_score': trend_score,
                'rsi': latest['RSI'],
                'macd_signal': 'BULLISH' if latest['MACD'] > latest['MACD_Signal'] else 'BEARISH',
                'price': latest['close']
            }

    # Determine overall alignment
    if mtf_context:
        trend_scores = [v['trend_score'] for v in mtf_context.values()]
        if all(s > 3 for s in trend_scores):
            alignment = "FULLY ALIGNED BULLISH 🚀"
            alignment_color = "#10b981"
        elif all(s < -3 for s in trend_scores):
            alignment = "FULLY ALIGNED BEARISH 🔻"
            alignment_color = "#ef4444"
        elif sum(1 for s in trend_scores if s > 0) >= 3:
            alignment = "MOSTLY BULLISH ⬆️"
            alignment_color = "#3b82f6"
        elif sum(1 for s in trend_scores if s < 0) >= 3:
            alignment = "MOSTLY BEARISH ⬇️"
            alignment_color = "#f59e0b"
        else:
            alignment = "MIXED - NO CLEAR DIRECTION ↔️"
            alignment_color = "#a0aec0"

        mtf_context['alignment'] = alignment
        mtf_context['alignment_color'] = alignment_color

    return mtf_context


def get_historical_performance(symbol):
    """Get historical performance context"""
    df_weekly = get_symbol_data(symbol, timeframe=mt5.TIMEFRAME_H1, count=500)
    if df_weekly is None:
        return None

    current_price = df_weekly['close'].iloc[-1]

    # 7 days ago (168 hours)
    if len(df_weekly) > 168:
        price_7d = df_weekly['close'].iloc[-168]
        change_7d = ((current_price - price_7d) / price_7d) * 100
    else:
        change_7d = 0

    # 30 days ago (~720 hours)
    if len(df_weekly) > 400:
        price_30d = df_weekly['close'].iloc[-400]
        change_30d = ((current_price - price_30d) / price_30d) * 100
    else:
        change_30d = 0

    # High/Low for context
    high_period = df_weekly['high'].max()
    low_period = df_weekly['low'].min()
    distance_from_high = ((current_price - high_period) / high_period) * 100
    distance_from_low = ((current_price - low_period) / low_period) * 100

    return {
        'change_7d': change_7d,
        'change_30d': change_30d,
        'high_period': high_period,
        'low_period': low_period,
        'distance_from_high': distance_from_high,
        'distance_from_low': distance_from_low,
        'current_price': current_price
    }


def analyze_symbol_decision(symbol, position=None):
    """
    Deep analysis for a symbol - TRADE or NO TRADE with detailed reasoning
    """
    df = get_symbol_data(symbol, count=200)
    if df is None:
        return None

    df = calculate_indicators(df)
    trend, trend_score = detect_trend(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Get multi-timeframe context
    mtf_context = get_multi_timeframe_context(symbol)

    # Get historical performance
    historical = get_historical_performance(symbol)

    # Current metrics
    price = latest['close']
    rsi = latest['RSI']
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']
    stoch_k = latest['Stoch_K']
    stoch_d = latest['Stoch_D']
    sma_20 = latest['SMA_20']
    sma_50 = latest['SMA_50']
    sma_200 = latest['SMA_200']
    atr = latest['ATR']
    bb_upper = latest['BB_Upper']
    bb_lower = latest['BB_Lower']

    # Calculate score factors
    factors = {
        'trend_quality': 0,
        'momentum': 0,
        'entry_timing': 0,
        'risk_reward': 0,
        'market_structure': 0
    }

    reasons = []
    warnings = []

    # TREND QUALITY (40 points)
    if trend_score > 7:
        factors['trend_quality'] = 40
        reasons.append(f"✓ STRONG UPTREND - Price above SMA50 > SMA200")
    elif trend_score > 3:
        factors['trend_quality'] = 25
        reasons.append(f"✓ Uptrend - Price above SMA50")
    elif trend_score < -7:
        factors['trend_quality'] = 40
        reasons.append(f"✓ STRONG DOWNTREND - Price below SMA50 < SMA200")
    elif trend_score < -3:
        factors['trend_quality'] = 25
        reasons.append(f"✓ Downtrend - Price below SMA50")
    else:
        factors['trend_quality'] = 0
        warnings.append(f"✗ NO CLEAR TREND - Choppy, avoid")

    # MOMENTUM (25 points)
    if macd > macd_signal:
        if prev['MACD'] <= prev['MACD_Signal']:
            factors['momentum'] = 25
            reasons.append(f"✓ MACD BULLISH CROSSOVER - Fresh momentum")
        else:
            factors['momentum'] = 15
            reasons.append(f"✓ MACD Bullish - Momentum positive")
    elif macd < macd_signal:
        if prev['MACD'] >= prev['MACD_Signal']:
            factors['momentum'] = 25
            reasons.append(f"✓ MACD BEARISH CROSSOVER - Fresh momentum")
        else:
            factors['momentum'] = 15
            reasons.append(f"✓ MACD Bearish - Momentum negative")

    # ENTRY TIMING (20 points)
    if 30 < rsi < 70:
        factors['entry_timing'] = 20
        reasons.append(f"✓ RSI HEALTHY ({rsi:.0f}) - Not overbought/oversold")
    elif rsi < 30:
        if trend_score > 5:
            factors['entry_timing'] = 15
            reasons.append(f"✓ RSI OVERSOLD ({rsi:.0f}) in uptrend - Pullback entry")
        else:
            warnings.append(f"✗ RSI OVERSOLD ({rsi:.0f}) - Could go lower")
    elif rsi > 70:
        if trend_score < -5:
            factors['entry_timing'] = 15
            reasons.append(f"✓ RSI OVERBOUGHT ({rsi:.0f}) in downtrend - Rejection entry")
        else:
            warnings.append(f"✗ RSI OVERBOUGHT ({rsi:.0f}) - Could reverse")

    # RISK/REWARD (10 points)
    atr_pct = (atr / price) * 100
    if 0.5 < atr_pct < 3:
        factors['risk_reward'] = 10
        reasons.append(f"✓ GOOD VOLATILITY ({atr_pct:.2f}%) - Manageable risk")
    elif atr_pct < 0.5:
        warnings.append(f"✗ LOW VOLATILITY ({atr_pct:.2f}%) - Limited profit potential")
    else:
        warnings.append(f"✗ HIGH VOLATILITY ({atr_pct:.2f}%) - Risky")

    # MARKET STRUCTURE (5 points)
    if (stoch_k > stoch_d and stoch_k < 80) or (stoch_k < stoch_d and stoch_k > 20):
        factors['market_structure'] = 5
        reasons.append(f"✓ Stochastic aligned")

    # CALCULATE TOTAL SCORE
    total_score = sum(factors.values())

    # MAKE DECISION
    if total_score >= 70:
        decision = "STRONG BUY" if trend_score > 0 else "STRONG SELL"
        decision_color = "#10b981"
        confidence = "VERY HIGH"
    elif total_score >= 50:
        decision = "BUY" if trend_score > 0 else "SELL"
        decision_color = "#3b82f6"
        confidence = "HIGH"
    elif total_score >= 30:
        decision = "MAYBE" if trend_score > 0 else "MAYBE"
        decision_color = "#fbbf24"
        confidence = "MEDIUM"
    else:
        decision = "DON'T TRADE"
        decision_color = "#ef4444"
        confidence = "LOW"

    # If position exists, add position-specific analysis
    position_analysis = None
    if position:
        position_type = 'LONG' if position.type == 0 else 'SHORT'
        profit_pct = (position.profit / (position.volume * position.price_current)) * 100

        # Check if position aligns with current analysis
        position_correct = False
        if position_type == 'LONG' and trend_score > 0:
            position_correct = True
        elif position_type == 'SHORT' and trend_score < 0:
            position_correct = True

        position_action = ""
        if position.profit < -5000:
            position_action = "🚨 CLOSE NOW - Large loss"
        elif position.profit > 5000:
            position_action = "💰 TAKE PROFIT - Lock in gains"
        elif not position_correct:
            position_action = "⚠️ CLOSE - Against trend"
        elif profit_pct < -5:
            position_action = "⚠️ CONSIDER CLOSING - Down >5%"
        else:
            position_action = "✓ HOLD - Position aligns"

        position_analysis = {
            'type': position_type,
            'profit': position.profit,
            'profit_pct': profit_pct,
            'correct_direction': position_correct,
            'action': position_action,
            'entry': position.price_open,
            'current': position.price_current
        }

    # Determine direction for new trade
    if decision in ["STRONG BUY", "BUY"]:
        trade_direction = "LONG"
        entry_price = price
        stop_loss = price - (atr * 2.0)
        take_profit = price + (atr * 3.0)
    elif decision in ["STRONG SELL", "SELL"]:
        trade_direction = "SHORT"
        entry_price = price
        stop_loss = price + (atr * 2.0)
        take_profit = price - (atr * 3.0)
    else:
        trade_direction = "NO TRADE"
        entry_price = None
        stop_loss = None
        take_profit = None

    # Get AI-powered real-time intelligence (only for tradeable symbols)
    ai_intelligence = None
    if decision != "DON'T TRADE" and gemini_ai.can_make_request():
        try:
            tech_data = {
                'price': price,
                'trend': trend,
                'trend_score': trend_score,
                'rsi': rsi,
                'macd': macd,
                'macd_signal': macd_signal,
                'score': total_score
            }

            # Get news
            news = finnhub.get_news("forex" if "USD" in symbol or "EUR" in symbol or "GBP" in symbol else "general", count=3)

            # Get AI analysis
            ai_analysis = gemini_ai.analyze_market_setup(symbol, tech_data, news)

            ai_intelligence = {
                'verdict': ai_analysis.get('ai_verdict', 'NEUTRAL'),
                'confidence': ai_analysis.get('ai_confidence', 0),
                'reasoning': ai_analysis.get('ai_reasoning', 'No analysis available'),
                'risk': ai_analysis.get('ai_risk', 'Unknown'),
                'news_count': len(news),
                'top_headline': news[0].get('headline', 'No news') if news else 'No news'
            }
        except Exception as e:
            print(f"[AI Intelligence Error] {symbol}: {e}")
            ai_intelligence = None

    return {
        'symbol': symbol,
        'decision': decision,
        'decision_color': decision_color,
        'confidence': confidence,
        'score': total_score,
        'trade_direction': trade_direction,
        'current_price': price,
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'trend': trend,
        'trend_score': trend_score,
        'rsi': rsi,
        'macd': macd,
        'macd_signal': macd_signal,
        'atr_pct': atr_pct,
        'reasons': reasons,
        'warnings': warnings,
        'factors': factors,
        'position_analysis': position_analysis,
        'mtf_context': mtf_context,
        'historical': historical,
        'ai_intelligence': ai_intelligence
    }


def generate_mtf_html(analysis):
    """Generate multi-timeframe context HTML"""
    mtf = analysis.get('mtf_context')
    if not mtf or not isinstance(mtf, dict):
        return ""

    # Check if we have timeframe data
    has_data = any(k in mtf for k in ['M15', 'H1', 'H4', 'D1'])
    if not has_data:
        return ""

    timeframes_html = ""
    for tf_key in ['M15', 'H1', 'H4', 'D1']:
        if tf_key in mtf:
            tf_data = mtf[tf_key]
            trend_color = "#10b981" if tf_data['trend_score'] > 0 else "#ef4444"
            timeframes_html += f"""
            <div style="background: rgba(45, 55, 72, 0.5); padding: 10px; border-radius: 6px;">
                <div style="color: #a0aec0; font-size: 10px; margin-bottom: 4px;">{tf_data['display']}</div>
                <div style="color: {trend_color}; font-weight: bold; font-size: 12px;">{tf_data['trend']}</div>
                <div style="color: #a0aec0; font-size: 11px;">RSI: {tf_data['rsi']:.0f}</div>
            </div>
            """

    alignment_color = mtf.get('alignment_color', '#a0aec0')
    alignment = mtf.get('alignment', 'N/A')

    return f"""
    <div style="background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 8px; padding: 16px; margin-bottom: 16px;">
        <div style="color: #3b82f6; font-size: 14px; font-weight: bold; margin-bottom: 12px;">📊 MULTI-TIMEFRAME ANALYSIS</div>
        <div style="background: rgba(45, 55, 72, 0.3); padding: 10px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid {alignment_color};">
            <strong style="color: {alignment_color};">{alignment}</strong>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 8px;">
            {timeframes_html}
        </div>
    </div>
    """


def generate_historical_html(analysis):
    """Generate historical performance HTML"""
    hist = analysis.get('historical')
    if not hist or not isinstance(hist, dict):
        return ""

    change_7d = hist.get('change_7d', 0)
    change_30d = hist.get('change_30d', 0)
    dist_high = hist.get('distance_from_high', 0)
    dist_low = hist.get('distance_from_low', 0)

    color_7d = "#10b981" if change_7d > 0 else "#ef4444"
    color_30d = "#10b981" if change_30d > 0 else "#ef4444"

    return f"""
    <div style="background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 8px; padding: 16px; margin-bottom: 8px;">
        <div style="color: #f59e0b; font-size: 14px; font-weight: bold; margin-bottom: 12px;">📈 HISTORICAL PERFORMANCE</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;">
            <div style="background: rgba(45, 55, 72, 0.5); padding: 10px; border-radius: 6px;">
                <div style="color: #a0aec0; font-size: 10px; margin-bottom: 4px;">7 DAYS</div>
                <div style="color: {color_7d}; font-weight: bold; font-size: 16px;">{change_7d:+.2f}%</div>
            </div>
            <div style="background: rgba(45, 55, 72, 0.5); padding: 10px; border-radius: 6px;">
                <div style="color: #a0aec0; font-size: 10px; margin-bottom: 4px;">30 DAYS</div>
                <div style="color: {color_30d}; font-weight: bold; font-size: 16px;">{change_30d:+.2f}%</div>
            </div>
            <div style="background: rgba(45, 55, 72, 0.5); padding: 10px; border-radius: 6px;">
                <div style="color: #a0aec0; font-size: 10px; margin-bottom: 4px;">FROM HIGH</div>
                <div style="color: #ef4444; font-weight: bold; font-size: 16px;">{dist_high:.2f}%</div>
            </div>
            <div style="background: rgba(45, 55, 72, 0.5); padding: 10px; border-radius: 6px;">
                <div style="color: #a0aec0; font-size: 10px; margin-bottom: 4px;">FROM LOW</div>
                <div style="color: #10b981; font-weight: bold; font-size: 16px;">{dist_low:+.2f}%</div>
            </div>
        </div>
    </div>
    """


def generate_ai_intelligence_html(analysis):
    """Generate AI-powered intelligence HTML"""
    ai = analysis.get('ai_intelligence')
    if not ai or not isinstance(ai, dict):
        return ""

    verdict = ai.get('verdict', 'NEUTRAL')
    confidence = ai.get('confidence', 0)
    reasoning = ai.get('reasoning', 'No analysis available')
    risk = ai.get('ai_risk', 'Unknown')
    headline = ai.get('top_headline', 'No news')

    # Verdict color
    verdict_colors = {
        'BUY': '#10b981',
        'SELL': '#ef4444',
        'HOLD': '#fbbf24',
        'NEUTRAL': '#a0aec0'
    }
    verdict_color = verdict_colors.get(verdict, '#a0aec0')

    # Confidence bar color
    if confidence >= 70:
        conf_color = "#10b981"
    elif confidence >= 40:
        conf_color = "#fbbf24"
    else:
        conf_color = "#ef4444"

    return f"""
    <div style="background: linear-gradient(135deg, rgba(147, 51, 234, 0.1) 0%, rgba(79, 70, 229, 0.1) 100%); border: 2px solid rgba(147, 51, 234, 0.3); border-radius: 8px; padding: 16px; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 24px; margin-right: 10px;">🤖</div>
            <div>
                <div style="color: #a78bfa; font-size: 14px; font-weight: bold;">GEMINI AI INTELLIGENCE</div>
                <div style="color: #a0aec0; font-size: 11px;">Powered by Google Gemini + Finnhub</div>
            </div>
        </div>

        <!-- AI Verdict -->
        <div style="background: rgba(45, 55, 72, 0.3); padding: 12px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid {verdict_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">AI VERDICT</div>
                    <div style="color: {verdict_color}; font-weight: bold; font-size: 18px;">{verdict}</div>
                </div>
                <div>
                    <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">CONFIDENCE</div>
                    <div style="color: {conf_color}; font-weight: bold; font-size: 18px;">{confidence}%</div>
                </div>
            </div>
        </div>

        <!-- AI Reasoning -->
        <div style="margin-bottom: 12px;">
            <div style="color: #a78bfa; font-size: 11px; margin-bottom: 6px;">💡 AI ANALYSIS</div>
            <div style="color: #e2e8f0; font-size: 13px; line-height: 1.5;">{reasoning}</div>
        </div>

        <!-- Risk Factor -->
        <div style="margin-bottom: 12px;">
            <div style="color: #fbbf24; font-size: 11px; margin-bottom: 6px;">⚠️ RISK FACTOR</div>
            <div style="color: #e2e8f0; font-size: 13px; line-height: 1.5;">{risk}</div>
        </div>

        <!-- Latest News -->
        <div>
            <div style="color: #a78bfa; font-size: 11px; margin-bottom: 6px;">📰 LATEST NEWS</div>
            <div style="color: #a0aec0; font-size: 12px; font-style: italic;">{headline}</div>
        </div>
    </div>
    """


def generate_symbol_cards_html(all_symbols_analysis):
    """Generate beautiful card-based HTML with one card per symbol"""

    # Sort: positions first, then by score
    positions_cards = [s for s in all_symbols_analysis if s['position_analysis']]
    new_symbols_cards = [s for s in all_symbols_analysis if not s['position_analysis']]

    positions_cards.sort(key=lambda x: x['position_analysis']['profit'])
    new_symbols_cards.sort(key=lambda x: x['score'], reverse=True)

    # Generate cards HTML
    cards_html = ""

    # POSITIONS FIRST
    if positions_cards:
        cards_html += '<h2 style="color: #e2e8f0; margin: 40px 0 20px 0; font-size: 24px; border-bottom: 3px solid #3b82f6; padding-bottom: 10px;">📊 YOUR CURRENT POSITIONS</h2>'

        for analysis in positions_cards:
            pos = analysis['position_analysis']
            profit_color = "#10b981" if pos['profit'] > 0 else "#ef4444"

            reasons_html = "".join([f"<div style='padding: 4px 0; font-size: 13px;'>{r}</div>" for r in analysis['reasons'][:5]])
            warnings_html = "".join([f"<div style='padding: 4px 0; font-size: 13px; color: #fbbf24;'>{w}</div>" for w in analysis['warnings'][:3]])

            cards_html += f"""
            <div style="background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); border-radius: 12px; padding: 24px; margin-bottom: 20px; border-left: 6px solid {analysis['decision_color']}; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div>
                        <h3 style="margin: 0; font-size: 24px; color: #e2e8f0;">{analysis['symbol']}</h3>
                        <div style="color: #a0aec0; font-size: 13px; margin-top: 4px;">{pos['type']} Position</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 28px; font-weight: bold; color: {profit_color};">
                            ${pos['profit']:+,.2f}
                        </div>
                        <div style="font-size: 14px; color: {profit_color};">
                            {pos['profit_pct']:+.1f}%
                        </div>
                    </div>
                </div>

                <!-- Position Action -->
                <div style="background: rgba(59, 130, 246, 0.1); border-left: 4px solid #3b82f6; padding: 12px; border-radius: 6px; margin-bottom: 16px;">
                    <strong style="color: #3b82f6; font-size: 16px;">{pos['action']}</strong>
                </div>

                <!-- Current Analysis -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 16px;">
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">CURRENT TREND</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{analysis['trend']}</div>
                    </div>
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">CURRENT PRICE</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{analysis['current_price']:.5f}</div>
                    </div>
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">ENTRY PRICE</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{pos['entry']:.5f}</div>
                    </div>
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">RSI</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{analysis['rsi']:.0f}</div>
                    </div>
                </div>

                <!-- Analysis Score -->
                <div style="background: rgba(45, 55, 72, 0.3); padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <div style="color: #a0aec0; font-size: 12px; margin-bottom: 8px;">CURRENT MARKET SCORE: {analysis['score']}/100</div>
                    <div style="background: #1a202c; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: {analysis['score']}%; height: 100%; background: {analysis['decision_color']};"></div>
                    </div>
                    <div style="margin-top: 8px; font-size: 14px; font-weight: bold; color: {analysis['decision_color']};">
                        {analysis['decision']} - {analysis['confidence']} CONFIDENCE
                    </div>
                </div>

                <!-- Reasons -->
                <div style="margin-bottom: 12px;">
                    <div style="color: #a0aec0; font-size: 12px; margin-bottom: 8px;">WHY THIS SCORE:</div>
                    {reasons_html}
                    {warnings_html}
                </div>

                <!-- Position Verdict -->
                <div style="background: {'rgba(239, 68, 68, 0.1)' if not pos['correct_direction'] else 'rgba(16, 185, 129, 0.1)'}; border-left: 4px solid {'#ef4444' if not pos['correct_direction'] else '#10b981'}; padding: 12px; border-radius: 6px; margin-bottom: 16px;">
                    <strong style="color: {'#ef4444' if not pos['correct_direction'] else '#10b981'};">
                        {'⚠️ POSITION AGAINST TREND' if not pos['correct_direction'] else '✓ Position aligned with trend'}
                    </strong>
                </div>

                <!-- AI Intelligence -->
                {generate_ai_intelligence_html(analysis)}

                <!-- Multi-Timeframe Context -->
                {generate_mtf_html(analysis)}

                <!-- Historical Performance -->
                {generate_historical_html(analysis)}
            </div>
            """

    # NEW OPPORTUNITIES
    if new_symbols_cards:
        cards_html += '<h2 style="color: #e2e8f0; margin: 40px 0 20px 0; font-size: 24px; border-bottom: 3px solid #10b981; padding-bottom: 10px;">💎 NEW TRADING OPPORTUNITIES</h2>'

        for analysis in new_symbols_cards[:10]:  # Top 10
            reasons_html = "".join([f"<div style='padding: 4px 0; font-size: 13px;'>{r}</div>" for r in analysis['reasons'][:5]])
            warnings_html = "".join([f"<div style='padding: 4px 0; font-size: 13px; color: #fbbf24;'>{w}</div>" for w in analysis['warnings'][:3]])

            if analysis['decision'] == "DON'T TRADE":
                continue  # Skip don't trade symbols

            # Prepare trade setup HTML only if we have valid prices
            trade_setup_html = ""
            if analysis['entry_price'] is not None and analysis['stop_loss'] is not None and analysis['take_profit'] is not None:
                trade_setup_html = f"""
                <!-- Trade Setup -->
                <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 12px; border-radius: 6px; margin-bottom: 16px;">
                    <strong style="color: #10b981; font-size: 16px;">TRADE {analysis['trade_direction']}</strong>
                    <div style="margin-top: 8px; font-size: 13px; color: #e2e8f0;">
                        Entry: {analysis['entry_price']:.5f} | Stop: {analysis['stop_loss']:.5f} | Target: {analysis['take_profit']:.5f}
                    </div>
                </div>
                """

            cards_html += f"""
            <div style="background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); border-radius: 12px; padding: 24px; margin-bottom: 20px; border-left: 6px solid {analysis['decision_color']}; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div>
                        <h3 style="margin: 0; font-size: 24px; color: #e2e8f0;">{analysis['symbol']}</h3>
                        <div style="color: #a0aec0; font-size: 13px; margin-top: 4px;">New Opportunity</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 24px; font-weight: bold; color: {analysis['decision_color']};">
                            {analysis['decision']}
                        </div>
                        <div style="font-size: 12px; color: #a0aec0;">
                            {analysis['confidence']} CONFIDENCE
                        </div>
                    </div>
                </div>

                {trade_setup_html}

                <!-- Market Metrics -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px;">
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">TREND</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{analysis['trend']}</div>
                    </div>
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">PRICE</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{analysis['current_price']:.5f}</div>
                    </div>
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">RSI</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{analysis['rsi']:.0f}</div>
                    </div>
                    <div style="background: rgba(45, 55, 72, 0.5); padding: 12px; border-radius: 6px;">
                        <div style="color: #a0aec0; font-size: 11px; margin-bottom: 4px;">VOLATILITY</div>
                        <div style="color: #e2e8f0; font-weight: bold;">{analysis['atr_pct']:.2f}%</div>
                    </div>
                </div>

                <!-- Analysis Score -->
                <div style="background: rgba(45, 55, 72, 0.3); padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <div style="color: #a0aec0; font-size: 12px; margin-bottom: 8px;">SETUP QUALITY: {analysis['score']}/100</div>
                    <div style="background: #1a202c; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: {analysis['score']}%; height: 100%; background: {analysis['decision_color']};"></div>
                    </div>
                </div>

                <!-- Reasons -->
                <div style="margin-bottom: 16px;">
                    <div style="color: #a0aec0; font-size: 12px; margin-bottom: 8px;">WHY TRADE:</div>
                    {reasons_html}
                    {warnings_html}
                </div>

                <!-- AI Intelligence -->
                {generate_ai_intelligence_html(analysis)}

                <!-- Multi-Timeframe Context -->
                {generate_mtf_html(analysis)}

                <!-- Historical Performance -->
                {generate_historical_html(analysis)}
            </div>
            """

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
                max-width: 1200px;
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
            }}
            .header h1 {{
                margin: 0;
                font-size: 42px;
                font-weight: bold;
            }}
            .content {{
                padding: 40px;
                color: #e2e8f0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 SYMBOL DECISION CARDS</h1>
                <div style="color: rgba(255,255,255,0.8); margin-top: 10px; font-size: 16px;">
                    Every Symbol • Deep Analysis • Clear Decision
                </div>
                <div style="color: rgba(255,255,255,0.7); margin-top: 15px; font-size: 14px;">
                    {datetime.now().strftime('%A, %B %d, %Y • %H:%M:%S')}
                </div>
            </div>
            <div class="content">
                {cards_html}
            </div>
        </div>
    </body>
    </html>
    """

    return html


def run():
    """Main execution"""
    print("="*80)
    print("SYMBOL DECISION CARDS - Deep Analysis for Every Symbol")
    print("="*80)
    print()

    if not init_mt5():
        print("[ERROR] Failed to initialize MT5")
        return

    # Get positions
    positions = get_positions()
    position_dict = {p.symbol: p for p in positions} if positions else {}

    # Analyze all symbols (positions + opportunities)
    symbols_to_analyze = list(set(list(position_dict.keys()) + ALL_SYMBOLS[:15]))

    all_analysis = []

    print(f"Analyzing {len(symbols_to_analyze)} symbols...")
    for symbol in symbols_to_analyze:
        print(f"  Analyzing {symbol}...")
        position = position_dict.get(symbol)
        analysis = analyze_symbol_decision(symbol, position)
        if analysis:
            all_analysis.append(analysis)

    print("\nGenerating symbol decision cards...")
    html_report = generate_symbol_cards_html(all_analysis)

    print("Sending symbol cards to email...")
    subject = f"🎯 Symbol Decision Cards - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    if send_email(subject, html_report):
        print("[SUCCESS] Symbol decision cards sent!")
    else:
        print("[ERROR] Failed to send email")

    print("\n[DONE]\n")


if __name__ == "__main__":
    run()
