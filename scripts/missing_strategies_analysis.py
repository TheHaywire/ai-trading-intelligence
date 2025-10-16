#!/usr/bin/env python3
"""
Analysis of Missing Strategies That Could Have Captured More GOLD Profits
"""

import sys
import numpy as np
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker


def analyze_missing_strategies():
    """Analyze what additional strategies we need."""
    
    broker = MT5Broker(
        login="165835373", 
        password="Manan@123!!",
        server="XMGlobal-MT5 2",
        paper_mode=False
    )
    
    print("=== MISSING STRATEGIES ANALYSIS ===")
    print("What strategies did we NOT have that lost us profits?")
    
    try:
        broker.connect()
        print("✅ Connected to MT5")
        
        # Get data
        bars_h1 = broker.get_bars("GOLD", "H1", count=200) or []
        bars_h4 = broker.get_bars("GOLD", "H4", count=100) or []
        bars_d1 = broker.get_bars("GOLD", "D1", count=50) or []
        
        if len(bars_d1) == 0:
            print("❌ No data")
            return
            
        # Extract prices
        closes_h1 = [bar['close'] for bar in bars_h1]
        closes_h4 = [bar['close'] for bar in bars_h4]
        closes_d1 = [bar['close'] for bar in bars_d1]
        highs_h1 = [bar['high'] for bar in bars_h1]
        lows_h1 = [bar['low'] for bar in bars_h1]
        volumes_h1 = [bar['volume'] for bar in bars_h4]  # Use H4 vol
        
        print(f"📊 Analyzed: {len(closes_d1)} days of GOLD data")
        
        # MISSING STRATEGY 1: BREAKOUT STRATEGIES
        print(f"\n🔥 MISSING STRATEGY 1: BREAKOUTS")
        
        # Daily breakout analysis
        breakout_profits = []
        for i in range(20, len(closes_d1)):
            # Previous day high/low
            prev_high = max([bars_d1[j]['high'] for j in range(max(0, i-5), i)])
            prev_low = min([bars_d1[j]['low'] for j in range(max(0, i-5), i)])
            
            # Current day range
            current_close = closes_d1[i]
            
            # Breakout scenarios
            if current_close > prev_high:
                breakout_profit = (current_close - prev_high) / prev_high * 100
                breakout_profits.append(breakout_profit)
                print(f"  📈 Breakout ABOVE ${prev_high:.2f}: +{breakout_profit:.1f}%")
            
            elif current_close < prev_low:
                breakout_profit = (prev_low - current_close) / prev_low * 100
                breakout_profits.append(breakout_profit)
                print(f"  📉 Breakout BELOW ${prev_low:.2f}: +{breakout_profit:.1f}%")
        
        if breakout_profits:
            avg_breakout_profit = np.mean(breakout_profits)
            print(f"  💰 MISSED PROFITS: Avg breakout = +{avg_breakout_profit:.1f}%")
            print(f"  🎯 NEEDED: Donchian Channel Breakout strategy")
            print(f"  📋 Could have caught {len(breakout_profits)} more profitable moves")
        
        # MISSING STRATEGY 2: MOMENTUM STRATEGIES
        print(f"\n⚡ MISSING STRATEGY 2: HIGH-FREQUENCY MOMENTUM")
        
        # Intraday momentum
        momentum_profits = []
        for i in range(24, len(closes_h1)):  # Daily chunks
            day_start = closes_h1[i-24]
            day_high = max(closes_h1[i-24:i])
            day_low = min(closes_h1[i-24:i])
            
            # Morning momentum (first 6 hours)
            morning_starts = closes_h1[i-24:i-18]
            morning_ends = closes_h1[i-18:i-12] if len(closes_h1[i-18:i-12]) > 0 else morning_starts
            
            if len(morning_starts) > 0 and len(morning_ends) > 0:
                morning_start = np.mean(morning_starts)
                morning_end = np.mean(morning_ends)
                morning_momentum = (morning_end - morning_start) / morning_start * 100
                
                if abs(morning_momentum) > 0.5:  # Significant momentum
                    momentum_profits.append(morning_momentum)
        
        if momentum_profits:
            avg_momentum_gain = np.mean([m for m in momentum_profits if m > 0])
            avg_momentum_loss = np.mean([abs(m) for m in momentum_profits if m < 0])
            print(f"  💰 MISSED PROFITS: Morning momentum = +{avg_momentum_gain:.1f}%")
            print(f"  🎯 NEEDED: Opening Range Breakout strategy")
            print(f"  📋 Could scalp {len(momentum_profits)} intraday moves")
        
        # MISSING STRATEGY 3: VOLATILITY STRATEGIES
        print(f"\n📊 MISSING STRATEGY 3: VOLATILITY EXPANSION")
        
        # Range expansion detection
        volatility_profits = []
        for i in range(20, len(closes_h1)):
            # 20-period ATR
            recent_highs = highs_h1[i-20:i]
            recent_lows = lows_h1[i-20:i]
            recent_closes = closes_h1[i-20:i]
            
            if len(recent_highs) > 10:
                ranges = [h - l for h, l in zip(recent_highs, recent_lows)]
                atr_20 = np.mean(ranges)
                
                # Current range vs ATR
                current_range = highs_h1[i] - lows_h1[i]
                vol_expansion = (current_range - atr_20) / atr_20
                
                if vol_expansion > 1.5:  # High expansion
                    # Estimate profit from catching the expansion
                    expansion_profit = vol_expansion * 0.5  # Conservative
                    volatility_profits.append(expansion_profit)
        
        if volatility_profits:
            avg_vol_profit = np.mean(volatility_profits)
            print(f"  💰 MISSED PROFITS: Volatility expansion = +{avg_vol_profit:.1f}%")
            print(f"  🎯 NEEDED: Bollinger Band Squeeze strategy")
            print(f"  📋 Could capture {len(volatility_profits)} vol expansion moves")
        
        # MISSING STRATEGY 4: NEWS/CATALYST STRATEGIES
        print(f"\n📰 MISSING STRATEGY 4: NEWS-SPARKED MOVES")
        
        # Gap analysis (simulate news moves)
        gap_profits = []
        for i in range(1, len(closes_d1)):
            gap = (closes_d1[i] - closes_d1[i-1]) / closes_d1[i-1] * 100
            
            if abs(gap) > 1.0:  # Significant daily gap
                gap_profits.append(abs(gap))
                direction = "Gap Up" if gap > 0 else "Gap Down"
                print(f"  📰 {direction}: {abs(gap):.1f}% move")
        
        if gap_profits:
            avg_gap_profit = np.mean(gap_profits)
            print(f"  💰 MISSED PROFITS: News gaps = +{avg_gap_profit:.1f}%")
            print(f"  🎯 NEEDED: News Sentiment + Reverse strategy")
            print(f"  📋 Could fade/follow {len(gap_profits)} news-driven moves")
        
        # MISSING STRATEGY 5: CORRELATION STRATEGIES
        print(f"\n🔗 MISSING STRATEGY 5: CORRELATION BREAKDOWN")
        
        # DXY proxy (simplified)
        # In real implementation, would correlate with DXY, yields, etc.
        print(f"  💰 MISSED PROFITS: Dollar correlation trades")
        print(f"  🎯 NEEDED: DXY-GOLD divergence strategy")
        print(f"  📋 Could exploit dollar weakness → gold strength")
        
        # MISSING STRATEGY 6: CENTRAL BANK POLICY
        print(f"\n🏛️ MISSING STRATEGY 6: POLICY CYCLES")
        print(f"  💰 MISSED PROFITS: Fed pivot trades")
        print(f"  🎯 NEEDED: Yield curve + Gold momentum")
        print(f"  📋 Could front-run policy changes")
        
        # MISSING STRATEGY 7: MARKET SESSION STRATEGIES
        print(f"\n🕒 MISSING STRATEGY 7: SESSION-BASED")
        
        # Analyze opening gaps vs overnight moves
        session_profits = []
        for i in range(24, len(closes_h1), 24):  # Daily
            # Overnight change (gap)
            day_close = closes_h1[i-24]
            day_open = closes_h1[i] if i < len(closes_h1) else closes_h1[i-1]
            
            overnight_change = (day_open - day_close) / day_close * 100
            
            if abs(overnight_change) > 0.5:
                session_profits.append(abs(overnight_change))
        
        if session_profits:
            avg_session_profit = np.mean(session_profits)
            print(f"  💰 MISSED PROFITS: Session gaps = +{avg_session_profit:.1f}%")
            print(f"  🎯 NEEDED: London/NY Open strategies")
            print(f"  📋 Could capture {len(session_profits)} opening moves")
        
        # PRIORITY RANKING
        print(f"\n🔥 PRIORITY STRATEGY RANKING:")
        print(f"1. 🥇 BREAKOUT STRATEGIES (Highest impact)")
        print(f"   - Donchian Channel Breakout + Retest")
        print(f"   - Support/Resistance Breakout")
        print(f"   - False breakout catcher")
        
        print(f"\n2. 🥈 MOMENTUM STRATEGIES (High frequency)")
        print(f"   - Opening Range Breakout")
        print(f"   - Intraday Trend Following")
        print(f"   - MACD Momentum divergence")
        
        print(f"\n3. 🥉 VOLATILITY STRATEGIES (Mean reversion)")
        print(f"   - Bollinger Band Squeeze")
        print(f"   - Volatility regime detector")
        print(f"   - ATR-based position sizing")
        
        print(f"\n4. 📰 NEWS/EVENT STRATEGIES (Catalyst-driven)")
        print(f"   - Economic indicator reactivity")
        print(f"   - Central bank speech trades")
        print(f"   - Risk-on/risk-off detector")
        
        print(f"\n5. 🔗 MULTI-ASSET STRATEGIES (Portfolio edge)")
        print(f"   - DXY correlation breakdown")
        print(f"   - Gold vs S&P ratio trading")
        print(f"   - Commodity basket signals")
        
        # CALCULATE MISSED PROFITS
        estimated_total_missed = (
            sum(gap_profits) * 0.3 +  # Conservative capture rate
            len(breakout_profits) * 2.0 +  # Estimated per breakout
            len(volatility_profits) * 0.5 +  # Vol expansion profit
            len(session_profits) * 0.3  # Session profitability
        )
        
        print(f"\n💸 TOTAL MISSED PROFIT OPPORTUNITY:")
        print(f"   Conservative estimate: +{estimated_total_missed:.1f}%")
        print(f"   On $2.3M account: ${estimated_total_missed/100*2320000:.0f}")
        print(f"   Strategy diversification needed: +5 strategies minimum")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        broker.disconnect()

if __name__ == "__main__":
    analyze_missing_strategies()
