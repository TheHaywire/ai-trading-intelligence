"""
COMMAND: status
Shows account status, positions, and P&L
"""

import sys
sys.path.append('..')

from core.mt5_service import *
from core.email_service import send_simple_update

def run():
    if not init_mt5():
        return

    account = get_account_info()
    positions = get_positions()

    print("="*60)
    print("ACCOUNT STATUS")
    print("="*60)
    print(f"Balance:     ${account.balance:,.2f}")
    print(f"Equity:      ${account.equity:,.2f}")
    print(f"P&L:         ${account.profit:+,.2f}")
    print(f"Margin:      {account.margin_level:.2f}%")
    print(f"Positions:   {len(positions) if positions else 0}")

    if positions:
        print(f"\n{'='*60}")
        print("OPEN POSITIONS")
        print(f"{'='*60}")

        total_profit = 0
        for p in positions:
            direction = "LONG" if p.type == 0 else "SHORT"
            status = "[WIN]" if p.profit > 0 else "[LOSS]"
            print(f"{status} {p.symbol:10s} {direction:5s} | ${p.profit:+10,.2f}")
            total_profit += p.profit

        print(f"\nTotal P&L: ${total_profit:+,.2f}")

    shutdown_mt5()

if __name__ == "__main__":
    run()
