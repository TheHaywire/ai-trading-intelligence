"""
PERFORMANCE TRACKER - Daily Trade Review & Analytics
Tracks trade performance, win rates, and provides detailed analysis
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

class PerformanceTracker:
    """Track and analyze trading performance"""

    def __init__(self, log_file: str = "trades_log.json"):
        self.log_file = log_file
        self.trades = self._load_trades()

    def _load_trades(self) -> List[Dict]:
        """Load trades from log file"""
        if not os.path.exists(self.log_file):
            return []

        try:
            with open(self.log_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading trades: {e}")
            return []

    def _save_trades(self):
        """Save trades to log file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.trades, f, indent=2)
        except Exception as e:
            print(f"Error saving trades: {e}")

    def log_trade(self, trade: Dict):
        """Log a new trade"""
        trade['timestamp'] = datetime.now().isoformat()
        self.trades.append(trade)
        self._save_trades()

    def get_daily_performance(self, date: Optional[datetime] = None) -> Dict:
        """Get performance for a specific day"""
        if date is None:
            date = datetime.now()

        date_str = date.strftime('%Y-%m-%d')

        daily_trades = [t for t in self.trades
                       if t.get('timestamp', '').startswith(date_str)]

        if not daily_trades:
            return {
                'date': date_str,
                'total_trades': 0,
                'winners': 0,
                'losers': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }

        winners = [t for t in daily_trades if t.get('pnl', 0) > 0]
        losers = [t for t in daily_trades if t.get('pnl', 0) < 0]

        total_pnl = sum(t.get('pnl', 0) for t in daily_trades)
        avg_win = np.mean([t['pnl'] for t in winners]) if winners else 0
        avg_loss = np.mean([t['pnl'] for t in losers]) if losers else 0

        gross_profit = sum(t['pnl'] for t in winners)
        gross_loss = abs(sum(t['pnl'] for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            'date': date_str,
            'total_trades': len(daily_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(daily_trades) * 100 if daily_trades else 0,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'trades': daily_trades
        }

    def get_weekly_summary(self) -> Dict:
        """Get performance summary for the past week"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        weekly_trades = [t for t in self.trades
                        if start_date <= datetime.fromisoformat(t.get('timestamp', '')) <= end_date]

        if not weekly_trades:
            return {
                'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0
            }

        winners = [t for t in weekly_trades if t.get('pnl', 0) > 0]
        total_pnl = sum(t.get('pnl', 0) for t in weekly_trades)

        return {
            'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
            'total_trades': len(weekly_trades),
            'winners': len(winners),
            'losers': len(weekly_trades) - len(winners),
            'win_rate': len(winners) / len(weekly_trades) * 100 if weekly_trades else 0,
            'total_pnl': total_pnl,
            'best_trade': max([t.get('pnl', 0) for t in weekly_trades]) if weekly_trades else 0,
            'worst_trade': min([t.get('pnl', 0) for t in weekly_trades]) if weekly_trades else 0
        }

    def analyze_strategy_performance(self) -> Dict:
        """Analyze performance by strategy type"""
        if not self.trades:
            return {}

        strategies = {}
        for trade in self.trades:
            strategy = trade.get('strategy', 'Unknown')
            if strategy not in strategies:
                strategies[strategy] = {
                    'trades': [],
                    'winners': 0,
                    'total_pnl': 0
                }

            strategies[strategy]['trades'].append(trade)
            if trade.get('pnl', 0) > 0:
                strategies[strategy]['winners'] += 1
            strategies[strategy]['total_pnl'] += trade.get('pnl', 0)

        # Calculate metrics for each strategy
        for strategy, data in strategies.items():
            total = len(data['trades'])
            data['win_rate'] = (data['winners'] / total * 100) if total > 0 else 0
            data['avg_pnl'] = data['total_pnl'] / total if total > 0 else 0
            data['total_trades'] = total

        return strategies

    def generate_html_summary(self) -> str:
        """Generate HTML summary for yesterday's trades"""
        yesterday = datetime.now() - timedelta(days=1)
        perf = self.get_daily_performance(yesterday)

        if perf['total_trades'] == 0:
            return f"""
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1e3c72; margin-bottom: 15px;">📊 Yesterday's Performance Review</h3>
                <p style="color: #666;">No trades were executed on {perf['date']}.</p>
            </div>
"""

        pnl_color = '#10b981' if perf['total_pnl'] > 0 else '#ef4444'

        html = f"""
        <div style="background: #f8f9fa; padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 5px solid {pnl_color};">
            <h3 style="color: #1e3c72; margin-bottom: 20px;">📊 Yesterday's Performance Review ({perf['date']})</h3>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #666; text-transform: uppercase; margin-bottom: 5px;">Total Trades</div>
                    <div style="font-size: 24px; font-weight: 700; color: #1e3c72;">{perf['total_trades']}</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #666; text-transform: uppercase; margin-bottom: 5px;">Win Rate</div>
                    <div style="font-size: 24px; font-weight: 700; color: {'#10b981' if perf['win_rate'] >= 50 else '#ef4444'};">{perf['win_rate']:.1f}%</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #666; text-transform: uppercase; margin-bottom: 5px;">Total P&L</div>
                    <div style="font-size: 24px; font-weight: 700; color: {pnl_color};">${perf['total_pnl']:+.2f}</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #666; text-transform: uppercase; margin-bottom: 5px;">Profit Factor</div>
                    <div style="font-size: 24px; font-weight: 700; color: #1e3c72;">{perf['profit_factor']:.2f}</div>
                </div>
            </div>

            <div style="background: white; padding: 15px; border-radius: 8px;">
                <h4 style="color: #1e3c72; margin-bottom: 10px;">Trade Breakdown:</h4>
                <ul style="margin-left: 20px; color: #333;">
                    <li>Winners: {perf['winners']} (Avg: ${perf['avg_win']:+.2f})</li>
                    <li>Losers: {perf['losers']} (Avg: ${perf['avg_loss']:+.2f})</li>
                </ul>
            </div>

            <div style="margin-top: 15px; padding: 15px; background: #e7f3ff; border-radius: 8px;">
                <strong style="color: #1565C0;">Lessons Learned:</strong>
                <p style="color: #333; margin-top: 8px;">
"""

        # Add insights
        if perf['win_rate'] >= 60:
            html += "Excellent win rate! Continue following your trading plan with discipline."
        elif perf['win_rate'] >= 50:
            html += "Solid performance. Focus on maintaining consistency and risk management."
        else:
            html += "Win rate below target. Review losing trades for pattern recognition and strategy adjustments."

        if perf['profit_factor'] >= 2:
            html += " Strong profit factor indicates good risk/reward management."
        elif perf['profit_factor'] >= 1:
            html += " Profit factor is positive but could be improved with better trade selection."
        else:
            html += " Profit factor needs improvement. Consider tighter stop losses or better entry timing."

        html += """
                </p>
            </div>
        </div>
"""

        return html


def demo_performance_tracking():
    """Demo performance tracking with sample data"""
    tracker = PerformanceTracker()

    # Sample trades for demo
    sample_trades = [
        {
            'symbol': 'EURUSD',
            'direction': 'LONG',
            'entry': 1.0850,
            'exit': 1.0880,
            'pnl': 300,
            'strategy': 'EMA Crossover',
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
        },
        {
            'symbol': 'GOLD',
            'direction': 'SHORT',
            'entry': 2050,
            'exit': 2045,
            'pnl': 500,
            'strategy': 'Donchian Breakout',
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
        },
        {
            'symbol': 'GBPUSD',
            'direction': 'LONG',
            'entry': 1.2650,
            'exit': 1.2640,
            'pnl': -100,
            'strategy': 'RSI Reversal',
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
        }
    ]

    # Log sample trades
    for trade in sample_trades:
        tracker.log_trade(trade)

    # Generate summary
    print("\n" + "="*80)
    print("PERFORMANCE TRACKING DEMO")
    print("="*80)

    yesterday_perf = tracker.get_daily_performance(datetime.now() - timedelta(days=1))
    print(f"\nYesterday's Performance:")
    print(f"  Total Trades: {yesterday_perf['total_trades']}")
    print(f"  Win Rate: {yesterday_perf['win_rate']:.1f}%")
    print(f"  Total P&L: ${yesterday_perf['total_pnl']:+.2f}")
    print(f"  Profit Factor: {yesterday_perf['profit_factor']:.2f}")

    html_summary = tracker.generate_html_summary()
    print("\n✅ HTML summary generated (will be included in daily report)")


if __name__ == "__main__":
    demo_performance_tracking()
