"""
VALIDATE TOP 5 WINNERS - Test on different time periods
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
from datetime import datetime, timedelta
import MetaTrader5 as mt5

print('='*80)
print('WALK-FORWARD VALIDATION - TOP 5 STRATEGIES')
print('='*80)

mt5.initialize()

# Test periods
now = datetime.now()
periods = [
    {'name': 'Last 6 Months', 'start': now - timedelta(days=180), 'end': now},
    {'name': 'Last 3 Months', 'start': now - timedelta(days=90), 'end': now},
    {'name': 'Q1 2025', 'start': datetime(2025, 1, 1), 'end': datetime(2025, 3, 31)},
    {'name': 'Q2 2025', 'start': datetime(2025, 4, 1), 'end': datetime(2025, 6, 30)},
    {'name': 'Q3 2025', 'start': datetime(2025, 7, 1), 'end': datetime(2025, 9, 30)},
]

all_results = []

for period in periods:
    print(f'\n{"="*80}')
    print(f'{period["name"]}: {period["start"].date()} to {period["end"].date()}')
    print('='*80)

    rates = mt5.copy_rates_range('GOLD', mt5.TIMEFRAME_H1, period['start'], period['end'])

    if rates is None or len(rates) < 100:
        print(f'  [SKIP] Insufficient data')
        continue

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    close = df['close']
    high = df['high']
    low = df['low']

    print(f'  Bars: {len(df)} | Price: ${close.iloc[0]:.0f} -> ${close.iloc[-1]:.0f} ({((close.iloc[-1]/close.iloc[0]-1)*100):.1f}%)')

    # Test RSI_28_35_80
    rsi = vbt.RSI.run(close, 28).rsi
    entries = rsi.vbt.crossed_above(35)
    exits = rsi.vbt.crossed_below(80)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.0007, freq='1H')
    stats = pf.stats()
    if stats['Total Trades'] >= 5:
        all_results.append({'period': period['name'], 'strategy': 'RSI_28_35_80',
                           'return': stats['Total Return [%]'], 'trades': stats['Total Trades'],
                           'wr': stats['Win Rate [%]'], 'pf': stats['Profit Factor']})
        print(f'  RSI_28_35_80:       {stats["Total Return [%]"]:>7.1f}% | {stats["Total Trades"]:>3.0f} trades | {stats["Win Rate [%]"]:>5.1f}% WR')

    # Test EMA_25_100
    fast = vbt.MA.run(close, 25).ma
    slow = vbt.MA.run(close, 100).ma
    entries = fast.vbt.crossed_above(slow)
    exits = fast.vbt.crossed_below(slow)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.0007, freq='1H')
    stats = pf.stats()
    if stats['Total Trades'] >= 5:
        all_results.append({'period': period['name'], 'strategy': 'EMA_25_100',
                           'return': stats['Total Return [%]'], 'trades': stats['Total Trades'],
                           'wr': stats['Win Rate [%]'], 'pf': stats['Profit Factor']})
        print(f'  EMA_25_100:         {stats["Total Return [%]"]:>7.1f}% | {stats["Total Trades"]:>3.0f} trades | {stats["Win Rate [%]"]:>5.1f}% WR')

    # Test EMA_20_100
    fast = vbt.MA.run(close, 20).ma
    slow = vbt.MA.run(close, 100).ma
    entries = fast.vbt.crossed_above(slow)
    exits = fast.vbt.crossed_below(slow)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.0007, freq='1H')
    stats = pf.stats()
    if stats['Total Trades'] >= 5:
        all_results.append({'period': period['name'], 'strategy': 'EMA_20_100',
                           'return': stats['Total Return [%]'], 'trades': stats['Total Trades'],
                           'wr': stats['Win Rate [%]'], 'pf': stats['Profit Factor']})
        print(f'  EMA_20_100:         {stats["Total Return [%]"]:>7.1f}% | {stats["Total Trades"]:>3.0f} trades | {stats["Win Rate [%]"]:>5.1f}% WR')

    # Test Donchian_50
    upper = high.rolling(50).max()
    lower = low.rolling(50).min()
    entries = ((close > upper.shift(1)) & (close.shift(1) <= upper.shift(2))).fillna(False)
    exits = ((close < lower.shift(1)) & (close.shift(1) >= lower.shift(2))).fillna(False)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.0007, freq='1H')
    stats = pf.stats()
    if stats['Total Trades'] >= 5:
        all_results.append({'period': period['name'], 'strategy': 'Donchian_50',
                           'return': stats['Total Return [%]'], 'trades': stats['Total Trades'],
                           'wr': stats['Win Rate [%]'], 'pf': stats['Profit Factor']})
        print(f'  Donchian_50:        {stats["Total Return [%]"]:>7.1f}% | {stats["Total Trades"]:>3.0f} trades | {stats["Win Rate [%]"]:>5.1f}% WR')

    # Test BB_30_1.5
    bbands = vbt.BBANDS.run(close, 30, 1.5)
    entries = (close <= bbands.lower).fillna(False)
    exits = (close >= bbands.upper).fillna(False)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.0007, freq='1H')
    stats = pf.stats()
    if stats['Total Trades'] >= 5:
        all_results.append({'period': period['name'], 'strategy': 'BB_30_1.5',
                           'return': stats['Total Return [%]'], 'trades': stats['Total Trades'],
                           'wr': stats['Win Rate [%]'], 'pf': stats['Profit Factor']})
        print(f'  BB_30_1.5:          {stats["Total Return [%]"]:>7.1f}% | {stats["Total Trades"]:>3.0f} trades | {stats["Win Rate [%]"]:>5.1f}% WR')

# Summary
print('\n' + '='*80)
print('SUMMARY - PERFORMANCE BY STRATEGY')
print('='*80)

df = pd.DataFrame(all_results)
for strat in df['strategy'].unique():
    data = df[df['strategy'] == strat]
    print(f'\n{strat}:')
    print(f'  Avg Return: {data["return"].mean():.1f}%')
    print(f'  Best: {data["return"].max():.1f}% | Worst: {data["return"].min():.1f}%')
    print(f'  Profitable: {len(data[data["return"] > 0])}/{len(data)} periods ({len(data[data["return"] > 0])/len(data)*100:.0f}%)')
    print(f'  Avg Win Rate: {data["wr"].mean():.1f}%')

print('\n' + '='*80)
print('WINNER:')
avg_returns = df.groupby('strategy')['return'].mean().sort_values(ascending=False)
winner = avg_returns.index[0]
winner_data = df[df['strategy'] == winner]
print(f'{winner} - Avg Return: {avg_returns.iloc[0]:.1f}%')
print(f'  Profitable in {len(winner_data[winner_data["return"] > 0])}/{len(winner_data)} periods')

df.to_csv('validation_results.csv', index=False)
print(f'\n[OK] Exported to validation_results.csv')

mt5.shutdown()
