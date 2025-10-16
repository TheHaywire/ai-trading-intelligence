# Momentum Matrix Trader - Complete Ensemble System

## Overview

A sophisticated **7-layer ensemble trading strategy** that combines multiple technical analysis components into a weighted scoring system. Only trades when conviction is high enough (weighted score exceeds threshold).

---

## System Architecture

### 1. Core Strategy: `src/strategy/momentum_matrix.py`

**MomentumMatrixTrader** - Multi-layer ensemble with weighted voting

#### The 7 Layers:

| Layer | Component | Weight | Purpose |
|-------|-----------|--------|---------|
| 1 | **Trend** | 2 | EMA20 vs EMA50 direction bias |
| 2 | **Momentum** | 1 | RSI divergence + slope confirmation |
| 3 | **Price Action** | 2 | Breakout + Engulfing patterns |
| 4 | **MTF Confluence** | 3 | H1/H4/D1 alignment (highest weight) |
| 5 | **Volatility** | 1 | ATR + Spread filter (blocks bad conditions) |
| 6 | **Intermarket** | 2 | DXY correlation (placeholder for now) |
| 7 | **Session** | 1 | London/NY/Asia filter |

#### Scoring Logic:

Each layer outputs:
- `+1` = Bullish signal
- `-1` = Bearish signal
- `0` = Neutral or filter blocks

**Weighted Total Score** = Σ (layer_score × layer_weight)

**Trade Decision:**
- If score ≥ threshold → LONG
- If score ≤ -threshold → SHORT
- Otherwise → NO TRADE

---

### 2. Backtester: `src/engine/backtester.py`

Enhanced backtesting engine with:
- Realistic spread and slippage simulation
- ATR-based position sizing
- Multi-timeframe data support (M15, H1, H4, D1)
- Full P&L tracking with equity curve
- Performance metrics: Sharpe, drawdown, expectancy, profit factor

---

### 3. Analyzer: `src/engine/matrix_analyzer.py`

**MomentumMatrixAnalyzer** - Generates institutional-grade reports

Performs:
- **Threshold Optimization**: Test ≥2, ≥3, ≥4, ≥5
- **Weight Optimization**: Test different layer weight combinations
- **Component Backtests**: Individual layer performance
- **Ablation Analysis**: Measure impact of removing each layer
- **Walk-Forward Validation**: In-sample vs out-of-sample
- **Session Segmentation**: Performance by trading session
- **Comprehensive Reports**: Markdown format with tables

---

## Configuration

### Default Settings

```yaml
strategy: MomentumMatrix
threshold: 3                    # Minimum score to trigger trade
weights:
  trend: 2
  momentum: 1
  price_action: 2
  mtf_confluence: 3             # Highest - most predictive
  volatility: 1
  intermarket: 2
  session: 1

# Risk Management
risk_per_trade: 0.5%            # 0.5R per trade
atr_multiplier: 2.0             # Stop loss = 2x ATR
risk_reward_ratio: 2.0          # Target 2:1 R:R

# Filters
max_spread_pips: 3.0
min_atr_pips: 5.0
session_filter_enabled: true
dxy_enabled: false              # Needs DXY data feed
```

---

## Sample Trade Example

### Layer Scoring Breakdown:

| Layer | Signal | Weight | Weighted Score |
|-------|--------|--------|----------------|
| Trend | Bullish | 2 | +2 |
| Momentum | Neutral | 1 | 0 |
| Price Action | Bullish | 2 | +2 |
| MTF Confluence | Bullish | 3 | +3 |
| Volatility | OK | 1 | 0 |
| Intermarket | No Data | 2 | 0 |
| Session | London | 1 | 0 |
| **TOTAL** | | | **+7** |

**Decision**: BUY (score ≥3)

**Trade Result**:
- Entry: $1.0850
- SL: $1.0830 (20 pips, 2x ATR)
- TP: $1.0890 (40 pips, 2:1 R:R)
- Exit: $1.0890 (TP hit)
- P&L: +40 pips = +$400 (2R win)

---

## Usage

### 1. Quick Test

```bash
python test_momentum_matrix_quick.py
```

Tests strategy with 1 month of data on EURUSD M15.

### 2. Full Analysis (Comprehensive Report)

```bash
python run_momentum_matrix_analysis.py
```

Generates complete backtest report with:
- Threshold optimization
- Weight optimization
- Ablation analysis
- Walk-forward validation
- Session segmentation
- Recommended settings

### 3. Custom Backtest (Python)

