"""
Debug the regime classifier to see what scores and classifications it's producing.
"""

import logging
import sys
from datetime import datetime
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
    alpha = 2.0 / (period + 1)
    for i in range(1, len(data)):
        ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
    return ema


def calculate_adx(bars, period=14):
    """Calculate ADX."""
    highs = np.array([bar["high"] for bar in bars])
    lows = np.array([bar["low"] for bar in bars])
    closes = np.array([bar["close"] for bar in bars])

    # True Range
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    # Directional Movement
    plus_dm = np.where((highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]),
                      np.maximum(highs[1:] - highs[:-1], 0), 0)
    minus_dm = np.where((lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]),
                       np.maximum(lows[:-1] - lows[1:], 0), 0)

    # Smooth
    atr = np.zeros(len(tr))
    plus_di = np.zeros(len(plus_dm))
    minus_di = np.zeros(len(minus_dm))

    atr[period-1] = np.mean(tr[:period])
    plus_di[period-1] = np.mean(plus_dm[:period])
    minus_di[period-1] = np.mean(minus_dm[:period])

    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        plus_di[i] = (plus_di[i-1] * (period - 1) + plus_dm[i]) / period
        minus_di[i] = (minus_di[i-1] * (period - 1) + minus_dm[i]) / period

    plus_di = 100 * plus_di / (atr + 1e-10)
    minus_di = 100 * minus_di / (atr + 1e-10)

    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)

    adx = np.zeros(len(dx))
    adx[period-1] = np.mean(dx[:period])

    for i in range(period, len(dx)):
        adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period

    return adx[-1] if len(adx) > 0 else 0.0


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
    return atr[-1]


def debug_regime_detection(bars, period_name):
    """Debug regime detection on a period."""
    logger.info(f"\n{'='*80}")
    logger.info(f"DEBUGGING: {period_name}")
    logger.info(f"{'='*80}")

    if len(bars) < 50:
        logger.warning("Not enough bars")
        return

    # Calculate all factors
    adx = calculate_adx(bars, 14)
    atr = calculate_atr(bars, 14)
    current_price = bars[-1]["close"]
    atr_pct = (atr / current_price) * 100

    # Trend consistency
    closes = np.array([bar["close"] for bar in bars[-40:]])
    ema_fast = calculate_ema(closes, 10)
    ema_slow = calculate_ema(closes, 20)

    trend_up = ema_fast > ema_slow
    same_direction = np.sum(trend_up == trend_up[-1])
    trend_consistency = same_direction / len(trend_up)

    # Reversal rate
    price_changes = np.diff(closes)
    reversals = np.sum(np.sign(price_changes[:-1]) != np.sign(price_changes[1:]))
    reversal_rate = reversals / (len(price_changes) - 1) if len(price_changes) > 1 else 0.5

    # Bollinger width
    sma = np.mean(closes[-20:])
    std = np.std(closes[-20:])
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    bb_width = ((upper - lower) / sma) * 100 if sma > 0 else 0

    logger.info(f"\nRAW METRICS:")
    logger.info(f"  ADX: {adx:.2f}")
    logger.info(f"  ATR %: {atr_pct:.3f}%")
    logger.info(f"  Trend Consistency: {trend_consistency:.1%}")
    logger.info(f"  Reversal Rate: {reversal_rate:.1%}")
    logger.info(f"  Bollinger Width: {bb_width:.3f}%")

    # Calculate score (same logic as in strategy)
    score = 0

    # ADX contribution (max 30 points)
    if adx > 32:
        score += 30
        adx_contrib = 30
    elif adx > 25:
        score += 20
        adx_contrib = 20
    elif adx > 20:
        score += 10
        adx_contrib = 10
    else:
        adx_contrib = 0

    # Trend Consistency contribution (max 40 points)
    if trend_consistency > 0.53:
        score += 40
        tc_contrib = 40
    elif trend_consistency > 0.45:
        score += 25
        tc_contrib = 25
    elif trend_consistency > 0.35:
        score += 10
        tc_contrib = 10
    else:
        tc_contrib = 0

    # Reversal Rate contribution (max 20 points)
    if reversal_rate < 0.50:
        score += 20
        rr_contrib = 20
    elif reversal_rate < 0.55:
        score += 10
        rr_contrib = 10
    else:
        rr_contrib = 0

    # Volatility contribution (max 10 points)
    if 0.10 < atr_pct < 0.25:
        score += 10
        vol_contrib = 10
    elif 0.08 < atr_pct < 0.30:
        score += 5
        vol_contrib = 5
    else:
        vol_contrib = 0

    logger.info(f"\nSCORE BREAKDOWN:")
    logger.info(f"  ADX contribution: {adx_contrib}/30")
    logger.info(f"  Trend Consistency contribution: {tc_contrib}/40")
    logger.info(f"  Reversal Rate contribution: {rr_contrib}/20")
    logger.info(f"  Volatility contribution: {vol_contrib}/10")
    logger.info(f"  TOTAL SCORE: {score}/100")

    # Classification
    if score >= 70:
        regime = "TRENDING"
    elif score >= 50:
        regime = "MODERATE_TREND"
    else:
        regime = "RANGING"

    logger.info(f"\nCLASSIFICATION: {regime}")

    return score, regime


