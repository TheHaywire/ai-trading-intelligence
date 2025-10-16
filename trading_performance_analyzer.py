
"""
TRADING PERFORMANCE ANALYZER

Analyzes the historical performance of an MT5 trading account.
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import yaml
import os

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(script_dir, 'configs', 'example_if_100k.yaml')
ANALYSIS_PERIOD_DAYS = 90

def main():
    """Main function to connect, fetch, analyze, and report."""
    print("--- Trading Performance Analyzer --- ")
    # Load MT5 credentials
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        platform_config = config.get('platform', {})
        login = int(platform_config.get('login'))
        password = platform_config.get('password')
        server = platform_config.get('server')
    except Exception as e:
        print(f"[FATAL] Could not read MT5 config. Error: {e}")
        return

    # Connect to MT5
    if not mt5.initialize(login=login, password=password, server=server):
        print(f"[FATAL] MT5 initialization failed. Error: {mt5.last_error()}")
        return
    print(f"\n[SUCCESS] Connected to MT5 Account #{login}")

    # Fetch trade history
    from_date = datetime.now() - timedelta(days=ANALYSIS_PERIOD_DAYS)
    to_date = datetime.now()
    print(f"Fetching trade history from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}...")
    
    deals = mt5.history_deals_get(from_date, to_date)
    if deals is None or len(deals) == 0:
        print("\nNo trading history found for the specified period.")
        mt5.shutdown()
        return

    # Process deals into a DataFrame
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    # Filter out balance/credit operations
    df = df[df['entry'].isin([mt5.DEAL_ENTRY_IN, mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT])]
    print(f"Found {len(df)} deals to analyze.")

    # --- ANALYSIS --- #
    # Group deals by position to reconstruct trades
    trades = []
    for position_id, group in df.groupby('position_id'):
        entry_deals = group[group['entry'] == mt5.DEAL_ENTRY_IN]
        exit_deals = group[group['entry'] == mt5.DEAL_ENTRY_OUT]

        if entry_deals.empty or exit_deals.empty:
            continue # Skip positions that are not complete trades (e.g., still open)

        entry_deal = entry_deals.iloc[0]
        exit_deal = exit_deals.iloc[-1]
        
        trade = {
            'symbol': entry_deal['symbol'],
            'type': 'BUY' if entry_deal['type'] == mt5.DEAL_TYPE_BUY else 'SELL',
            'volume': entry_deal['volume'],
            'entry_time': entry_deal['time'],
            'exit_time': exit_deal['time'],
            'duration_minutes': (exit_deal['time'] - entry_deal['time']).total_seconds() / 60,
            'profit': group['profit'].sum(),
            'commission': group['commission'].sum(),
            'swap': group['swap'].sum(),
        }
        trades.append(trade)

    if not trades:
        print("\nCould not reconstruct any complete trades from the deal history.")
        mt5.shutdown()
        return

    trades_df = pd.DataFrame(trades)
    trades_df['net_profit'] = trades_df['profit'] + trades_df['commission'] + trades_df['swap']

    # --- REPORTING --- #
    print_report(trades_df)

    # Disconnect
    mt5.shutdown()
    print("\n[DONE] MT5 Disconnected.")

def print_report(df):
    """Prints the full performance report from the trades DataFrame."""
    total_trades = len(df)
    wins = df[df['net_profit'] > 0]
    losses = df[df['net_profit'] <= 0]
    
    # 1. Overall Performance Summary
    print("\n" + "="*50)
    print("          OVERALL PERFORMANCE SUMMARY")
    print("="*50)
    print(f"Total Trades Analyzed:      {total_trades}")
    print(f"Gross Profit:               ${wins['net_profit'].sum():,.2f}")
    print(f"Gross Loss:                 ${losses['net_profit'].sum():,.2f}")
    print(f"Net Profit:                 ${df['net_profit'].sum():,.2f}")
    profit_factor = wins['net_profit'].sum() / abs(losses['net_profit'].sum()) if losses['net_profit'].sum() != 0 else float('inf')
    print(f"Profit Factor:              {profit_factor:.2f}")
    print(f"Total Volume Traded (Lots): {df['volume'].sum():,.2f}")

    # 2. Trade Statistics
    print("\n" + "-"*50)
    print("                 TRADE STATISTICS")
    print("-"*50)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    print(f"Win Rate:                   {win_rate:.2f}%")
    avg_win = wins['net_profit'].mean() if len(wins) > 0 else 0
    avg_loss = losses['net_profit'].mean() if len(losses) > 0 else 0
    print(f"Average Winning Trade:      ${avg_win:,.2f}")
    print(f"Average Losing Trade:       ${avg_loss:,.2f}")
    reward_risk_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
    print(f"Reward/Risk Ratio:          {reward_risk_ratio:.2f}:1")
    print(f"Largest Winning Trade:      ${df['net_profit'].max():,.2f}")
    print(f"Largest Losing Trade:       ${df['net_profit'].min():,.2f}")

    # 3. Holding Time Analysis
    print("\n" + "-"*50)
    print("               HOLDING TIME ANALYSIS")
    print("-"*50)
    print(f"Average Trade Duration:       {df['duration_minutes'].mean():.2f} minutes")
    print(f"Median Trade Duration:        {df['duration_minutes'].median():.2f} minutes")
    print(f"Longest Trade:              {df['duration_minutes'].max() / 60:.2f} hours")
    print(f"Shortest Trade:             {df['duration_minutes'].min():.2f} minutes")

    # 4. Performance by Symbol
    print("\n" + "-"*50)
    print("               PERFORMANCE BY SYMBOL")
    print("-"*50)
    by_symbol = df.groupby('symbol')['net_profit'].agg(['sum', 'count', 'mean'])
    by_symbol.columns = ['Net Profit', 'Trade Count', 'Avg Profit/Trade']
    print(by_symbol.sort_values(by='Net Profit', ascending=False).to_string(formatters={'Net Profit': '${:,.2f}'.format, 'Avg Profit/Trade': '${:,.2f}'.format}))

    # 5. Performance by Direction
    print("\n" + "-"*50)
    print("              PERFORMANCE BY DIRECTION")
    print("-"*50)
    by_direction = df.groupby('type')['net_profit'].agg(['sum', 'count', 'mean'])
    by_direction.columns = ['Net Profit', 'Trade Count', 'Avg Profit/Trade']
    print(by_direction.sort_values(by='Net Profit', ascending=False).to_string(formatters={'Net Profit': '${:,.2f}'.format, 'Avg Profit/Trade': '${:,.2f}'.format}))
    print("="*50)

if __name__ == "__main__":
    main()
