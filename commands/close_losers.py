"""
COMMAND: close_losers
Closes all losing positions
"""

import sys
sys.path.append('..')

from core.mt5_service import *
from core.email_service import send_simple_update

def run():
    if not init_mt5():
        return

    print("="*60)
    print("CLOSING ALL LOSING POSITIONS")
    print("="*60)

    result = close_losing_positions()

    if result['success']:
        print(f"\n[SUCCESS] Closed {result['count']} losing positions")
        print(f"Total P&L: ${result['total_pnl']:+,.2f}")

        # Send email notification
        message = f"Closed {result['count']} losing positions\nTotal P&L: ${result['total_pnl']:+,.2f}"
        send_simple_update("Positions Closed", message)
    else:
        print(f"\n[PARTIAL] Closed {result['count']} positions")
        print(f"Errors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"  - {error}")

    shutdown_mt5()

if __name__ == "__main__":
    run()
