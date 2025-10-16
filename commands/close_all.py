"""
COMMAND: close_all
Closes ALL positions (winners and losers)
"""

import sys
sys.path.append('..')

from core.mt5_service import *
from core.email_service import send_simple_update

def run():
    if not init_mt5():
        return

    print("="*60)
    print("CLOSING ALL POSITIONS")
    print("="*60)

    result = close_all_positions()

    if result['success']:
        print(f"\n[SUCCESS] Closed {result['count']} positions")
        print(f"Total P&L: ${result['total_pnl']:+,.2f}")

        # Send email notification
        message = f"Closed {result['count']} positions\nTotal P&L: ${result['total_pnl']:+,.2f}"
        send_simple_update("All Positions Closed", message)
    else:
        print(f"\n[PARTIAL] Closed {result['count']} positions")
        print(f"Errors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"  - {error}")

    shutdown_mt5()

if __name__ == "__main__":
    run()