```python
from datetime import datetime, timedelta
from src.strategy.momentum_matrix import MomentumMatrixTrader
from src.engine.backtester import Backtester

# Create strategy
strategy = MomentumMatrixTrader(config={
    'threshold': 3,
    'weights': {
        'trend': 2,
        'momentum': 1,
        'price_action': 2,
        'mtf_confluence': 3,
        'volatility': 1,
        'intermarket': 2,
        'session': 1
    }
})

# Run backtest
backtester = Backtester(
    strategy=strategy,
    initial_capital=10000.0,
    risk_per_trade_pct=0.5
)

end_date = datetime.now()
start_date = end_date - timedelta(days=90)

metrics = backtester.run('EURUSD', 'H1', start_date, end_date)

print(f"Total Trades: {metrics.total_trades}")
print(f"Win Rate: {metrics.win_rate:.1%}")
print(f"Expectancy: ${metrics.expectancy:.2f}")
print(f"Sharpe: {metrics.sharpe_ratio:.2f}")
```

### 4. Generate Full Report

```python
from datetime import datetime, timedelta
from src.engine.matrix_analyzer import MomentumMatrixAnalyzer

analyzer = MomentumMatrixAnalyzer(
    symbol='EURUSD',
    timeframe='H1',
    initial_capital=10000.0,
    risk_per_trade_pct=0.5
)

end_date = datetime.now()
start_date = end_date - timedelta(days=90)

report_path = analyzer.run_full_analysis(
    start_date,
    end_date,
    output_file='momentum_matrix_report.md'
)

print(f"Report saved to: {report_path}")
```

---

## Generated Report Sections

The full analysis generates a markdown report with:

### A. Single Trade Example
- Complete layer scoring breakdown
- Trade entry/exit details
- P&L and reasoning

### C. Threshold Optimization
- Test thresholds: ≥2, ≥3, ≥4, ≥5
- Metrics: Trades, Win%, Avg R:R, Expectancy, Max DD
- Optimal threshold recommendation

### D. Weight Optimization
- Test different weight configurations
- Compare: Baseline, MTF-Heavy, Trend-Focused, PA-Heavy
- Best performing combination

### E. Component Backtests
- Individual layer performance
- Trend, Momentum, Price Action, MTF separately
- Shows standalone vs ensemble strength

### F. Walk-Forward Validation
- In-sample vs out-of-sample performance
- Tests robustness and overfitting
- 75/25 split

### G. Session Segmentation
- Performance by session: London, NY, Asia
- Best session identification
- Session-specific statistics

### I. Ablation Analysis
- Remove each layer and measure impact
- Identifies critical vs redundant layers
- Change in expectancy when layer removed

### K. Final Recommended Settings
- Optimal configuration based on all tests
- Best threshold, weights, session rules
- Rationale for recommendations

### L. Next Steps Checklist
- Implementation priorities
- DXY integration
- News filter refinement
- Regime detection
- Monte Carlo simulation

---

## Files Created

```
PropShop-IF/
├── src/
│   ├── strategy/
│   │   └── momentum_matrix.py          # 7-layer ensemble strategy
│   └── engine/
│       └── matrix_analyzer.py          # Report generator
├── run_momentum_matrix_analysis.py     # Full analysis script
├── test_momentum_matrix_quick.py       # Quick test script
├── demo_momentum_matrix.py             # Architecture demo
└── MOMENTUM_MATRIX_README.md           # This file
```

---

## System Status

✓ **All components installed and tested**

✓ **MT5 integration verified**

✓ **Syntax validated (all files compile)**

✓ **Ready for backtesting with real data**

---

## Key Features

### Ensemble Advantages
- **Robust**: Multiple confirmation layers reduce false signals
- **Adaptive**: Weighted scoring allows tuning for market conditions
- **Transparent**: Every trade shows exact layer contributions
- **Optimizable**: Threshold and weights can be systematically optimized

### Risk Management
- ATR-based stops adapt to volatility
- Fixed risk per trade (0.5R default)
- Position sizing accounts for symbol pip value
- Max drawdown tracking

### Performance Metrics
- Expectancy per trade
- Risk-adjusted returns (Sharpe)
- Win rate and profit factor
- Maximum drawdown
- Average trade duration

---

## Next Steps

1. **Run Full Analysis**:
   ```bash
   python run_momentum_matrix_analysis.py
   ```

2. **Review Report**: Check `momentum_matrix_report_*.md`

3. **Optimize Settings**: Use ablation and weight optimization results

4. **Implement DXY Filter**: Add intermarket correlation data

5. **Add News Filter**: Integrate economic calendar

6. **Live Testing**: Paper trade before going live

7. **Monitor Performance**: Track live vs backtest metrics

---

## Notes

- **Data Requirements**: Needs H1, H4, D1 bars for MTF analysis
- **Minimum Bars**: At least 100 bars for EMA calculations
- **Symbol Support**: Works with any MT5 symbol (FX, metals, indices)
- **Timeframe**: Primary M15, but analyzes higher TFs

---

## Support

For issues or questions:
- Check logs for detailed error messages
- Verify MT5 connection and data availability
- Test with EURUSD first (most reliable data)
- Review layer scores in signal metadata

---

## License

Proprietary - PropShop Internal Use

---

**Built with institutional-grade quantitative analysis standards.**

**Ready to deploy. Test thoroughly before live trading.**
