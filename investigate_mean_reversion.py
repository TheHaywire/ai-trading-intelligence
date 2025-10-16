"""Investigate the Mean Reversion $1.79M result"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '.')

from test_all_strategy_types import MeanReversionStrategy
from src.engine.backtester import Backtester

if not mt5.initialize():
    print('MT5 failed')
    exit()

strategy = MeanReversionStrategy()
backtester = Backtester(
    strategy=strategy,
    initial_capital=10000.0,
    risk_per_trade_pct=1.0,
    spread_pips=2.0,
    commission_per_lot=7.0
)

end = datetime.now()
start = end - timedelta(days=365)

metrics = backtester.run('GOLD', 'H1', start, end)

print(f'Total Trades: {metrics.total_trades}')
print(f'Win Rate: {metrics.win_rate:.1%}')
print(f'Total P&L: ${metrics.total_pnl:,.0f}')
print(f'Final Equity: ${metrics.final_equity:,.0f}')
print()

print('Last 10 trades:')
for i, t in enumerate(backtester.trades[-10:], 1):
    print(f'{i}. Vol: {t.volume:.2f} lots | Entry: ${t.entry_price:.2f} | P&L: ${t.pnl:,.0f}')

print()
print('Top 5 Winners:')
sorted_trades = sorted(backtester.trades, key=lambda x: x.pnl, reverse=True)
for i, t in enumerate(sorted_trades[:5], 1):
    print(f'{i}. Vol: {t.volume:.2f} lots | Entry: ${t.entry_price:.2f} → ${t.exit_price:.2f} | P&L: ${t.pnl:,.0f}')

print()
print('Top 5 Losers:')
for i, t in enumerate(sorted_trades[-5:], 1):
    print(f'{i}. Vol: {t.volume:.2f} lots | Entry: ${t.entry_price:.2f} → ${t.exit_price:.2f} | P&L: ${t.pnl:,.0f}')

mt5.shutdown()
