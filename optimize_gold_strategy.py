"""
ULTIMATE GOLD STRATEGY OPTIMIZATION
Based on reverse-engineered patterns from actual $1.9M trading results

Will test thousands of combinations:
- Session filters (Asian/NY/London)
- Breakout strategies (previous high/low breaks)
- Trend continuation (EMA pullbacks)
- Support/resistance levels
- Momentum indicators
- Stop/target combinations
- Day of week filters

Expected to find strategies making $500k-$1M annually
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from multiprocessing import Pool, cpu_count
import itertools

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

logging.basicConfig(level=logging.ERROR)

# Import existing backtester
from src.engine.backtester import Backtester
from src.strategy.loader import Strategy, Signal, MarketState

import numpy as np


class GoldScalpingStrategy(Strategy):
    """
    Gold scalping strategy based on session timing + breakouts/momentum
    """

    def __init__(self, name: str = "GoldScalp", config: dict = None):
        default_config = {
            # Session filters
            'use_asian_session': True,
            'use_london_session': False,
            'use_ny_session': True,

            # Day of week filter
            'avoid_wednesday': False,
            'prefer_monday': False,

            # Entry type
            'entry_type': 'breakout',  # 'breakout', 'ema_pullback', 'momentum'

            # Breakout params
            'lookback_periods': 20,  # Bars to find high/low
            'breakout_buffer_pips': 2,  # Extra pips above high to confirm

            # EMA params (for trend confirmation)
            'use_ema_filter': False,
            'fast_ema': 9,
            'slow_ema': 21,

            # Momentum params
            'use_momentum': False,
            'momentum_lookback': 5,
            'momentum_threshold': 0.5,  # % move

            # Risk management
            'stop_pips': 75,  # Based on analysis
            'target_pips': 40,  # Based on analysis
            'use_atr_stops': False,
            'atr_stop_mult': 2.0,
            'atr_target_mult': 1.0,

            # Position sizing
            'base_risk_pct': 1.0,
            'enabled': True,
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def _get_session(self, timestamp: datetime) -> str:
        """Determine trading session (UTC based)"""
        hour = timestamp.hour

        # Asian: 0-7 UTC (best WR: 70.1%, $821k profit)
        if 0 <= hour < 8:
            return 'asian'
        # London: 8-12 UTC (WORST WR: 21.7%, -$41k loss)
        elif 8 <= hour < 13:
            return 'london'
        # NY: 13-21 UTC (best WR: 73.3%, $900k profit)
        elif 13 <= hour < 22:
            return 'ny'
        # Late: 22-23 UTC
        else:
            return 'late'

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate EMA"""
        if len(prices) < period:
            return prices[-1]

        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def _calculate_atr(self, bars: list, period: int = 14) -> float:
        """Calculate ATR"""
        if len(bars) < period + 1:
            return 0.0

        trs = []
        for i in range(len(bars) - period, len(bars)):
            high = bars[i]['high']
            low = bars[i]['low']
            prev_close = bars[i-1]['close']

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)

        return sum(trs) / len(trs)

    def analyze(self, state: MarketState) -> Signal | None:
        """Analyze market and generate signals"""

        # Use M15 data for scalping (since avg hold time is minutes)
        bars = state.bars_h1  # Will use whatever timeframe backtester provides
        if not bars or len(bars) < 100:
            return None

        current_bar = bars[-1]
        timestamp = state.timestamp

        # Session filter
        session = self._get_session(timestamp)

        allowed_sessions = []
        if self.config['use_asian_session']:
            allowed_sessions.append('asian')
        if self.config['use_london_session']:
            allowed_sessions.append('london')
        if self.config['use_ny_session']:
            allowed_sessions.append('ny')

        if session not in allowed_sessions:
            return None

        # Day of week filter
        day_of_week = timestamp.weekday()  # 0=Monday, 2=Wednesday

        if self.config['avoid_wednesday'] and day_of_week == 2:
            return None

        if self.config['prefer_monday'] and day_of_week != 0:
            # Only trade Mondays if this filter is on
            return None

        # Calculate indicators
        closes = np.array([b['close'] for b in bars])
        highs = np.array([b['high'] for b in bars])
        lows = np.array([b['low'] for b in bars])

        current_price = closes[-1]

        # EMA trend filter (optional)
        if self.config['use_ema_filter']:
            ema_fast = self._calculate_ema(closes, self.config['fast_ema'])
            ema_slow = self._calculate_ema(closes, self.config['slow_ema'])

            # Need aligned trend
            uptrend = ema_fast > ema_slow
            downtrend = ema_fast < ema_slow
        else:
            uptrend = True
            downtrend = True

        # Entry logic based on type
        direction = None

        if self.config['entry_type'] == 'breakout':
            # Find recent high/low
            lookback = min(self.config['lookback_periods'], len(bars) - 1)
            recent_high = max(highs[-lookback:-1])
            recent_low = min(lows[-lookback:-1])

            buffer = self.config['breakout_buffer_pips'] * 0.1  # Gold pip = $0.10

            # Bullish breakout
            if current_price > recent_high + buffer and uptrend:
                direction = 'long'

            # Bearish breakout
            elif current_price < recent_low - buffer and downtrend:
                direction = 'short'

        elif self.config['entry_type'] == 'ema_pullback':
            # Wait for pullback to EMA in trending market
            if self.config['use_ema_filter']:
                ema_fast = self._calculate_ema(closes, self.config['fast_ema'])
                ema_slow = self._calculate_ema(closes, self.config['slow_ema'])

                # Price near fast EMA in uptrend
                if ema_fast > ema_slow:
                    distance_pct = abs(current_price - ema_fast) / current_price
                    if distance_pct < 0.002:  # Within 0.2%
                        direction = 'long'

                # Price near fast EMA in downtrend
                elif ema_fast < ema_slow:
                    distance_pct = abs(current_price - ema_fast) / current_price
                    if distance_pct < 0.002:
                        direction = 'short'

        elif self.config['entry_type'] == 'momentum':
            # Strong momentum continuation
            lookback = self.config['momentum_lookback']
            if len(closes) > lookback:
                price_change_pct = (closes[-1] - closes[-lookback]) / closes[-lookback] * 100

                threshold = self.config['momentum_threshold']

                if price_change_pct > threshold and uptrend:
                    direction = 'long'
                elif price_change_pct < -threshold and downtrend:
                    direction = 'short'

        if not direction:
            return None

        # Calculate stops and targets
        if self.config['use_atr_stops']:
            atr = self._calculate_atr(bars)
            if atr == 0:
                return None

            stop_distance = atr * self.config['atr_stop_mult']
            target_distance = atr * self.config['atr_target_mult']
        else:
            # Fixed pip stops
            stop_distance = self.config['stop_pips'] * 0.1
            target_distance = self.config['target_pips'] * 0.1

        from src.core.broker_mt5 import OrderType

        if direction == 'long':
            stop_loss = current_price - stop_distance
            take_profit = current_price + target_distance
            order_type = OrderType.BUY
        else:
            stop_loss = current_price + stop_distance
            take_profit = current_price - target_distance
            order_type = OrderType.SELL

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=order_type,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason=f"Gold {self.config['entry_type']} {session}",
            confidence=0.7,
            metadata={'session': session, 'entry_type': self.config['entry_type']}
        )


