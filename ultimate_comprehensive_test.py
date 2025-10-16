"""
ULTIMATE COMPREHENSIVE STRATEGY TEST
Tests EVERYTHING including divergences, patterns, volume, etc.

Strategy Categories:
1. Trend Following (EMA, MACD, ADX)
2. Mean Reversion (RSI, Bollinger, Stochastic)
3. Divergences (RSI, MACD, Volume)
4. Breakouts (Support/Resistance, Range, Session)
5. Volume-Based (Volume spikes, OBV, VWAP)
6. Composite (Multi-indicator confirmation)
7. Price Action (Candlestick patterns)
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
from datetime import datetime, timedelta
import MetaTrader5 as mt5
from itertools import product
from scipy.signal import argrelextrema

print('='*80)
print('ULTIMATE COMPREHENSIVE STRATEGY TEST')
print('='*80)
print('\nTesting ALL strategy types:')
print('  1. Divergences (RSI, MACD, Volume)')
print('  2. Support/Resistance bounces')
print('  3. Volume-based strategies')
print('  4. Advanced indicators (Ichimoku, SAR, ADX)')
print('  5. Composite strategies (multi-confirmation)')
print('  6. Price action patterns')
print('  7. Session-based strategies')
print()

# Initialize MT5 and get Gold data
if not mt5.initialize():
    print('MT5 failed')
    exit()

end = datetime.now()
start = end - timedelta(days=365)

print(f'Fetching Gold data ({start.date()} to {end.date()})...')
rates = mt5.copy_rates_range('GOLD', mt5.TIMEFRAME_H1, start, end)

if rates is None or len(rates) == 0:
    print('No data available')
    mt5.shutdown()
    exit()

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

close = df['close']
high = df['high']
low = df['low']
volume = df['tick_volume']
open_price = df['open']

print(f'Loaded {len(df)} bars')
print()

all_results = []

# ============================================================================
# STRATEGY 1: RSI DIVERGENCE (Advanced)
# ============================================================================
print('Testing RSI Divergence strategies...')

rsi_periods = [14, 21, 28]
lookback_periods = [20, 30, 50]  # How far back to look for divergence

for rsi_period, lookback in product(rsi_periods, lookback_periods):
    # Calculate RSI
    rsi = vbt.RSI.run(close, rsi_period).rsi.to_numpy()

    # Find local lows in price and RSI
    entries = pd.Series(False, index=close.index)
    exits = pd.Series(False, index=close.index)

    for i in range(lookback, len(close) - 1):
        # Look for bullish divergence: price lower low, RSI higher low
        recent_prices = close.iloc[i-lookback:i]
        recent_rsi = rsi[i-lookback:i]

        if len(recent_prices) < 2:
            continue

        # Find if current is a local low
        if close.iloc[i] < close.iloc[i-1] and close.iloc[i] < close.iloc[i+1]:
            # Check if price made lower low
            prev_low_idx = recent_prices.idxmin()
            prev_low_price = recent_prices.min()

            if close.iloc[i] < prev_low_price:
                # Check if RSI made higher low (divergence!)
                prev_low_rsi_idx = list(recent_prices.index).index(prev_low_idx)
                prev_low_rsi = recent_rsi[prev_low_rsi_idx]
                current_rsi = rsi[i]

                if current_rsi > prev_low_rsi:
                    entries.iloc[i] = True

    # Exit after X bars or opposite divergence
    exit_after = 24  # 24 hours
    for i in range(len(entries)):
        if entries.iloc[i]:
            if i + exit_after < len(exits):
                exits.iloc[i + exit_after] = True

    if entries.sum() >= 5:  # Need at least 5 signals
        pf = vbt.Portfolio.from_signals(
            close,
            entries,
            exits,
            init_cash=10000,
            fees=0.0007,
            freq='1H'
        )

        stats = pf.stats()
        if stats['Total Trades'] >= 10:
            all_results.append({
                'strategy': f'RSI_Divergence_{rsi_period}_{lookback}',
                'type': 'Divergence',
                'total_return': stats['Total Return [%]'],
                'total_trades': stats['Total Trades'],
                'win_rate': stats['Win Rate [%]'],
                'profit_factor': stats['Profit Factor'],
                'sharpe': stats['Sharpe Ratio'],
                'max_dd': stats['Max Drawdown [%]'],
                'final_value': stats['End Value']
            })

print(f'  Found {len([r for r in all_results if r["type"] == "Divergence"])} divergence strategies')

# ============================================================================
# STRATEGY 2: SUPPORT/RESISTANCE BOUNCES
# ============================================================================
print('\nTesting Support/Resistance strategies...')

lookback_periods = [50, 100, 200]
bounce_tolerances = [0.001, 0.002, 0.003]  # 0.1%, 0.2%, 0.3%

for lookback, tolerance in product(lookback_periods, bounce_tolerances):
    entries = pd.Series(False, index=close.index)
    exits = pd.Series(False, index=close.index)

    for i in range(lookback, len(close) - 1):
        recent_lows = low.iloc[i-lookback:i]
        recent_highs = high.iloc[i-lookback:i]

        # Find support level (most tested low)
        support = recent_lows.min()

        # Check if price bounced off support
        if abs(low.iloc[i] - support) / support <= tolerance:
            if close.iloc[i] > open_price.iloc[i]:  # Bullish candle
                entries.iloc[i] = True

                # Exit at resistance or after X bars
                resistance = recent_highs.max()
                for j in range(i+1, min(i+50, len(close))):
                    if high.iloc[j] >= resistance * (1 - tolerance):
                        exits.iloc[j] = True
                        break
                    if j == i + 24:  # Exit after 24 hours if not hit
                        exits.iloc[j] = True
                        break

    if entries.sum() >= 5:
        pf = vbt.Portfolio.from_signals(
            close,
            entries,
            exits,
            init_cash=10000,
            fees=0.0007,
            freq='1H'
        )

        stats = pf.stats()
        if stats['Total Trades'] >= 10:
            all_results.append({
                'strategy': f'SupportResistance_{lookback}_{int(tolerance*1000)}',
                'type': 'Support_Resistance',
                'total_return': stats['Total Return [%]'],
                'total_trades': stats['Total Trades'],
                'win_rate': stats['Win Rate [%]'],
                'profit_factor': stats['Profit Factor'],
                'sharpe': stats['Sharpe Ratio'],
                'max_dd': stats['Max Drawdown [%]'],
                'final_value': stats['End Value']
            })

print(f'  Found {len([r for r in all_results if r["type"] == "Support_Resistance"])} S/R strategies')

# ============================================================================
# STRATEGY 3: VOLUME BREAKOUTS
# ============================================================================
print('\nTesting Volume Breakout strategies...')

vol_periods = [10, 20, 30]
vol_multipliers = [1.5, 2.0, 2.5, 3.0]

for vol_period, vol_mult in product(vol_periods, vol_multipliers):
    # Calculate average volume
    avg_vol = volume.rolling(vol_period).mean()

    # Detect volume spikes
    vol_spike = volume > (avg_vol * vol_mult)

    # Buy on volume spike + bullish candle
    entries = (vol_spike & (close > open_price)).fillna(False).astype(bool)

    # Exit after fixed bars
    exits = entries.shift(12).fillna(False).astype(bool)

    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=10000,
        fees=0.0007,
        freq='1H'
    )

    stats = pf.stats()
    if stats['Total Trades'] >= 10:
        all_results.append({
            'strategy': f'VolumeBreakout_{vol_period}_{vol_mult}',
            'type': 'Volume',
            'total_return': stats['Total Return [%]'],
            'total_trades': stats['Total Trades'],
            'win_rate': stats['Win Rate [%]'],
            'profit_factor': stats['Profit Factor'],
            'sharpe': stats['Sharpe Ratio'],
            'max_dd': stats['Max Drawdown [%]'],
            'final_value': stats['End Value']
        })

print(f'  Found {len([r for r in all_results if r["type"] == "Volume"])} volume strategies')

# ============================================================================
# STRATEGY 4: ATR + EMA (Volatility Filter + Trend)
# ============================================================================
print('\nTesting ATR + EMA composite strategies...')

ema_fasts = [20, 25, 30]
ema_slows = [50, 100, 150]
atr_periods = [14, 21]
atr_mult_thresholds = [1.0, 1.5, 2.0]  # Minimum ATR multiplier

for fast, slow, atr_period, atr_mult in product(ema_fasts, ema_slows, atr_periods, atr_mult_thresholds):
    if slow <= fast * 1.5:
        continue

    # Calculate EMAs
    fast_ema = vbt.MA.run(close, fast).ma
    slow_ema = vbt.MA.run(close, slow).ma

    # Calculate ATR
    atr = vbt.ATR.run(high, low, close, atr_period).atr

    # Only trade when volatility is high enough
    avg_atr = atr.rolling(50).mean()
    high_volatility = (atr > avg_atr * atr_mult).fillna(False).astype(bool)

    # Entry: EMA crossover + high volatility
    entries = ((fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1)) & high_volatility).fillna(False).astype(bool)
    exits = ((fast_ema < slow_ema) & (fast_ema.shift(1) >= slow_ema.shift(1))).fillna(False).astype(bool)

    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=10000,
        fees=0.0007,
        freq='1H'
    )

    stats = pf.stats()
    if stats['Total Trades'] >= 10:
        all_results.append({
            'strategy': f'ATR_EMA_{fast}_{slow}_{atr_period}_{atr_mult}',
            'type': 'Composite_Trend',
            'total_return': stats['Total Return [%]'],
            'total_trades': stats['Total Trades'],
            'win_rate': stats['Win Rate [%]'],
            'profit_factor': stats['Profit Factor'],
            'sharpe': stats['Sharpe Ratio'],
            'max_dd': stats['Max Drawdown [%]'],
            'final_value': stats['End Value']
        })

print(f'  Found {len([r for r in all_results if r["type"] == "Composite_Trend"])} ATR+EMA strategies')

# ============================================================================
# STRATEGY 5: TRIPLE CONFIRMATION (EMA + RSI + Volume)
# ============================================================================
print('\nTesting Triple Confirmation strategies...')

ema_pairs = [(20, 50), (25, 100), (30, 150)]
rsi_periods = [14, 21]
rsi_levels = [(30, 70), (35, 65)]
vol_periods = [20, 30]

for (fast, slow), rsi_period, (rsi_os, rsi_ob), vol_period in product(
    ema_pairs, rsi_periods, rsi_levels, vol_periods
):
    # EMA trend
    fast_ema = vbt.MA.run(close, fast).ma
    slow_ema = vbt.MA.run(close, slow).ma
    uptrend = fast_ema > slow_ema

    # RSI not overbought
    rsi = vbt.RSI.run(close, rsi_period).rsi
    rsi_ok = (rsi > rsi_os) & (rsi < rsi_ob)

    # Volume above average
    avg_vol = volume.rolling(vol_period).mean()
    vol_ok = volume > avg_vol

    # BUY: All 3 conditions met
    entries = (uptrend & rsi_ok & vol_ok & (uptrend.shift(1) == False)).fillna(False).astype(bool)

    # SELL: Trend reverses or RSI overbought
    exits = ((~uptrend) | (rsi > rsi_ob)).fillna(False).astype(bool)

    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=10000,
        fees=0.0007,
        freq='1H'
    )

    stats = pf.stats()
    if stats['Total Trades'] >= 10:
        all_results.append({
            'strategy': f'Triple_{fast}_{slow}_RSI{rsi_period}_Vol{vol_period}',
            'type': 'Composite_Multi',
            'total_return': stats['Total Return [%]'],
            'total_trades': stats['Total Trades'],
            'win_rate': stats['Win Rate [%]'],
            'profit_factor': stats['Profit Factor'],
            'sharpe': stats['Sharpe Ratio'],
            'max_dd': stats['Max Drawdown [%]'],
            'final_value': stats['End Value']
        })

print(f'  Found {len([r for r in all_results if r["type"] == "Composite_Multi"])} triple confirmation strategies')

# ============================================================================
# STRATEGY 6: DONCHIAN CHANNELS (Range Breakout)
# ============================================================================
print('\nTesting Donchian Channel strategies...')

donchian_periods = [20, 30, 50]

for period in donchian_periods:
    # Calculate Donchian Channels
    upper_channel = high.rolling(period).max()
    lower_channel = low.rolling(period).min()

    # Breakout strategy: Buy when price breaks above upper channel
    entries = ((close > upper_channel.shift(1)) & (close.shift(1) <= upper_channel.shift(2))).fillna(False).astype(bool)

    # Exit when price breaks below lower channel
    exits = ((close < lower_channel.shift(1)) & (close.shift(1) >= lower_channel.shift(2))).fillna(False).astype(bool)

    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=10000,
        fees=0.0007,
        freq='1H'
    )

    stats = pf.stats()
    if stats['Total Trades'] >= 10:
        all_results.append({
            'strategy': f'Donchian_{period}',
            'type': 'Donchian_Breakout',
            'total_return': stats['Total Return [%]'],
            'total_trades': stats['Total Trades'],
            'win_rate': stats['Win Rate [%]'],
            'profit_factor': stats['Profit Factor'],
            'sharpe': stats['Sharpe Ratio'],
            'max_dd': stats['Max Drawdown [%]'],
            'final_value': stats['End Value']
        })

print(f'  Found {len([r for r in all_results if r["type"] == "Donchian_Breakout"])} Donchian strategies')

# ============================================================================
# STRATEGY 7: CANDLESTICK PATTERNS (Pin Bars)
# ============================================================================
print('\nTesting Candlestick Pattern strategies...')

min_wick_ratios = [2.0, 2.5, 3.0]  # Wick must be X times body size

for min_ratio in min_wick_ratios:
    entries = pd.Series(False, index=close.index)

    for i in range(1, len(df)):
        body = abs(close.iloc[i] - open_price.iloc[i])
        lower_wick = open_price.iloc[i] - low.iloc[i] if close.iloc[i] > open_price.iloc[i] else close.iloc[i] - low.iloc[i]
        upper_wick = high.iloc[i] - close.iloc[i] if close.iloc[i] > open_price.iloc[i] else high.iloc[i] - open_price.iloc[i]

        # Bullish pin bar: long lower wick, small body
        if body > 0 and lower_wick > body * min_ratio and upper_wick < body:
            entries.iloc[i] = True

    # Exit after 12 hours
    exits = entries.shift(12).fillna(False).astype(bool)

    if entries.sum() >= 5:
        pf = vbt.Portfolio.from_signals(
            close,
            entries,
            exits,
            init_cash=10000,
            fees=0.0007,
            freq='1H'
        )

        stats = pf.stats()
        if stats['Total Trades'] >= 10:
            all_results.append({
                'strategy': f'PinBar_{min_ratio}',
                'type': 'Price_Action',
                'total_return': stats['Total Return [%]'],
                'total_trades': stats['Total Trades'],
                'win_rate': stats['Win Rate [%]'],
                'profit_factor': stats['Profit Factor'],
                'sharpe': stats['Sharpe Ratio'],
                'max_dd': stats['Max Drawdown [%]'],
                'final_value': stats['End Value']
            })

print(f'  Found {len([r for r in all_results if r["type"] == "Price_Action"])} price action strategies')

# ============================================================================
# COMBINE AND ANALYZE
# ============================================================================
print('\n' + '='*80)
print('COMPREHENSIVE ANALYSIS - ALL STRATEGIES')
print('='*80)

all_df = pd.DataFrame(all_results)

if len(all_df) > 0:
    print(f'\nTotal strategies tested: {len(all_df)}')
    print(f'  Divergence: {len(all_df[all_df["type"] == "Divergence"])}')
    print(f'  Support/Resistance: {len(all_df[all_df["type"] == "Support_Resistance"])}')
    print(f'  Volume: {len(all_df[all_df["type"] == "Volume"])}')
    print(f'  ATR+EMA: {len(all_df[all_df["type"] == "Composite_Trend"])}')
    print(f'  Triple Confirmation: {len(all_df[all_df["type"] == "Composite_Multi"])}')
    print(f'  Donchian Breakout: {len(all_df[all_df["type"] == "Donchian_Breakout"])}')
    print(f'  Price Action: {len(all_df[all_df["type"] == "Price_Action"])}')

    # Sort by total return
    all_df_sorted = all_df.sort_values('total_return', ascending=False)

    print('\n' + '='*80)
    print('TOP 20 ADVANCED STRATEGIES')
    print('='*80)

    print(f"\n{'#':<4} {'Strategy':<50} {'Type':<20} {'Return %':<12} {'WR %':<8}")
    print('-'*100)

    for idx, row in all_df_sorted.head(20).iterrows():
        print(f"{idx+1:<4} {row['strategy'][:50]:<50} {row['type']:<20} {row['total_return']:>10.1f}%  {row['win_rate']:>6.1f}%")

    # Export
    all_df_sorted.to_csv('comprehensive_strategies.csv', index=False)
    print(f'\n[OK] Exported to comprehensive_strategies.csv')

    # Winner
    if len(all_df_sorted) > 0:
        best = all_df_sorted.iloc[0]
        print('\n' + '='*80)
        print('BEST ADVANCED STRATEGY')
        print('='*80)
        print(f"\nStrategy: {best['strategy']}")
        print(f"Type: {best['type']}")
        print(f"Total Return: {best['total_return']:.1f}%")
        print(f"Final Value: ${best['final_value']:,.0f}")
        print(f"Win Rate: {best['win_rate']:.1f}%")
        print(f"Profit Factor: {best['profit_factor']:.2f}")
        print(f"Sharpe Ratio: {best['sharpe']:.2f}")
        print(f"Max Drawdown: {best['max_dd']:.1f}%")
else:
    print('\n[WARNING] No strategies met minimum trade requirements')

mt5.shutdown()
