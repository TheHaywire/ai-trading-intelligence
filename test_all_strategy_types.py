"""
MULTI-STRATEGY TYPE TESTER
Test completely different strategy approaches (not just parameters)

Will test:
1. MACD + Bollinger Bands (78% WR from research)
2. RSI Divergence (catch reversals)
3. Stochastic Oscillator (overbought/oversold)
4. EMA Breakout (what we already found)
5. Mean Reversion (Bollinger squeeze)
6. Support/Resistance Bounce
7. Momentum (MACD histogram)
8. Volume-based entries

Expected runtime: 20-30 minutes
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from multiprocessing import Pool, cpu_count

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import numpy as np

logging.basicConfig(level=logging.ERROR)

from src.engine.backtester import Backtester
from src.strategy.loader import Strategy, Signal, MarketState
from src.core.broker_mt5 import OrderType


class MACDBollingerStrategy(Strategy):
    """MACD + Bollinger Bands - Research shows 78% WR"""

    def __init__(self, name: str = "MACD_BB", config: dict = None):
        default_config = {
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2,
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Signal | None:
        bars = state.bars_h1
        if not bars or len(bars) < 100:
            return None

        closes = np.array([b['close'] for b in bars])

        # Calculate MACD
        ema_fast = self._ema(closes, self.config['macd_fast'])
        ema_slow = self._ema(closes, self.config['macd_slow'])
        macd_line = ema_fast - ema_slow
        macd_signal = self._ema(macd_line, self.config['macd_signal'])

        # Calculate Bollinger Bands
        sma = np.mean(closes[-self.config['bb_period']:])
        std = np.std(closes[-self.config['bb_period']:])
        upper_band = sma + (std * self.config['bb_std'])
        lower_band = sma - (std * self.config['bb_std'])

        current_price = closes[-1]

        # Entry: Breakout above upper band + MACD bullish
        if current_price > upper_band and macd_line[-1] > macd_signal[-1]:
            direction = OrderType.BUY
            stop_loss = current_price - (2 * std)
            take_profit = current_price + (3 * std)
        # Entry: Breakout below lower band + MACD bearish
        elif current_price < lower_band and macd_line[-1] < macd_signal[-1]:
            direction = OrderType.SELL
            stop_loss = current_price + (2 * std)
            take_profit = current_price - (3 * std)
        else:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason="MACD+BB breakout",
            confidence=0.8,
            metadata={}
        )

    def _ema(self, data, period):
        alpha = 2 / (period + 1)
        ema = np.zeros(len(data))
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema


class RSIDivergenceStrategy(Strategy):
    """RSI Divergence - Catch reversals early"""

    def __init__(self, name: str = "RSI_Div", config: dict = None):
        default_config = {
            'rsi_period': 14,
            'lookback': 20,
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Signal | None:
        bars = state.bars_h1
        if not bars or len(bars) < 100:
            return None

        closes = np.array([b['close'] for b in bars])
        highs = np.array([b['high'] for b in bars])
        lows = np.array([b['low'] for b in bars])

        # Calculate RSI
        rsi = self._calculate_rsi(closes, self.config['rsi_period'])

        # Find recent swing high/low
        lookback = self.config['lookback']
        recent_high_idx = np.argmax(highs[-lookback:])
        recent_low_idx = np.argmin(lows[-lookback:])

        current_price = closes[-1]

        # Bullish divergence: price makes lower low, RSI makes higher low
        if recent_low_idx < lookback - 5:  # Recent low was earlier
            prev_low_price = lows[-lookback + recent_low_idx]
            curr_low_price = lows[-1]
            prev_low_rsi = rsi[-lookback + recent_low_idx]
            curr_low_rsi = rsi[-1]

            if curr_low_price < prev_low_price and curr_low_rsi > prev_low_rsi:
                # Bullish divergence!
                direction = OrderType.BUY
                stop_loss = curr_low_price - (curr_low_price * 0.02)
                take_profit = current_price + (current_price * 0.04)

                return Signal(
                    strategy_name=self.name,
                    symbol=state.symbol,
                    direction=direction,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    volume=state.symbol_info.min_lot,
                    reason="RSI bullish divergence",
                    confidence=0.7,
                    metadata={}
                )

        # Bearish divergence: price makes higher high, RSI makes lower high
        if recent_high_idx < lookback - 5:
            prev_high_price = highs[-lookback + recent_high_idx]
            curr_high_price = highs[-1]
            prev_high_rsi = rsi[-lookback + recent_high_idx]
            curr_high_rsi = rsi[-1]

            if curr_high_price > prev_high_price and curr_high_rsi < prev_high_rsi:
                # Bearish divergence!
                direction = OrderType.SELL
                stop_loss = curr_high_price + (curr_high_price * 0.02)
                take_profit = current_price - (current_price * 0.04)

                return Signal(
                    strategy_name=self.name,
                    symbol=state.symbol,
                    direction=direction,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    volume=state.symbol_info.min_lot,
                    reason="RSI bearish divergence",
                    confidence=0.7,
                    metadata={}
                )

        return None

    def _calculate_rsi(self, closes, period):
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(closes))
        avg_loss = np.zeros(len(closes))

        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])

        for i in range(period + 1, len(closes)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi


class StochasticStrategy(Strategy):
    """Stochastic Oscillator - Overbought/Oversold"""

    def __init__(self, name: str = "Stochastic", config: dict = None):
        default_config = {
            'k_period': 14,
            'd_period': 3,
            'overbought': 80,
            'oversold': 20,
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Signal | None:
        bars = state.bars_h1
        if not bars or len(bars) < 100:
            return None

        closes = np.array([b['close'] for b in bars])
        highs = np.array([b['high'] for b in bars])
        lows = np.array([b['low'] for b in bars])

        # Calculate Stochastic
        k_values = []
        period = self.config['k_period']

        for i in range(period, len(closes)):
            high_max = np.max(highs[i-period:i])
            low_min = np.min(lows[i-period:i])
            k = ((closes[i] - low_min) / (high_max - low_min + 1e-10)) * 100
            k_values.append(k)

        k_values = np.array(k_values)
        d_values = np.convolve(k_values, np.ones(self.config['d_period'])/self.config['d_period'], mode='valid')

        if len(k_values) < 2 or len(d_values) < 2:
            return None

        current_price = closes[-1]
        current_k = k_values[-1]
        prev_k = k_values[-2]
        current_d = d_values[-1]
        prev_d = d_values[-2]

        # Bullish: K crosses above D in oversold zone
        if (prev_k < prev_d and current_k > current_d and
            current_k < self.config['oversold']):
            direction = OrderType.BUY
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.04
        # Bearish: K crosses below D in overbought zone
        elif (prev_k > prev_d and current_k < current_d and
              current_k > self.config['overbought']):
            direction = OrderType.SELL
            stop_loss = current_price * 1.02
            take_profit = current_price * 0.96
        else:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason="Stochastic crossover",
            confidence=0.65,
            metadata={}
        )


class MeanReversionStrategy(Strategy):
    """Mean Reversion - Bollinger Squeeze"""

    def __init__(self, name: str = "MeanRev", config: dict = None):
        default_config = {
            'bb_period': 20,
            'bb_std': 2,
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Signal | None:
        bars = state.bars_h1
        if not bars or len(bars) < 100:
            return None

        closes = np.array([b['close'] for b in bars])

        # Calculate Bollinger Bands
        sma = np.mean(closes[-self.config['bb_period']:])
        std = np.std(closes[-self.config['bb_period']:])
        upper_band = sma + (std * self.config['bb_std'])
        lower_band = sma - (std * self.config['bb_std'])

        current_price = closes[-1]

        # Buy at lower band (expect reversion to mean)
        if current_price <= lower_band:
            direction = OrderType.BUY
            stop_loss = lower_band - std
            take_profit = sma  # Target is middle band
        # Sell at upper band
        elif current_price >= upper_band:
            direction = OrderType.SELL
            stop_loss = upper_band + std
            take_profit = sma
        else:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason="Mean reversion",
            confidence=0.6,
            metadata={}
        )


class SupportResistanceStrategy(Strategy):
    """Support/Resistance Bounce"""

    def __init__(self, name: str = "SupRes", config: dict = None):
        default_config = {
            'lookback': 50,
            'tolerance': 0.001,  # 0.1% tolerance for level
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Signal | None:
        bars = state.bars_h1
        if not bars or len(bars) < 100:
            return None

        highs = np.array([b['high'] for b in bars])
        lows = np.array([b['low'] for b in bars])
        closes = np.array([b['close'] for b in bars])

        lookback = self.config['lookback']

        # Find support (recent lows)
        support_level = np.min(lows[-lookback:])

        # Find resistance (recent highs)
        resistance_level = np.max(highs[-lookback:])

        current_price = closes[-1]
        tolerance = current_price * self.config['tolerance']

        # Bounce off support
        if abs(current_price - support_level) < tolerance:
            direction = OrderType.BUY
            stop_loss = support_level * 0.99
            take_profit = support_level + (resistance_level - support_level) * 0.5
        # Bounce off resistance
        elif abs(current_price - resistance_level) < tolerance:
            direction = OrderType.SELL
            stop_loss = resistance_level * 1.01
            take_profit = resistance_level - (resistance_level - support_level) * 0.5
        else:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason="S/R bounce",
            confidence=0.7,
            metadata={}
        )


class MomentumHistogramStrategy(Strategy):
    """Momentum - MACD Histogram Expansion"""

    def __init__(self, name: str = "Momentum", config: dict = None):
        default_config = {
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'ema_trend': 50,
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Signal | None:
        bars = state.bars_h1
        if not bars or len(bars) < 100:
            return None

        closes = np.array([b['close'] for b in bars])

        # Calculate MACD
        ema_fast = self._ema(closes, self.config['macd_fast'])
        ema_slow = self._ema(closes, self.config['macd_slow'])
        macd_line = ema_fast - ema_slow
        macd_signal = self._ema(macd_line, self.config['macd_signal'])
        macd_hist = macd_line - macd_signal

        # Trend filter
        ema_trend = self._ema(closes, self.config['ema_trend'])

        current_price = closes[-1]

        # Momentum expansion (histogram getting bigger)
        if len(macd_hist) < 3:
            return None

        hist_expanding = abs(macd_hist[-1]) > abs(macd_hist[-2]) > abs(macd_hist[-3])

        # Buy: Bullish histogram expanding + price above trend EMA
        if macd_hist[-1] > 0 and hist_expanding and current_price > ema_trend[-1]:
            direction = OrderType.BUY
            stop_loss = ema_trend[-1]
            take_profit = current_price * 1.03
        # Sell: Bearish histogram expanding + price below trend EMA
        elif macd_hist[-1] < 0 and hist_expanding and current_price < ema_trend[-1]:
            direction = OrderType.SELL
            stop_loss = ema_trend[-1]
            take_profit = current_price * 0.97
        else:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason="Momentum expansion",
            confidence=0.75,
            metadata={}
        )

    def _ema(self, data, period):
        alpha = 2 / (period + 1)
        ema = np.zeros(len(data))
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema


class VolumeBreakoutStrategy(Strategy):
    """Volume-based Breakout"""

    def __init__(self, name: str = "Volume", config: dict = None):
        default_config = {
            'volume_multiplier': 1.5,
            'lookback': 20,
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(name, default_config)

    def analyze(self, state: MarketState) -> Signal | None:
        bars = state.bars_h1
        if not bars or len(bars) < 100:
            return None

        volumes = np.array([b['volume'] for b in bars])
        closes = np.array([b['close'] for b in bars])
        highs = np.array([b['high'] for b in bars])
        lows = np.array([b['low'] for b in bars])

        avg_volume = np.mean(volumes[-self.config['lookback']:])
        current_volume = volumes[-1]

        # Volume surge
        if current_volume < avg_volume * self.config['volume_multiplier']:
            return None

        # Find recent high/low
        recent_high = np.max(highs[-self.config['lookback']:-1])
        recent_low = np.min(lows[-self.config['lookback']:-1])

        current_price = closes[-1]

        # Bullish breakout with volume
        if current_price > recent_high:
            direction = OrderType.BUY
            stop_loss = recent_high * 0.99
            take_profit = current_price * 1.03
        # Bearish breakout with volume
        elif current_price < recent_low:
            direction = OrderType.SELL
            stop_loss = recent_low * 1.01
            take_profit = current_price * 0.97
        else:
            return None

        return Signal(
            strategy_name=self.name,
            symbol=state.symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=state.symbol_info.min_lot,
            reason="Volume breakout",
            confidence=0.7,
            metadata={}
        )


def test_strategy(params):
    """Test a single strategy"""
    strategy_class, strategy_name, symbol, start, end = params

    try:
        if not mt5.initialize():
            return None

        strategy = strategy_class()
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000.0,
            risk_per_trade_pct=1.0,
            spread_pips=2.0,
            commission_per_lot=7.0
        )

        metrics = backtester.run(symbol, "H1", start, end)

        mt5.shutdown()

        if metrics and metrics.total_trades >= 10:
            return {
                'strategy': strategy_name,
                'symbol': symbol,
                'trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'pnl': metrics.total_pnl,
                'pnl_pct': metrics.total_pnl_pct,
                'profit_factor': metrics.profit_factor,
                'max_dd': metrics.max_drawdown_pct,
                'sharpe': metrics.sharpe_ratio,
                'expectancy': metrics.expectancy,
            }
    except Exception as e:
        print(f"Error testing {strategy_name}: {e}")

    return None


def main():
    print('='*80)
    print('MULTI-STRATEGY TYPE COMPARISON')
    print('='*80)
    print('\nTesting 8 COMPLETELY DIFFERENT strategy types:')
    print('  1. MACD + Bollinger Bands (78% WR from research)')
    print('  2. RSI Divergence (catch reversals)')
    print('  3. Stochastic Oscillator (overbought/oversold)')
    print('  4. Mean Reversion (Bollinger squeeze)')
    print('  5. Support/Resistance Bounce')
    print('  6. Momentum (MACD histogram)')
    print('  7. Volume Breakout')
    print('  8. EMA Breakout (our previous winner)')
    print()

    # Import our previous winner
    from optimize_gold_strategy import GoldScalpingStrategy

    strategies = [
        (MACDBollingerStrategy, "MACD+Bollinger"),
        (RSIDivergenceStrategy, "RSI_Divergence"),
        (StochasticStrategy, "Stochastic"),
        (MeanReversionStrategy, "Mean_Reversion"),
        (SupportResistanceStrategy, "Support_Resistance"),
        (MomentumHistogramStrategy, "Momentum"),
        (VolumeBreakoutStrategy, "Volume_Breakout"),
        (GoldScalpingStrategy, "EMA_Breakout_Winner"),
    ]

    # Test period
    end = datetime.now()
    start_12m = end - timedelta(days=365)

    symbol = 'GOLD'

    print(f'Testing on {symbol} (12 months)...')
    print()

    # Test sequentially to avoid pickle issues
    print('Running tests...')
    results = []

    for strategy_class, name in strategies:
        print(f'  Testing: {name}...', end='', flush=True)

        try:
            if not mt5.initialize():
                print(' FAILED (MT5)')
                continue

            # Special handling for GoldScalpingStrategy
            if name == "EMA_Breakout_Winner":
                strategy = strategy_class(config={
                    'use_asian_session': True,
                    'use_london_session': True,
                    'use_ny_session': True,
                    'entry_type': 'breakout',
                    'lookback_periods': 10,
                    'stop_pips': 100,
                    'target_pips': 100,
                    'avoid_wednesday': True,
                })
            else:
                strategy = strategy_class()

            backtester = Backtester(
                strategy=strategy,
                initial_capital=10000.0,
                risk_per_trade_pct=1.0,
                spread_pips=2.0,
                commission_per_lot=7.0
            )

            metrics = backtester.run(symbol, "H1", start_12m, end)

            mt5.shutdown()

            if metrics and metrics.total_trades >= 5:
                results.append({
                    'strategy': name,
                    'symbol': symbol,
                    'trades': metrics.total_trades,
                    'win_rate': metrics.win_rate,
                    'pnl': metrics.total_pnl,
                    'pnl_pct': metrics.total_pnl_pct,
                    'profit_factor': metrics.profit_factor,
                    'max_dd': metrics.max_drawdown_pct,
                    'sharpe': metrics.sharpe_ratio,
                    'expectancy': metrics.expectancy,
                })
                print(f' DONE ({metrics.total_trades} trades, ${metrics.total_pnl:,.0f})')
            else:
                print(' SKIPPED (insufficient trades)')

        except Exception as e:
            print(f' ERROR: {e}')
            mt5.shutdown()

    print('\n' + '='*80)
    print('RESULTS - Strategy Type Comparison')
    print('='*80)

    if not results:
        print('No valid results')
        return

    # Sort by P&L
    results.sort(key=lambda x: x['pnl'], reverse=True)

    print(f"\n{'#':<4} {'Strategy Type':<30} {'Trades':<8} {'WR':<8} {'P&L':<12} {'PF':<8} {'Sharpe':<8}")
    print('-'*100)

    for i, r in enumerate(results, 1):
        print(f"{i:<4} {r['strategy']:<30} {r['trades']:<8} {r['win_rate']:>6.1%}  "
              f"${r['pnl']:>9,.0f}  {r['profit_factor']:<8.2f} {r['sharpe']:<8.2f}")

    # Show best strategy details
    best = results[0]
    print('\n' + '='*80)
    print('WINNER - Best Strategy Type')
    print('='*80)
    print(f"\nStrategy: {best['strategy']}")
    print(f"P&L: ${best['pnl']:,.0f} on $10k ({best['pnl_pct']*100:.1f}%)")
    print(f"Trades: {best['trades']}")
    print(f"Win Rate: {best['win_rate']:.1%}")
    print(f"Profit Factor: {best['profit_factor']:.2f}")
    print(f"Max Drawdown: {best['max_dd']*100:.1f}%")
    print(f"Sharpe Ratio: {best['sharpe']:.2f}")
    print(f"Expectancy: ${best['expectancy']:.2f} per trade")

    # Comparison
    print('\n' + '='*80)
    print('KEY INSIGHTS')
    print('='*80)

    print(f"\n1. Best Performer: {best['strategy']}")
    print(f"   Makes ${best['pnl']:,.0f} vs EMA Breakout's $7,662")

    profitable = [r for r in results if r['pnl'] > 0]
    print(f"\n2. Profitable Strategies: {len(profitable)} of {len(results)}")

    high_wr = [r for r in results if r['win_rate'] > 0.55]
    print(f"\n3. High Win Rate (>55%): {len(high_wr)} strategies")

    print('\n' + '='*80)
    print('NEXT STEPS')
    print('='*80)
    print('\n1. Take top 2-3 strategy types')
    print('2. Optimize parameters for each')
    print('3. Run portfolio combining best strategies')
    print('4. Validate with walk-forward analysis')
    print('5. Paper trade winner for 2 weeks')


if __name__ == '__main__':
    main()
