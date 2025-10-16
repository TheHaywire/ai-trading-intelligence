#!/usr/bin/env python3
"""
GOLD Price Action Analysis
Analyze recent GOLD trends and identify which strategies would have captured profitable moves.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker


def analyze_gold_trends():
    """Analyze GOLD price trends and strategy performance."""
    
    broker = MT5Broker(
        login="165835373", 
        password="Manan@123!!",
        server="XMGlobal-MT5 2",
        paper_mode=False
    )
    
    print("=== GOLD PRICE ACTION ANALYSIS ===")
    print("Analyzing recent trends and strategy performance...")
    
    try:
        broker.connect()
        print("✅ Connected to MT5")
        
        # Get comprehensive historical data
        bars_h1 = broker.get_bars("GOLD", "H1", count=500) or []
        bars_h4 = broker.get_bars("GOLD", "H4", count=200) or []
        bars_d1 = broker.get_bars("GOLD", "D1", count=100) or []
        
        if len(bars_d1) == 0:
            print("❌ No historical data available")
            return
            
        print(f"📊 Data Retrieved: {len(bars_d1)} daily, {len(bars_h4)} H4, {len(bars_h1)} H1 bars")
        
        # Convert to pandas for analysis
        df_d1 = pd.DataFrame(bars_d1)
        df_h4 = pd.DataFrame(bars_h4)
        df_h1 = pd.DataFrame(bars_h1)
        
        if 'close' in df_d1.columns:
            df_d1['close'] = df_d1['close'].astype(float)
            df_d1 = df_d1.sort_values('time').reset_index(drop=True)
        
        if 'close' in df_h4.columns:
            df_h4['close'] = df_h4['close'].astype(float)
            df_h4 = df_h4.sort_values('time').reset_index(drop=True)
            
        if 'close' in df_h1.columns:
            df_h1['close'] = df_h1['close'].astype(float)
            df_h1 = df_h1.sort_values('time').reset_index(drop=True)
        
        # Analyze major trends
        print("\n=== MAJOR TREND ANALYSIS ===")
        
        # Daily trends
        if len(df_d1) >= 20:
            recent_daily = df_d1.tail(20)
            start_price = recent_daily.iloc[0]['close']
            end_price = recent_daily.iloc[-1]['close']
            daily_change = (end_price - start_price) / start_price * 100
            
            print(f"📈 Daily Trend (last 20 days):")
            print(f"  Start: ${start_price:.2f}")
            print(f"  End: ${end_price:.2f}")
            print(f"  Change: {daily_change:+.2f}%")
            
            if daily_change > 2:
                print(f"  📊 Strong Uptrend - EMA Trend Strategy would capture this")
            elif daily_change < -2:
                print(f"  📉 Strong Downtrend - EMA Trend Strategy would capture this")
            else:
                print(f"  📄 Sideways - Mean Reversion Strategy preferable")
        
        # Weekly analysis
        if len(df_d1) >= 7:
            weekly_change = []
            for i in range(7, len(df_d1)):
                week_start = df_d1.iloc[i-7]['close']
                week_end = df_d1.iloc[i]['close']
                change = (week_end - week_start) / week_start * 100
                weekly_change.append({
                    'period': i,
                    'start': week_start,
                    'end': week_end,
                    'change': change,
                    'high': df_d1.iloc[i-7:i]['close'].max(),
                    'low': df_d1.iloc[i-7:i]['close'].min()
                })
            
            print(f"\n📅 Weekly Performance (last 4 weeks):")
            for i, week in enumerate(weekly_change[-4:]):
                period_end = len(df_d1) - len(weekly_change) + week['period'] - 7
                print(f"  Week {i+1}: ${week['start']:.2f} → ${week['end']:.2f} ({week['change']:+.2f}%)")
                
                # Identify strategy effectiveness
                if abs(week['change']) > 3:  # Significant move
                    if week['change'] > 0:
                        print(f"    🎯 Strategy: EMA Trend BUY (trend continuation)")
                        print(f"    💰 Profit capture: {week['change']:.1f}%")
                    else:
                        print(f"    🎯 Strategy: EMA Trend SELL (trend continuation)")
                        print(f"    💰 Profit capture: {abs(week['change']):.1f}%")
                elif abs(week['change']) < 1:  # Low volatility week
                    print(f"    🎯 Strategy: Mean Reversion (mean reversion)")
                    print(f"    💰 Profit capture: Range-bound scalping")
        
        # Intraday volatility analysis
        if len(df_h1) >= 24:
            print(f"\n⚡ Intraday Volatility Analysis:")
            
            # Calculate daily ranges
            daily_ranges = []
            for i in range(0, len(df_h1), 24):
                day_bars = df_h1.iloc[i:i+24]
                if len(day_bars) > 0:
                    daily_high = day_bars['high'].max()
                    daily_low = day_bars['low'].min()
                    daily_range = daily_high - daily_low
                    daily_range_pct = daily_range / day_bars.iloc[0]['open'] * 100
                    daily_ranges.append(daily_range_pct)
            
            if daily_ranges:
                avg_intraday_range = np.mean(daily_ranges[-7:])  # Last 7 days
                print(f"  Average intraday range: {avg_intraday_range:.1f}%")
                
                if avg_intraday_range > 1.5:
                    print(f"  📊 High volatility - EMA Trend Strategy optimal")
                    print(f"  💰 Profit opportunity: Capture trend moves of {avg_intraday_range:.1f}%")
                elif avg_intraday_range < 0.8:
                    print(f"  📄 Low volatility - Mean Reversion Strategy optimal")
                    print(f"  💰 Profit opportunity: Scalp small ranges")
                
                # Identify breakout days
                high_range_days = [i for i, r in enumerate(daily_ranges[-10:]) if r > avg_intraday_range * 1.5]
                if high_range_days:
                    print(f"  🔥 Breakout days detected: {len(high_range_days)} in last 10 days")
                    print(f"  💰 Strategy: Breakout Session Open for explosive moves")
        
        # Strategy Performance Simulation
        print(f"\n=== STRATEGY PERFORMANCE SIMULATION ===")
        
        # Simulate EMA Trend Strategy
        if len(df_d1) >= 50:
            print(f"📈 EMA Trend Strategy Simulation:")
            
            # Calculate EMA50
            df_d1['ema50'] = df_d1['close'].ewm(span=50).mean()
            
            signals = []
            for i in range(50, len(df_d1)):
                current_price = df_d1.iloc[i]['close']
                current_ema = df_d1.iloc[i]['ema50']
                prev_price = df_d1.iloc[i-1]['close']
                prev_ema = df_d1.iloc[i-1]['ema50']
                
                # Trend signals
                if current_price > current_ema and prev_price <= prev_ema:
                    signals.append({'type': 'BUY', 'day': i, 'price': current_price})
                elif current_price < current_ema and prev_price >= prev_ema:
                    signals.append({'type': 'SELL', 'day': i, 'price': current_price})
            
            # Calculate performance
            profits = []
            for signal in signals[-10:]:  # Last 10 signals
                day_idx = signal['day']
                entry_price = signal['price']
                
                # Look ahead 3 days for exit
                exit_day = min(day_idx + 3, len(df_d1)-1)
                exit_price = df_d1.iloc[exit_day]['close']
                
                if signal['type'] == 'BUY':
                    profit = (exit_price - entry_price) / entry_price * 100
                else:
                    profit = (entry_price - exit_price) / entry_price * 100
                
                profits.append(profit)
            
            if profits:
                avg_profit = np.mean(profits)
                win_rate = len([p for p in profits if p > 0]) / len(profits) * 100
                print(f"  Signals: {len(signals[-10:])} trades")
                print(f"  Win Rate: {win_rate:.1f}%")
                print(f"  Average Profit: {avg_profit:+.1f}%")
                print(f"  Best Trade: {max(profits):+.1f}%")
                print(f"  Worst Trade: {min(profits):+.1f}%")
        
        # Identify best profit capture opportunities
        print(f"\n=== PROFIT CAPTURE OPPORTUNITIES ===")
        
        # Long-term trends
        if len(df_d1) >= 30:
            trend_30d = (df_d1.iloc[-1]['close'] - df_d1.iloc[-30]['close']) / df_d1.iloc[-30]['close'] * 100
            
            if abs(trend_30d) > 5:
                direction = "BUY" if trend_30d > 0 else "SELL"
                print(f"🔥 Major Trend (30d): {trend_30d:+.1f}%")
                print(f"   Strategy: EMA Trend {direction}")
                print(f"   Profit: {abs(trend_30d):.1f}% captured")
        
        # Mean reversion opportunities  
        if len(df_d1) >= 20:
            recent_range = {
                'high': df_d1.tail(20)['high'].max(),
                'low': df_d1.tail(20)['low'].min(),
                'avg': df_d1.tail(20)['close'].mean()
            }
            
            current_price = df_d1.iloc[-1]['close']
            range_position = (current_price - recent_range['low']) / (recent_range['high'] - recent_range['low'])
            
            print(f"\n📊 Current Range Position: {range_position:.1%}")
            
            if range_position > 0.8:
                print(f"   Strategy: Mean Reversion SELL")
                print(f"   Profit: Sell at resistance, buy at mean (${recent_range['avg']:.2f})")
            elif range_position < 0.2:
                print(f"   Strategy: Mean Reversion BUY") 
                print(f"   Profit: Buy at support, sell at mean (${recent_range['avg']:.2f})")
            else:
                print(f"   Strategy: Range trading - buy low, sell high")
                print(f"   Profit: Capture ${recent_range['high'] - recent_range['low']:.2f} range")
        
        # Current market analysis
        print(f"\n=== CURRENT MARKET SIGNALS ===")
        
        current_price = bars_h1[-1]['close'] if bars_h1 else bars_d1.iloc[-1]['close']
        
        # VIX/Gold relationship (simplified volatility proxy)
        recent_volatility = np.std(df_d1.tail(10)['close']) / df_d1.tail(10)['close'].mean()
        
        print(f"Current GOLD: ${current_price:.2f}")
        print(f"Recent volatility: {recent_volatility:.3f}")
        
        if recent_volatility > 0.015:  # High volatility threshold
            print(f"🎯 HIGH VOLATILTY - Trend following strategies (EMA Trend)")
            print(f"💰 Profit opportunity: Large directional moves")
        else:
            print(f"📄 LOW VOLATILITY - Mean reversion strategies (Bands)")
            print(f"💰 Profit opportunity: Small range scalping")
        
        # Correlation analysis
        if len(df_d1) >= 20:
            daily_returns = df_d1['close'].pct_change().dropna()
            
            # Trend persistence (serial correlation)
            returns_autocorr = daily_returns.autocorr(lag=1)
            
            print(f"\n📈 Market Structure:")
            print(f"Autorrelation: {returns_autocorr:.3f}")
            
            if returns_autocorr > 0.2:
                print(f"🎯 Trend continuation likely - EMA Trend Strategy")
            elif returns_autocorr < -0.2:
                print(f"📄 Mean reversion likely - Mean Reversion Strategy")
            else:
                print(f"⚖️ Random walk - Mixed strategy approach")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        broker.disconnect()
        print("\n✅ Analysis complete")

if __name__ == "__main__":
    analyze_gold_trends()
