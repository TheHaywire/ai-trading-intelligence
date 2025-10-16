"""
DEMO: How to Use Different Signal Generation Strategies

This script shows you how to run each strategy type and understand
what makes each one unique.

Usage:
    python demo_signal_strategies.py
"""

from src.strategy.signal_examples import (
    TechnicalIndicatorsStrategy,
    PriceActionStrategy,
    MultiTimeframeStrategy,
    VolumeStrategy,
    MeanReversionStrategy,
    EnsembleStrategy
)


def demo_strategy_overview():
    """Print overview of each strategy type."""

    print("\n" + "="*70)
    print("MT5 SIGNAL GENERATION STRATEGIES - PRACTICAL GUIDE")
    print("="*70 + "\n")

    strategies = [
        {
            "name": "1. Technical Indicators Strategy",
            "class": TechnicalIndicatorsStrategy,
            "what": "Uses MA Crossover + RSI + MACD",
            "when": "All 3 indicators must align for signal",
            "best_for": "Trending markets with clear momentum",
            "example": "Fast EMA crosses above Slow EMA, RSI not overbought, MACD bullish = BUY"
        },
        {
            "name": "2. Price Action Strategy",
            "class": PriceActionStrategy,
            "what": "Detects Support/Resistance + Candlestick patterns",
            "when": "Price bounces off S/R with pattern confirmation",
            "best_for": "Range-bound markets, key levels",
            "example": "Price hits support, forms Bullish Hammer = BUY"
        },
        {
            "name": "3. Multi-Timeframe Strategy",
            "class": MultiTimeframeStrategy,
            "what": "Analyzes H4 trend + H1 pullback + M15 entry",
            "when": "All timeframes show confluence",
            "best_for": "High-probability entries in strong trends",
            "example": "H4 uptrend, H1 pullback to EMA, M15 momentum shift = BUY"
        },
        {
            "name": "4. Volume Strategy",
            "class": VolumeStrategy,
            "what": "Volume spike + Price breakout",
            "when": "Volume 2x average + price breaks recent high/low",
            "best_for": "Breakout scenarios, news events",
            "example": "Volume spikes 2.5x, price breaks resistance = BUY"
        },
        {
            "name": "5. Mean Reversion Strategy",
            "class": MeanReversionStrategy,
            "what": "Bollinger Bands + Z-score",
            "when": "Price is 2+ std devs from mean",
            "best_for": "Range-bound, oscillating markets",
            "example": "Price touches lower Bollinger Band, Z-score -2.5 = BUY (expect reversion)"
        },
        {
            "name": "6. Ensemble Strategy (MOST POWERFUL)",
            "class": EnsembleStrategy,
            "what": "Combines ALL 5 strategies above",
            "when": "3+ strategies vote for same direction",
            "best_for": "Reducing false signals, high-quality setups",
            "example": "4 out of 5 strategies say BUY = Strong BUY signal"
        }
    ]

    for i, strat in enumerate(strategies, 1):
        print(f"\n{strat['name']}")
        print("-" * 70)
        print(f"  WHAT:     {strat['what']}")
        print(f"  WHEN:     {strat['when']}")
        print(f"  BEST FOR: {strat['best_for']}")
        print(f"  EXAMPLE:  {strat['example']}")

        # Show how to initialize
        print(f"\n  CODE:")
        print(f"    strategy = {strat['class'].__name__}()")
        print(f"    signal = strategy.analyze(market_state)")
        print(f"    if signal:")
        print(f"        print(f'{{signal.direction}}: {{signal.reason}}')")

    print("\n" + "="*70)
    print("\nKEY DIFFERENCES:")
    print("="*70)
    print("""
1. TECHNICAL INDICATORS
   - Pro: Clear, objective rules
   - Con: Lagging (indicators react to past price)
   - Use when: Clear trends exist

2. PRICE ACTION
   - Pro: Leading (patterns form before moves)
   - Con: Subjective (pattern recognition)
   - Use when: Market at key levels

3. MULTI-TIMEFRAME
   - Pro: High win rate (multiple confirmations)
   - Con: Fewer signals (strict requirements)
   - Use when: Want quality over quantity

4. VOLUME
   - Pro: Confirms institutional involvement
   - Con: Can be manipulated
   - Use when: Major breakouts expected

5. MEAN REVERSION
   - Pro: High win rate in ranges
   - Con: Fails in strong trends (can keep extending)
   - Use when: Market is oscillating

6. ENSEMBLE
   - Pro: Best overall (filters noise)
   - Con: Very few signals (most signals get filtered)
   - Use when: Want highest quality trades only
""")

    print("\n" + "="*70)
    print("PRACTICAL USAGE:")
    print("="*70)
    print("""
STEP 1: Pick Your Strategy Type
    - Trending market? → Use Technical Indicators or Multi-Timeframe
    - Ranging market? → Use Mean Reversion or Price Action
    - Breakout? → Use Volume Strategy
    - Not sure? → Use Ensemble (it adapts)

STEP 2: Configure Parameters
    Each strategy has config parameters you can tune:

    strategy = TechnicalIndicatorsStrategy(config={
        "fast_ema": 12,
        "slow_ema": 26,
        "rsi_period": 14
    })

STEP 3: Run in Your MT5 System
    Add to your strategy loader:

    from src.strategy.signal_examples import TechnicalIndicatorsStrategy

    # In your main loop
    strategy = TechnicalIndicatorsStrategy()
    signal = strategy.analyze(market_state)

    if signal:
        broker.place_order(
            symbol=signal.symbol,
            direction=signal.direction,
            entry=signal.entry_price,
            sl=signal.stop_loss,
            tp=signal.take_profit
        )

STEP 4: Backtest & Optimize
    - Test each strategy on historical data
    - Compare win rates, profit factors
    - Tune parameters for your symbol/timeframe
    - Combine best performers in ensemble
""")

    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("""
1. ✓ You now have 6 working strategies in signal_examples.py

2. Choose one strategy to start with:
   - Beginner? Start with TechnicalIndicatorsStrategy (easiest)
   - Advanced? Start with EnsembleStrategy (best results)

3. Integration options:
   a) Replace your current ema_trend.py with one of these
   b) Run multiple strategies in parallel
   c) Use EnsembleStrategy to combine all

4. Test on demo account first:
   - Watch signals in real-time
   - Check if logic makes sense
   - Verify entry/exit points

5. Optimize:
   - Adjust parameters based on your symbol
   - Add filters (time of day, news events)
   - Track performance metrics
""")

    print("\n" + "="*70)
    print("WANT TO SEE LIVE SIGNALS?")
    print("="*70)
    print("""
To see these strategies generate signals on your MT5 account:

1. Check your main.py or trading engine file
2. Import any strategy from signal_examples.py
3. Add to strategy loader
4. Run your system

Example:
    from src.strategy.signal_examples import EnsembleStrategy

    # Add to your strategies list
    strategies = [
        EnsembleStrategy(config={"min_votes": 3}),
        # ... your other strategies
    ]

The system will automatically:
- Fetch market data from MT5
- Run analyze() on each bar
- Generate signals when conditions met
- Display in your dashboard
""")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    demo_strategy_overview()

    print("\n📊 All 6 strategies are ready to use in: src/strategy/signal_examples.py")
    print("📖 Read the code - each strategy is fully commented!")
    print("🚀 Pick one and integrate it into your MT5 system.\n")