def main():
    """Debug regime classifier on different periods."""
    logger.info("="*80)
    logger.info("REGIME CLASSIFIER DEBUG TOOL")
    logger.info("="*80)

    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return

    logger.info(f"MT5 connected: {mt5.version()}")

    symbol = "EURUSD"

    # April-June (bad period)
    april_start = datetime(2025, 4, 1)
    june_end = datetime(2025, 6, 30, 23, 59, 59)

    # July-October (good period)
    july_start = datetime(2025, 7, 1)
    oct_end = datetime.now()

    logger.info(f"\nFetching data for {symbol}...")

    # Get H4 data for both periods
    bars_april_june = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, april_start, june_end)
    bars_july_oct = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, july_start, oct_end)

    if bars_april_june is None or len(bars_april_june) == 0:
        logger.error("Failed to fetch April-June data")
        return

    if bars_july_oct is None or len(bars_july_oct) == 0:
        logger.error("Failed to fetch July-Oct data")
        return

    # Convert to list of dicts
    bars_april_june = [dict(zip(bars_april_june.dtype.names, bar)) for bar in bars_april_june]
    bars_july_oct = [dict(zip(bars_july_oct.dtype.names, bar)) for bar in bars_july_oct]

    logger.info(f"April-June: {len(bars_april_june)} bars")
    logger.info(f"July-Oct: {len(bars_july_oct)} bars")

    # Debug both periods
    score1, regime1 = debug_regime_detection(bars_april_june, "APRIL-JUNE (BAD PERIOD)")
    score2, regime2 = debug_regime_detection(bars_july_oct, "JULY-OCTOBER (GOOD PERIOD)")

    # Comparison
    logger.info(f"\n{'='*80}")
    logger.info("COMPARISON")
    logger.info(f"{'='*80}")
    logger.info(f"\n{'Period':<20} {'Score':<10} {'Classification':<20}")
    logger.info("-" * 50)
    logger.info(f"{'April-June':<20} {score1:<10} {regime1:<20}")
    logger.info(f"{'July-October':<20} {score2:<10} {regime2:<20}")

    score_diff = score2 - score1
    logger.info(f"\nScore Difference: {score_diff:+d} points")

    if regime1 == "RANGING" and regime2 in ["TRENDING", "MODERATE_TREND"]:
        logger.info("\nSUCCESS: Classifier correctly distinguishes good vs bad periods!")
    elif regime1 == regime2:
        logger.info("\nPROBLEM: Classifier treats both periods the same!")
        logger.info("Need to adjust thresholds or add more factors.")
    else:
        logger.info("\nPARTIAL: Some differentiation but may need tuning.")

    mt5.shutdown()


if __name__ == "__main__":
    main()