def test_config(params):
    """Test single configuration"""
    config, symbol, start, end = params

    try:
        if not mt5.initialize():
            return None

        strategy = GoldScalpingStrategy(config=config)
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000.0,
            risk_per_trade_pct=1.0,
            spread_pips=2.0,  # Gold spread typically wider
            commission_per_lot=7.0
        )

        metrics = backtester.run(symbol, "H1", start, end)

        mt5.shutdown()

        if metrics and metrics.total_trades >= 10:
            return {
                'config': config,
                'symbol': symbol,
                'trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'pnl': metrics.total_pnl,
                'pnl_pct': metrics.total_pnl_pct,
                'expectancy': metrics.expectancy,
                'profit_factor': metrics.profit_factor,
                'max_dd': metrics.max_drawdown_pct,
                'sharpe': metrics.sharpe_ratio,
            }
    except Exception as e:
        pass

    return None


def generate_configs():
    """Generate all parameter combinations for Gold strategy"""

    # Session combinations (based on analysis)
    session_combos = [
        {'name': 'Asian+NY', 'use_asian_session': True, 'use_london_session': False, 'use_ny_session': True},
        {'name': 'Asian Only', 'use_asian_session': True, 'use_london_session': False, 'use_ny_session': False},
        {'name': 'NY Only', 'use_asian_session': False, 'use_london_session': False, 'use_ny_session': True},
        {'name': 'All Sessions', 'use_asian_session': True, 'use_london_session': True, 'use_ny_session': True},
    ]

    # Entry types
    entry_types = ['breakout', 'ema_pullback', 'momentum']

    # Breakout lookback periods
    lookback_periods = [10, 20, 30, 50]

    # EMA combinations
    ema_combos = [
        (9, 21),
        (12, 26),
        (20, 50),
        (25, 55),
    ]

    # Stop/Target combinations (based on discovered 75:40 ratio)
    stop_target_pairs = [
        (50, 30),   # Tighter
        (75, 40),   # Discovered from data
        (100, 50),  # Wider
        (75, 60),   # Better R:R
        (100, 100), # 1:1 R:R
    ]

    # Day filters
    day_filters = [
        {'name': 'All Days', 'avoid_wednesday': False, 'prefer_monday': False},
        {'name': 'Avoid Wed', 'avoid_wednesday': True, 'prefer_monday': False},
        {'name': 'Monday Only', 'avoid_wednesday': False, 'prefer_monday': True},
    ]

    configs = []

    # Generate combinations
    for session, entry_type, lookback, ema_pair, st_pair, day_filter in itertools.product(
        session_combos, entry_types, lookback_periods, ema_combos, stop_target_pairs, day_filters
    ):
        config = {
            **session,
            'entry_type': entry_type,
            'lookback_periods': lookback,
            'fast_ema': ema_pair[0],
            'slow_ema': ema_pair[1],
            'use_ema_filter': True if entry_type in ['ema_pullback', 'momentum'] else False,
            'stop_pips': st_pair[0],
            'target_pips': st_pair[1],
            **{k: v for k, v in day_filter.items() if k != 'name'}
        }

        # Build name
        name_parts = [
            session['name'],
            entry_type.upper(),
            f"L{lookback}",
            f"EMA{ema_pair[0]}/{ema_pair[1]}",
            f"SL{st_pair[0]}:TP{st_pair[1]}",
            day_filter['name']
        ]

        config['_name'] = ' | '.join(name_parts)
        configs.append(config)

    return configs


