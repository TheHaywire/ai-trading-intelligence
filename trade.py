"""
TRADING COMMAND CENTER
Simple shortcuts to all trading functions

Usage:
  python trade.py summary          - Master Executive Summary (ONE powerful daily briefing!)
  python trade.py digest           - Complete daily quant digest (all metrics)
  python trade.py ai               - AI/ML Intelligence (predictions, win probability, trade quality)
  python trade.py signals          - Real-time signals & alerts (entry/exit signals, position monitoring)
  python trade.py risk             - Risk Management Dashboard (VaR, stress tests, heat maps)
  python trade.py perf             - Performance Attribution (which strategies/assets make money)
  python trade.py ta               - Technical Analysis report (patterns, levels, signals)
  python trade.py cards            - Symbol Decision Cards (AI-powered deep analysis per symbol)
  python trade.py status           - Show account status
  python trade.py scan             - Scan markets for opportunities
  python trade.py diagnostic       - Run full diagnostic
  python trade.py market           - Get market overview
  python trade.py close-losers     - Close all losing positions
  python trade.py close-all        - Close ALL positions
  python trade.py help             - Show this help
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def show_help():
    print(__doc__)

def run_command(command):
    if command == "help" or command == "-h" or command == "--help":
        show_help()

    elif command == "summary":
        print("[Running: Master Executive Summary]\n")
        from commands import executive_summary
        executive_summary.run()

    elif command == "digest":
        print("[Running: Complete Daily Digest]\n")
        from commands import daily_digest
        daily_digest.run()

    elif command == "ai":
        print("[Running: AI/ML Intelligence]\n")
        from commands import ai_intelligence
        ai_intelligence.run()

    elif command == "signals":
        print("[Running: Real-Time Signals & Alerts]\n")
        from commands import signals
        signals.run()

    elif command == "risk":
        print("[Running: Risk Management Dashboard]\n")
        from commands import risk
        risk.run()

    elif command == "perf":
        print("[Running: Performance Attribution Analysis]\n")
        from commands import performance_attribution
        performance_attribution.run()

    elif command == "ta":
        print("[Running: Technical Analysis Report]\n")
        from commands import ta_report
        ta_report.run()

    elif command == "cards":
        print("[Running: Symbol Decision Cards - AI-Powered Analysis]\n")
        from commands import symbol_cards
        symbol_cards.run()

    elif command == "status":
        print("[Running: Account Status]\n")
        from commands import status
        status.run()

    elif command == "scan":
        print("[Running: Smart Scanner]\n")
        os.system("python smart_scanner_trader.py")

    elif command == "diagnostic":
        print("[Running: Diagnostic]\n")
        os.system("python quant_diagnostic.py")

    elif command == "market":
        print("[Running: Market Overview]\n")
        os.system("python live_market_command_center.py")

    elif command == "close-losers":
        print("[Running: Close Losing Positions]\n")
        from commands import close_losers
        close_losers.run()

    elif command == "close-all":
        confirm = input("Are you sure you want to close ALL positions? (yes/no): ")
        if confirm.lower() == "yes":
            print("[Running: Close All Positions]\n")
            from commands import close_all
            close_all.run()
        else:
            print("Cancelled")

    elif command == "gold-analysis":
        print("[Running: Gold Reversal Analysis]\n")
        os.system("python gold_reversal_analysis.py")

    elif command == "ai-analysis":
        print("[Running: AI Deep Analysis]\n")
        os.system("python ai_deep_analysis.py")

    else:
        print(f"Unknown command: {command}")
        print("Run 'python trade.py help' to see all commands")

if __name__ == "__main__":
    print("="*70)
    print(" "*20 + "TRADING COMMAND CENTER")
    print("="*70)
    print()

    if len(sys.argv) < 2:
        show_help()
    else:
        command = sys.argv[1]
        run_command(command)
