"""
Reverse-Engineer Trading Strategy from MT5 History
Analyze actual trades to discover patterns and rules
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

def analyze_trades():
    if not mt5.initialize():
        print('MT5 failed')
        return

    print('='*80)
    print('REVERSE-ENGINEERING YOUR TRADING STRATEGY')
    print('='*80)

    # Get last 12 months of deals
    from_date = datetime.now() - timedelta(days=365)
    to_date = datetime.now()

    deals = mt5.history_deals_get(from_date, to_date)
    if not deals:
        print('No deals found')
        mt5.shutdown()
        return

    # Convert to list of dicts for easier analysis
    all_deals = []
    for d in deals:
        all_deals.append({
            'time': datetime.fromtimestamp(d.time),
            'symbol': d.symbol,
            'type': 'BUY' if d.type == 0 else 'SELL',
            'volume': d.volume,
            'price': d.price,
            'profit': d.profit,
            'commission': d.commission,
            'swap': d.swap,
            'entry': d.entry,  # 0=In, 1=Out
            'position_id': d.position_id,
        })

    # Match entry and exit deals to reconstruct trades
    positions = defaultdict(list)
    for deal in all_deals:
        if deal['position_id'] > 0:
            positions[deal['position_id']].append(deal)

    # Build complete trades (entry + exit pairs)
    trades = []
    for pos_id, pos_deals in positions.items():
        if len(pos_deals) >= 2:
            # Sort by time
            pos_deals.sort(key=lambda x: x['time'])
            entry = pos_deals[0]
            exit_deal = pos_deals[-1]

            # Calculate hold time
            hold_time = (exit_deal['time'] - entry['time']).total_seconds() / 60  # minutes

            # Calculate pip movement
            if entry['symbol'] in ['GOLD', 'XAUUSD']:
                pip_size = 0.1  # Gold pips are $0.10
                pip_move = abs(exit_deal['price'] - entry['price']) / pip_size
            elif 'JPY' in entry['symbol']:
                pip_size = 0.01
                pip_move = abs(exit_deal['price'] - entry['price']) / pip_size
            else:
                pip_size = 0.0001
                pip_move = abs(exit_deal['price'] - entry['price']) / pip_size

            trades.append({
                'entry_time': entry['time'],
                'exit_time': exit_deal['time'],
                'symbol': entry['symbol'],
                'direction': entry['type'],
                'entry_price': entry['price'],
                'exit_price': exit_deal['price'],
                'volume': entry['volume'],
                'profit': exit_deal['profit'],
                'hold_minutes': hold_time,
                'pip_move': pip_move,
            })

    print(f'\nReconstructed {len(trades)} complete trades')

    # Analyze GOLD trades specifically (your best performer)
    gold_trades = [t for t in trades if t['symbol'] in ['GOLD', 'XAUUSD']]

    if not gold_trades:
        print('No Gold trades found')
        mt5.shutdown()
        return

    print(f'\n{"="*80}')
    print(f'GOLD STRATEGY ANALYSIS ({len(gold_trades)} trades)')
    print(f'{"="*80}')

    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(gold_trades)

    # Basic stats
    winners = df[df['profit'] > 0]
    losers = df[df['profit'] <= 0]

    print(f'\nPerformance:')
    print(f'  Win Rate: {len(winners)/len(df)*100:.1f}%')
    print(f'  Avg Win: ${winners["profit"].mean():.2f}')
    print(f'  Avg Loss: ${losers["profit"].mean():.2f}')
    print(f'  Profit Factor: {abs(winners["profit"].sum() / losers["profit"].sum()):.2f}')

    # Hold time analysis
    print(f'\nHold Time Analysis:')
    print(f'  Avg Hold Time: {df["hold_minutes"].mean():.1f} minutes ({df["hold_minutes"].mean()/60:.1f} hours)')
    print(f'  Median Hold Time: {df["hold_minutes"].median():.1f} minutes')
    print(f'  Min Hold Time: {df["hold_minutes"].min():.1f} minutes')
    print(f'  Max Hold Time: {df["hold_minutes"].max():.1f} minutes')

    # Classify by hold time
    scalps = df[df['hold_minutes'] < 30]  # Under 30 min
    intraday = df[(df['hold_minutes'] >= 30) & (df['hold_minutes'] < 240)]  # 30min - 4hr
    swing = df[df['hold_minutes'] >= 240]  # Over 4hr

    print(f'\nTrade Type Breakdown:')
    print(f'  Scalps (<30min): {len(scalps)} trades ({len(scalps)/len(df)*100:.1f}%)')
    print(f'  Intraday (30min-4hr): {len(intraday)} trades ({len(intraday)/len(df)*100:.1f}%)')
    print(f'  Swing (>4hr): {len(swing)} trades ({len(swing)/len(df)*100:.1f}%)')

    # Position sizing analysis
    print(f'\nPosition Sizing:')
    print(f'  Avg Size: {df["volume"].mean():.2f} lots')
    print(f'  Median Size: {df["volume"].median():.2f} lots')
    print(f'  Min Size: {df["volume"].min():.2f} lots')
    print(f'  Max Size: {df["volume"].max():.2f} lots')

    # Check if size correlates with conviction/setup quality
    big_positions = df[df['volume'] > df['volume'].median()]
    small_positions = df[df['volume'] <= df['volume'].median()]

    print(f'\n  Big positions (>{df["volume"].median():.2f} lots): {len(big_positions[big_positions["profit"]>0])/len(big_positions)*100:.1f}% WR')
    print(f'  Small positions (<={df["volume"].median():.2f} lots): {len(small_positions[small_positions["profit"]>0])/len(small_positions)*100:.1f}% WR')

    # Time of day analysis
    df['hour'] = df['entry_time'].dt.hour

    print(f'\nTime of Day Analysis:')
    for session, hours in [('Asian (0-7)', range(0,8)), ('London (8-12)', range(8,13)), ('NY (13-21)', range(13,22)), ('Late (22-23)', range(22,24))]:
        session_trades = df[df['hour'].isin(hours)]
        if len(session_trades) > 0:
            wr = len(session_trades[session_trades['profit']>0])/len(session_trades)*100
            print(f'  {session}: {len(session_trades)} trades, {wr:.1f}% WR, ${session_trades["profit"].sum():.0f} total')

    # Day of week analysis
    df['weekday'] = df['entry_time'].dt.day_name()

    print(f'\nDay of Week Analysis:')
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        day_trades = df[df['weekday'] == day]
        if len(day_trades) > 0:
            wr = len(day_trades[day_trades['profit']>0])/len(day_trades)*100
            print(f'  {day}: {len(day_trades)} trades, {wr:.1f}% WR')

    # Pip target/stop analysis
    print(f'\nPip Movement Analysis:')
    print(f'  Avg Pip Move: {df["pip_move"].mean():.1f} pips')
    print(f'  Median Pip Move: {df["pip_move"].median():.1f} pips')

    win_pips = winners['pip_move'].mean()
    loss_pips = losers['pip_move'].mean()
    print(f'  Avg Win Size: {win_pips:.1f} pips')
    print(f'  Avg Loss Size: {loss_pips:.1f} pips')
    print(f'  Risk:Reward Ratio: 1:{win_pips/loss_pips:.2f}')

    # Look for patterns in recent trades
    print(f'\n{"="*80}')
    print('RECENT GOLD TRADES (Last 20)')
    print(f'{"="*80}')

    recent = df.tail(20).sort_values('entry_time', ascending=False)
    print(f'\n{"Date":<20} {"Dir":<6} {"Size":<8} {"Hold(min)":<12} {"Pips":<10} {"P&L":<12} {"Result"}')
    print('-'*80)

    for _, t in recent.iterrows():
        result = 'WIN' if t['profit'] > 0 else 'LOSS'
        date_str = t['entry_time'].strftime('%Y-%m-%d %H:%M')
        print(f"{date_str:<20} {t['direction']:<6} {t['volume']:<8.2f} {t['hold_minutes']:<12.1f} {t['pip_move']:<10.1f} ${t['profit']:<11.2f} {result}")

    # Export to CSV for deeper analysis
    csv_file = 'my_gold_trades_analysis.csv'
    df.to_csv(csv_file, index=False)
    print(f'\n[OK] Exported {len(df)} Gold trades to {csv_file}')

    # Try to identify the strategy type
    print(f'\n{"="*80}')
    print('STRATEGY TYPE IDENTIFICATION')
    print(f'{"="*80}')

    avg_hold = df['hold_minutes'].mean()
    trades_per_day = len(df) / 365

    print(f'\nBased on the data:')
    print(f'  Trades per day: {trades_per_day:.1f}')
    print(f'  Avg hold time: {avg_hold:.0f} minutes ({avg_hold/60:.1f} hours)')
    print(f'  Position sizing: {df["volume"].mean():.2f} lots avg')

    if avg_hold < 30:
        strategy_type = 'SCALPING'
        print(f'\n  Strategy Type: {strategy_type}')
        print(f'  Description: Quick 5-20 pip moves, very short hold times')
        print(f'  Likely using: Price action, order flow, support/resistance')
    elif avg_hold < 240:
        strategy_type = 'INTRADAY/DAY TRADING'
        print(f'\n  Strategy Type: {strategy_type}')
        print(f'  Description: Catching intraday swings, 1-4 hour holds')
        print(f'  Likely using: Breakouts, trend continuation, session opens')
    else:
        strategy_type = 'SWING TRADING'
        print(f'\n  Strategy Type: {strategy_type}')
        print(f'  Description: Multi-day position holds')
        print(f'  Likely using: Trend following, macro positioning')

    # Get current market data to see what's happening NOW
    print(f'\n{"="*80}')
    print('CURRENT MARKET CONDITIONS (for Gold)')
    print(f'{"="*80}')

    # Get recent gold bars
    gold_rates = mt5.copy_rates_from_pos('GOLD', mt5.TIMEFRAME_M15, 0, 100)
    if gold_rates is not None and len(gold_rates) > 0:
        df_rates = pd.DataFrame(gold_rates)
        current_price = df_rates['close'].iloc[-1]

        # Calculate simple indicators to see what you might be watching
        df_rates['ema_9'] = df_rates['close'].ewm(span=9).mean()
        df_rates['ema_21'] = df_rates['close'].ewm(span=21).mean()
        df_rates['ema_50'] = df_rates['close'].ewm(span=50).mean()

        # Support/resistance levels (recent highs/lows)
        recent_high = df_rates['high'].tail(20).max()
        recent_low = df_rates['low'].tail(20).min()

        print(f'\nCurrent Gold Price: ${current_price:.2f}')
        print(f'Recent High (20 bars): ${recent_high:.2f} (+{recent_high-current_price:.2f})')
        print(f'Recent Low (20 bars): ${recent_low:.2f} ({recent_low-current_price:.2f})')
        print(f'\nEMAs on M15:')
        print(f'  EMA 9: ${df_rates["ema_9"].iloc[-1]:.2f}')
        print(f'  EMA 21: ${df_rates["ema_21"].iloc[-1]:.2f}')
        print(f'  EMA 50: ${df_rates["ema_50"].iloc[-1]:.2f}')

        # Check trend
        if df_rates['ema_9'].iloc[-1] > df_rates['ema_21'].iloc[-1] > df_rates['ema_50'].iloc[-1]:
            print(f'\n  Trend: BULLISH (all EMAs aligned)')
        elif df_rates['ema_9'].iloc[-1] < df_rates['ema_21'].iloc[-1] < df_rates['ema_50'].iloc[-1]:
            print(f'\n  Trend: BEARISH (all EMAs aligned)')
        else:
            print(f'\n  Trend: CHOPPY/RANGING (EMAs mixed)')

    mt5.shutdown()

    print(f'\n{"="*80}')
    print('NEXT STEPS')
    print(f'{"="*80}')
    print(f'\n1. Review the analysis above')
    print(f'2. Check my_gold_trades_analysis.csv for full data')
    print(f'3. Tell me what sounds right/wrong based on your actual approach')
    print(f'4. I will build a backtest based on discovered patterns')

if __name__ == '__main__':
    analyze_trades()