def main():
    print('='*80)
    print('ULTIMATE GOLD STRATEGY OPTIMIZATION')
    print('='*80)
    print('\nBased on your actual $1.9M trading results:')
    print('  - 4,068 Gold trades analyzed')
    print('  - 69.9% win rate discovered')
    print('  - Asian/NY session dominance identified')
    print('  - 11 trades/day frequency')
    print()
    print('Now testing thousands of variations to find the best automated version...')

    # Generate configs
    all_configs = generate_configs()
    print(f'\nGenerated {len(all_configs)} unique strategy configurations')

    # Test period
    end = datetime.now()
    start_12m = end - timedelta(days=365)

    # Test on Gold only (your main edge)
    symbol = 'GOLD'

    print(f'\nPreparing {len(all_configs)} tests on {symbol}...')
    print(f'Using {cpu_count()} CPU cores for parallel execution')

    test_params = [(config, symbol, start_12m, end) for config in all_configs]

    print(f'\nRunning optimization... (this will take 30-60 minutes)')
    print('Progress: ', end='', flush=True)

    # Run in parallel
    results = []
    chunk_size = 50

    with Pool(processes=cpu_count()) as pool:
        for i, result in enumerate(pool.imap_unordered(test_config, test_params, chunksize=10)):
            if result:
                results.append(result)

            if i % chunk_size == 0:
                progress = (i / len(test_params)) * 100
                print(f'{progress:.0f}%...', end='', flush=True)

    print(' DONE!\n')

    print(f'Completed {len(test_params)} tests')
    print(f'Valid results: {len(results)}')

    if not results:
        print('\nNo valid results. Check MT5 connection.')
        return

    # Sort by P&L
    results.sort(key=lambda x: x['pnl'], reverse=True)

    print('\n' + '='*80)
    print('TOP 20 GOLD STRATEGIES - Ranked by P&L')
    print('='*80)

    print(f"\n{'#':<4} {'Strategy':<80} {'Trades':<8} {'P&L':<12} {'WR':<6} {'PF':<6}")
    print('-'*130)

    for i, r in enumerate(results[:20], 1):
        print(f"{i:<4} {r['config']['_name']:<80} {r['trades']:<8} "
              f"${r['pnl']:>9.0f}  {r['win_rate']:>5.0%}  {r['profit_factor']:<6.2f}")

    # Compare to actual performance
    print('\n' + '='*80)
    print('COMPARISON: Algo vs Your Actual Trading')
    print('='*80)

    best = results[0]

    print(f'\nBest Algo Strategy:')
    print(f'  Config: {best["config"]["_name"]}')
    print(f'  P&L: ${best["pnl"]:,.0f} on $10k = {best["pnl_pct"]:.1f}%')
    print(f'  Trades: {best["trades"]}')
    print(f'  Win Rate: {best["win_rate"]:.1%}')
    print(f'  Profit Factor: {best["profit_factor"]:.2f}')

    print(f'\nYour Actual Trading (12 months):')
    print(f'  P&L: $1,912,644 (Gold only)')
    print(f'  Trades: 4,068')
    print(f'  Win Rate: 69.9%')
    print(f'  Profit Factor: 1.35')

    # Scale up the algo
    scale_factor = 245  # $2.45M / $10k
    scaled_pnl = best['pnl'] * scale_factor

    print(f'\nIf algo ran on your $2.45M account:')
    print(f'  Projected P&L: ${scaled_pnl:,.0f}')
    print(f'  vs Your actual: $1,912,644')
    print(f'  Algo would capture: {scaled_pnl/1912644*100:.1f}% of your manual performance')

    # Show the winning config
    print('\n' + '='*80)
    print('WINNING STRATEGY CONFIGURATION')
    print('='*80)

    print(f'\n{best["config"]["_name"]}')
    print('\nParameters:')
    for key, value in best['config'].items():
        if not key.startswith('_'):
            print(f'  {key}: {value}')

    print('\n' + '='*80)
    print('NEXT STEPS')
    print('='*80)
    print('\n1. Review the top strategies above')
    print('2. Pick the best 2-3 configurations')
    print('3. Validate on extended timeframe (24 months)')
    print('4. Paper trade for 1-2 weeks')
    print('5. If successful, run alongside your manual trading')
    print('\nThe algo will handle 50-70% of setups, you can focus on the best opportunities.')


if __name__ == '__main__':
    main()
