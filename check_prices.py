import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd

mt5.initialize()

end = datetime.now()
start = end - timedelta(days=365)

rates = mt5.copy_rates_range('GOLD', mt5.TIMEFRAME_H1, start, end)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

print(f'Total bars: {len(df)}')
print(f'\nFirst 5 bars:')
print(df[['time', 'open', 'high', 'low', 'close']].head())
print(f'\nLast 5 bars:')
print(df[['time', 'open', 'high', 'low', 'close']].tail())
print(f'\nPrice range: ${df["close"].min():.2f} - ${df["close"].max():.2f}')
print(f'Current price: ${df["close"].iloc[-1]:.2f}')
print(f'\nSample trades at different price points:')
print(df[['time', 'close']].iloc[::1000])

mt5.shutdown()
