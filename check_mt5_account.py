"""
Check MT5 Account Performance
Shows actual manual trading results vs algo backtest results
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta

def main():
    if not mt5.initialize():
        print('MT5 initialization failed')
        print(f'Error: {mt5.last_error()}')
        return

    # Get account info
    account_info = mt5.account_info()
    if account_info:
        print('='*80)
        print('MT5 ACCOUNT OVERVIEW')
        print('='*80)
        print(f'Account ID: {account_info.login}')
        print(f'Server: {account_info.server}')
        print(f'Currency: {account_info.currency}')
        print(f'Balance: ${account_info.balance:,.2f}')
        print(f'Equity: ${account_info.equity:,.2f}')
        print(f'Margin Used: ${account_info.margin:,.2f}')
        print(f'Free Margin: ${account_info.margin_free:,.2f}')
        print(f'Floating P&L: ${account_info.profit:,.2f}')
        print(f'Leverage: 1:{account_info.leverage}')
        print()

    # Get historical deals (closed trades)
    from_date = datetime.now() - timedelta(days=365)
    to_date = datetime.now()

    print('='*80)
    print('TRADING HISTORY - Last 12 Months')
    print('='*80)

    deals = mt5.history_deals_get(from_date, to_date)
    if deals and len(deals) > 0:
        print(f'Total deal records: {len(deals)}')

        # Filter only actual trade deals (exclude deposits/withdrawals/balance operations)
        trades = [d for d in deals if d.entry == 1]  # entry=1 means Out (closed position)

        if trades:
            total_profit = sum(d.profit for d in trades)
            total_commission = sum(d.commission for d in trades)
            total_swap = sum(d.swap for d in trades)

            winners = [d for d in trades if d.profit > 0]
            losers = [d for d in trades if d.profit < 0]

            print(f'\nClosed Trades: {len(trades)}')
            print(f'Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)')
            print(f'Losers: {len(losers)} ({len(losers)/len(trades)*100:.1f}%)')
            print(f'\nGross P&L: ${total_profit:,.2f}')
            print(f'Commission: ${total_commission:,.2f}')
            print(f'Swap: ${total_swap:,.2f}')
            print(f'Net P&L: ${total_profit + total_commission + total_swap:,.2f}')

            if winners:
                avg_win = sum(d.profit for d in winners)/len(winners)
                print(f'\nAvg Win: ${avg_win:,.2f}')

            if losers:
                avg_loss = sum(d.profit for d in losers)/len(losers)
                print(f'Avg Loss: ${avg_loss:,.2f}')

                if avg_loss != 0:
                    profit_factor = abs(sum(d.profit for d in winners) / sum(d.profit for d in losers))
                    print(f'Profit Factor: {profit_factor:.2f}')

            # Show breakdown by symbol
            print('\n' + '='*80)
            print('BREAKDOWN BY SYMBOL')
            print('='*80)

            symbols = {}
            for d in trades:
                if d.symbol not in symbols:
                    symbols[d.symbol] = {'trades': 0, 'profit': 0, 'wins': 0}
                symbols[d.symbol]['trades'] += 1
                symbols[d.symbol]['profit'] += d.profit
                if d.profit > 0:
                    symbols[d.symbol]['wins'] += 1

            print(f"\n{'Symbol':<15} {'Trades':<10} {'Win Rate':<12} {'P&L':<15}")
            print('-'*60)
            for symbol, data in sorted(symbols.items(), key=lambda x: x[1]['profit'], reverse=True):
                wr = data['wins']/data['trades']*100 if data['trades'] > 0 else 0
                print(f"{symbol:<15} {data['trades']:<10} {wr:>5.1f}%      ${data['profit']:>10,.2f}")

            # Show last 10 trades
            print('\n' + '='*80)
            print('LAST 10 CLOSED TRADES')
            print('='*80)
            print(f"\n{'Date':<20} {'Symbol':<12} {'Volume':<10} {'P&L':<12} {'Result':<8}")
            print('-'*70)

            recent_trades = sorted(trades, key=lambda x: x.time, reverse=True)[:10]
            for d in recent_trades:
                trade_date = datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M')
                result = 'WIN' if d.profit > 0 else 'LOSS'
                print(f"{trade_date:<20} {d.symbol:<12} {d.volume:<10.2f} ${d.profit:>9.2f} {result:<8}")
        else:
            print('No closed trades found (only balance operations)')
    else:
        print('No deal history found')

    # Get open positions
    positions = mt5.positions_get()
    if positions and len(positions) > 0:
        print('\n' + '='*80)
        print(f'OPEN POSITIONS ({len(positions)})')
        print('='*80)
        print(f"\n{'Symbol':<12} {'Type':<6} {'Volume':<10} {'Entry':<12} {'Current P&L':<15}")
        print('-'*70)

        total_open_pnl = 0
        for p in positions:
            trade_type = "BUY" if p.type == 0 else "SELL"
            print(f"{p.symbol:<12} {trade_type:<6} {p.volume:<10.2f} {p.price_open:<12.5f} ${p.profit:>12,.2f}")
            total_open_pnl += p.profit

        print('-'*70)
        print(f"{'TOTAL':<12} {'':6} {'':10} {'':12} ${total_open_pnl:>12,.2f}")
    else:
        print('\n' + '='*80)
        print('No open positions')
        print('='*80)

    # Compare with algo results
    print('\n' + '='*80)
    print('MANUAL vs ALGO COMPARISON')
    print('='*80)
    print('\nAlgo Strategy (25/55 EMA + NY Session):')
    print('  EURUSD 12m: $305 (9 trades, 55.6% WR)')
    print('  GBPUSD 12m: $311 (14 trades, 50% WR)')
    print('  Combined: $616 on $10k = 6.1% return')
    print('\nYour Manual Trading (see above for actual results)')
    print('  → Compare your total P&L, win rate, and trade count')
    print('  → Which approach is more profitable for you?')

    mt5.shutdown()
    print('\n' + '='*80)
    print('ANALYSIS COMPLETE')
    print('='*80)


if __name__ == "__main__":
    main()
