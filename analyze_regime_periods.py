"""
Deep analysis of April-June vs July-October market characteristics.

This script will help us understand WHAT made July-Oct favorable
and April-June unfavorable, so we can build a better regime classifier.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def calculate_ema(data, period):
    """Calculate EMA."""
    ema = np.zeros_like(data)
    ema[0] = data[0]
    multiplier = 2.0 / (period + 1)

    for i in range(1, len(data)):
        ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))

    return ema


def calculate_atr(bars, period=14):
    """Calculate ATR."""
    highs = np.array([bar["high"] for bar in bars])
    lows = np.array([bar["low"] for bar in bars])
    closes = np.array([bar["close"] for bar in bars])

    tr = np.maximum(
        highs - lows,
        np.maximum(
            np.abs(highs - np.roll(closes, 1)),
            np.abs(lows - np.roll(closes, 1))
        )
    )
    tr[0] = highs[0] - lows[0]

    atr = calculate_ema(tr, period)
    return atr


def calculate_adx(bars, period=14):
    """Calculate ADX."""
    highs = np.array([bar["high"] for bar in bars])
    lows = np.array([bar["low"] for bar in bars])
    closes = np.array([bar["close"] for bar in bars])

    # Directional movement
    up_move = highs[1:] - highs[:-1]
    down_move = lows[:-1] - lows[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Pad to match length
    plus_dm = np.concatenate([[0], plus_dm])
    minus_dm = np.concatenate([[0], minus_dm])

    # True range
    tr = np.maximum(
        highs - lows,
        np.maximum(
            np.abs(highs - np.roll(closes, 1)),
            np.abs(lows - np.roll(closes, 1))
        )
    )
    tr[0] = highs[0] - lows[0]

    # Smooth
    atr = calculate_ema(tr, period)
    plus_di = 100 * calculate_ema(plus_dm, period) / atr
    minus_di = 100 * calculate_ema(minus_dm, period) / atr

    # ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx = calculate_ema(dx, period)

    return adx


def calculate_bollinger_width(closes, period=20, std_dev=2):
    """Calculate Bollinger Band width as % of price."""
    sma = np.convolve(closes, np.ones(period)/period, mode='valid')

    # Pad to match length
    sma = np.concatenate([np.full(period-1, np.nan), sma])

    std = np.array([
        np.std(closes[max(0, i-period+1):i+1]) if i >= period-1 else np.nan
        for i in range(len(closes))
    ])

    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    width = ((upper - lower) / sma) * 100

    return width


def analyze_period(symbol, start_date, end_date, period_name):
    """Analyze market characteristics for a specific period."""
    logger.info(f"\n{'='*80}")
    logger.info(f"ANALYZING: {period_name}")
    logger.info(f"Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"{'='*80}")

    # Get H1 data
    bars = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_date, end_date)

    if bars is None or len(bars) == 0:
        logger.warning(f"No data for {period_name}")
        return None

    bars = [dict(zip(bars.dtype.names, bar)) for bar in bars]
    closes = np.array([bar["close"] for bar in bars])
    highs = np.array([bar["high"] for bar in bars])
    lows = np.array([bar["low"] for bar in bars])

    logger.info(f"Bars loaded: {len(bars)}")

    # Calculate indicators
    atr = calculate_atr(bars)
    adx = calculate_adx(bars)
    bb_width = calculate_bollinger_width(closes)

    # Calculate ATR as % of price
    atr_pct = (atr / closes) * 100

    # Calculate trend consistency (how often price is trending in one direction)
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)

    trend_up = ema_20 > ema_50
    trend_consistency = np.sum(trend_up == trend_up[0]) / len(trend_up)

    # Calculate average range per day
    daily_ranges = []
    for i in range(0, len(bars), 24):  # Group by day (24 H1 bars)
        day_bars = bars[i:i+24]
        if len(day_bars) > 0:
            day_high = max(bar["high"] for bar in day_bars)
            day_low = min(bar["low"] for bar in day_bars)
            daily_ranges.append(day_high - day_low)

    avg_daily_range = np.mean(daily_ranges) if daily_ranges else 0
    avg_daily_range_pct = (avg_daily_range / np.mean(closes)) * 100

    # Calculate choppiness (how often price reverses)
    price_changes = np.diff(closes)
    reversals = np.sum(np.sign(price_changes[:-1]) != np.sign(price_changes[1:]))
    reversal_rate = reversals / len(price_changes) if len(price_changes) > 0 else 0

    # Statistics
    metrics = {
        "period": period_name,
        "bars": len(bars),
        "avg_adx": np.nanmean(adx[50:]),  # Skip first 50 for warmup
        "median_adx": np.nanmedian(adx[50:]),
        "adx_above_25_pct": np.sum(adx[50:] > 25) / len(adx[50:]) * 100,
        "adx_above_20_pct": np.sum(adx[50:] > 20) / len(adx[50:]) * 100,
        "avg_atr_pct": np.nanmean(atr_pct[50:]),
        "avg_bb_width": np.nanmean(bb_width[50:]),
        "trend_consistency": trend_consistency,
        "avg_daily_range_pct": avg_daily_range_pct,
        "reversal_rate": reversal_rate,
        "price_change_pct": ((closes[-1] - closes[0]) / closes[0]) * 100,
    }

    # Print results
    logger.info(f"\nADX Metrics:")
    logger.info(f"  Average ADX: {metrics['avg_adx']:.2f}")
    logger.info(f"  Median ADX: {metrics['median_adx']:.2f}")
    logger.info(f"  Time ADX > 25: {metrics['adx_above_25_pct']:.1f}%")
    logger.info(f"  Time ADX > 20: {metrics['adx_above_20_pct']:.1f}%")

    logger.info(f"\nVolatility Metrics:")
    logger.info(f"  Avg ATR: {metrics['avg_atr_pct']:.3f}%")
    logger.info(f"  Avg Bollinger Width: {metrics['avg_bb_width']:.3f}%")
    logger.info(f"  Avg Daily Range: {metrics['avg_daily_range_pct']:.3f}%")

    logger.info(f"\nTrend Metrics:")
    logger.info(f"  Trend Consistency: {metrics['trend_consistency']:.1%}")
    logger.info(f"  Reversal Rate: {metrics['reversal_rate']:.1%}")
    logger.info(f"  Overall Price Change: {metrics['price_change_pct']:+.2f}%")

    # Regime classification
    if metrics['avg_adx'] > 25 and metrics['trend_consistency'] > 0.65:
        regime = "STRONG TRENDING"
    elif metrics['avg_adx'] > 20 and metrics['trend_consistency'] > 0.55:
        regime = "MODERATE TRENDING"
    elif metrics['reversal_rate'] > 0.55:
        regime = "CHOPPY RANGING"
    else:
        regime = "RANGING"

    logger.info(f"\nREGIME CLASSIFICATION: {regime}")

    return metrics


def main():
    """Run regime analysis."""
    logger.info("="*80)
    logger.info("REGIME PERIOD ANALYSIS - APRIL-JUNE vs JULY-OCTOBER")
    logger.info("="*80)

    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return

    logger.info(f"MT5 connected: {mt5.version()}\n")

    symbol = "EURUSD"

    # Define periods
    end_date = datetime.now()

    # April-June (bad period)
    april_start = datetime(2025, 4, 1)
    june_end = datetime(2025, 6, 30, 23, 59, 59)

    # July-October (good period)
    july_start = datetime(2025, 7, 1)
    oct_end = end_date

    # Analyze both periods
    bad_period = analyze_period(symbol, april_start, june_end, "APRIL-JUNE (BAD PERIOD)")
    good_period = analyze_period(symbol, july_start, oct_end, "JULY-OCTOBER (GOOD PERIOD)")

    # Comparison
    if bad_period and good_period:
        logger.info(f"\n{'='*80}")
        logger.info("COMPARATIVE ANALYSIS")
        logger.info(f"{'='*80}")

        logger.info(f"\n{'Metric':<30} {'Apr-Jun':<15} {'Jul-Oct':<15} {'Difference':<15}")
        logger.info("-" * 80)

        comparisons = [
            ("Average ADX", "avg_adx", "{:.2f}"),
            ("ADX > 25 (% time)", "adx_above_25_pct", "{:.1f}%"),
            ("Avg ATR %", "avg_atr_pct", "{:.3f}%"),
            ("Bollinger Width", "avg_bb_width", "{:.3f}%"),
            ("Trend Consistency", "trend_consistency", "{:.1%}"),
            ("Reversal Rate", "reversal_rate", "{:.1%}"),
            ("Daily Range %", "avg_daily_range_pct", "{:.3f}%"),
        ]

        for metric_name, key, fmt in comparisons:
            bad_val = bad_period[key]
            good_val = good_period[key]
            diff = good_val - bad_val

            logger.info(
                f"{metric_name:<30} {fmt.format(bad_val):<15} "
                f"{fmt.format(good_val):<15} {fmt.format(diff):<15}"
            )

        # Key insights
        logger.info(f"\n{'='*80}")
        logger.info("KEY INSIGHTS")
        logger.info(f"{'='*80}")

        adx_diff = good_period['avg_adx'] - bad_period['avg_adx']
        trend_diff = good_period['trend_consistency'] - bad_period['trend_consistency']

        logger.info(f"\n1. TREND STRENGTH:")
        logger.info(f"   July-Oct had {adx_diff:+.2f} higher ADX on average")
        logger.info(f"   July-Oct was trending {good_period['adx_above_25_pct']:.1f}% of the time")
        logger.info(f"   April-June was only trending {bad_period['adx_above_25_pct']:.1f}% of the time")

        logger.info(f"\n2. TREND CONSISTENCY:")
        logger.info(f"   July-Oct had {trend_diff:+.1%} more consistent trend direction")
        logger.info(f"   April-June reversed direction {bad_period['reversal_rate']:.1%} of the time")

        logger.info(f"\n3. VOLATILITY:")
        vol_diff = good_period['avg_atr_pct'] - bad_period['avg_atr_pct']
        logger.info(f"   July-Oct had {vol_diff:+.3f}% different ATR")

        # Recommendations for improved filter
        logger.info(f"\n{'='*80}")
        logger.info("RECOMMENDATIONS FOR IMPROVED REGIME FILTER")
        logger.info(f"{'='*80}")

        logger.info(f"\n1. ADX THRESHOLD:")
        logger.info(f"   Require ADX > {good_period['median_adx']:.1f} (median from good period)")
        logger.info(f"   This would filter out {100 - good_period['adx_above_25_pct']:.1f}% of bad-period trades")

        logger.info(f"\n2. TREND CONSISTENCY:")
        logger.info(f"   Require consistency > {good_period['trend_consistency']:.0%}")
        logger.info(f"   Measure: EMA20 vs EMA50 alignment over 20 bars")

        logger.info(f"\n3. REVERSAL RATE:")
        logger.info(f"   Reject if reversal rate > {bad_period['reversal_rate']:.0%}")
        logger.info(f"   Measure: How often price direction changes")

        logger.info(f"\n4. MULTI-FACTOR SCORE:")
        logger.info(f"   Combine ADX + Consistency + (1-Reversals) into single score")
        logger.info(f"   Trade only when score > threshold")

    mt5.shutdown()
    logger.info(f"\n{'='*80}")
    logger.info("ANALYSIS COMPLETE")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    main()
