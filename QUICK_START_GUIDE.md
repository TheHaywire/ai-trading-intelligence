# Quick Start Guide - Daily Quantitative Trading Report

## 5-Minute Setup

### Step 1: Verify Prerequisites
```bash
# Check Python version (need 3.8+)
python --version

# Verify MetaTrader 5 is installed and running
```

### Step 2: Install Dependencies
```bash
pip install MetaTrader5 pandas numpy requests
```

### Step 3: Configure Email (Optional but Recommended)
Open `exhaustive_daily_quant_report.py` and update:
```python
EMAIL_TO = "your-email@example.com"  # Line 25 - Change this
```

### Step 4: Run Your First Report
```bash
python exhaustive_daily_quant_report.py
```

**Expected Output:**
```
================================================================================
SCANNING 65 INSTRUMENTS ACROSS 6 ASSET CLASSES
================================================================================

Forex Majors:
  [1/65] EURUSD         ... [SETUP] Score: 7
  [2/65] GBPUSD         ... [OK]
  ...

================================================================================
SCAN COMPLETE
================================================================================
Symbols scanned: 62
Opportunities found: 8
High-probability setups: 4

================================================================================
GENERATING COMPREHENSIVE REPORT
================================================================================
✅ Report saved: daily_quant_report_20250113_090000.html

================================================================================
SENDING EMAIL REPORT
================================================================================
✅ Email sent successfully

================================================================================
✅ ALL TASKS COMPLETED SUCCESSFULLY
================================================================================
```

### Step 5: Open Your Report
1. **Local File**: Open `daily_quant_report_YYYYMMDD_HHMMSS.html` in your browser
2. **Email**: Check your inbox for the full report

## Understanding Your First Report

### Key Sections to Focus On

#### 1. Statistics Bar (Top)
- **Instruments Scanned**: Total markets analyzed
- **High-Probability Setups**: Trades meeting minimum criteria (confidence ≥ 60%, R:R ≥ 1:2)
- **Avg Confidence**: Signal strength across all opportunities

#### 2. Market Overview
- **Market Sentiment**: Overall market direction (Bullish/Bearish/Neutral)
- **Active Sessions**: Which major markets are open now
- **Volatility Environment**: Current market conditions (Low/Moderate/High)

#### 3. Top Trade Setups (MOST IMPORTANT)
Each trade card shows:
- **Symbol & Direction**: What to trade and which way (BULLISH = Buy, BEARISH = Sell)
- **Confidence**: Higher = better (60-70% = Good, 70-80% = Very Good, 80%+ = Excellent)
- **Entry Price**: Where to enter the trade
- **Stop Loss**: Where to exit if trade goes against you (MANDATORY)
- **Targets**: Where to take profits (T1, T2, T3)
- **Position Size**: How many lots to trade
- **Supporting Signals**: Why the system recommends this trade

## Your First Trade - Step by Step

### Example Setup from Report:
```
Symbol: EURUSD
Direction: BULLISH
Confidence: 72%
Entry: 1.0850
Stop Loss: 1.0820
Target 1: 1.0880
Target 2: 1.0900
Target 3: 1.0930
Position Size: 0.15 Lots
Risk:Reward: 1:2.5
```

### How to Execute:

#### Step 1: Validate the Setup
- ✅ Confidence ≥ 60%? (YES - 72%)
- ✅ R:R ≥ 1:2? (YES - 1:2.5)
- ✅ No high-impact news in next 4 hours? (Check Risk Calendar section)
- ✅ Account has sufficient margin for 0.15 lots?

#### Step 2: Enter the Trade in MT5
1. Open MetaTrader 5
2. Click "New Order" or F9
3. Select symbol: EURUSD
4. Type: Market Execution (or Pending Order at 1.0850)
5. Volume: 0.15 lots
6. Stop Loss: 1.0820
7. Take Profit: 1.0880 (for T1)
8. Click "Buy" (BULLISH) or "Sell" (BEARISH)

#### Step 3: Manage the Position
- **At Target 1 (1.0880)**: Close 50% of position (0.075 lots)
- **Move Stop to Breakeven**: Change stop loss from 1.0820 to 1.0850
- **At Target 2 (1.0900)**: Close another 30% (0.045 lots)
- **At Target 3 (1.0930)**: Close remaining 20% (0.03 lots) OR let it run with trailing stop

#### Step 4: Log the Trade
After trade closes, log it in `trades_log.json`:
```json
{
  "symbol": "EURUSD",
  "direction": "LONG",
  "entry": 1.0850,
  "exit": 1.0895,
  "pnl": 450,
  "strategy": "EMA Crossover + RSI",
  "timestamp": "2025-01-13T09:30:00"
}
```

## Common Mistakes to Avoid

### ❌ DON'T
1. **Ignore stop losses** - Always set them, they protect your account
2. **Trade during high-impact news** - Check Risk Calendar section first
3. **Use full account leverage** - Stick to recommended position sizes
4. **Cherry-pick signals** - If confidence is low, skip the trade
5. **Revenge trade** - If you lose, don't immediately find another trade
6. **Overtrade** - Max 5 concurrent positions, max 2% risk per trade

### ✅ DO
1. **Follow position sizing** - Use the calculated lot size
2. **Take partial profits** - Lock in gains at T1 and T2
3. **Move stops to breakeven** - After T1 is hit
4. **Log all trades** - Track performance to improve
5. **Review yesterday's performance** - Learn from wins AND losses
6. **Be patient** - Some days have 0 setups, and that's OK

## Interpreting Confidence Levels

- **80-100%**: Exceptional setup, very strong signals, consider slightly larger position (max 1.2x)
- **70-79%**: Very good setup, multiple confirming signals, standard position size
- **60-69%**: Good setup, adequate signals, consider reducing position to 0.8x
- **50-59%**: Marginal setup, mixed signals, skip or use 0.5x position size
- **Below 50%**: Weak setup, NO TRADE

## Interpreting Signal Weights

Signals in each setup have weights showing their importance:
- **Weight 3**: Strong signal (Trend alignment, Major breakout, Divergence)
- **Weight 2**: Moderate signal (MACD cross, ADX strength, RSI extremes)
- **Weight 1**: Minor signal (Stochastic, Minor patterns)

**Total Score**: Sum of all weights
- **Score 8+**: Excellent (multiple strong confirmations)
- **Score 5-7**: Good (solid setup with confirmations)
- **Score 3-4**: Acceptable (minimal requirements met)
- **Score <3**: Weak (filtered out from high-probability setups)

## Daily Routine Checklist

### Morning (Before Market Open)
- [ ] Run report: `python exhaustive_daily_quant_report.py`
- [ ] Review Market Overview section
- [ ] Check Risk Calendar for today's events
- [ ] Identify 2-3 top setups (highest confidence)
- [ ] Set alerts in MT5 for entry prices

### During Trading Session
- [ ] Monitor open positions
- [ ] Adjust stops to breakeven after T1
- [ ] Take partial profits at T1 and T2
- [ ] Don't force trades if no alerts triggered

### Evening (After Market Close)
- [ ] Log all executed trades in `trades_log.json`
- [ ] Review yesterday's performance (in next day's report)
- [ ] Plan for tomorrow based on current positions

### Weekly Review (Sunday)
- [ ] Run weekly performance summary
- [ ] Analyze win rate and profit factor
- [ ] Identify best/worst performing strategies
- [ ] Adjust approach if needed

## Customization for Your Trading Style

### Conservative Trader (Capital Preservation)
```python
# In exhaustive_daily_quant_report.py
RISK_PARAMS = {
    'max_risk_per_trade': 1.0,      # Reduce to 1%
    'min_reward_risk': 3.0,         # Increase to 1:3
    'volatility_scalar': 2.0        # Wider stops
}
```

### Aggressive Trader (Maximum Returns)
```python
RISK_PARAMS = {
    'max_risk_per_trade': 3.0,      # Increase to 3%
    'min_reward_risk': 1.5,         # Accept 1:1.5
    'volatility_scalar': 1.0        # Tighter stops
}
```

### Swing Trader (Multi-Day Holds)
```python
# Change to H4 or D1 timeframe
scanner.scan_symbol(symbol, category, timeframe=mt5.TIMEFRAME_H4)

# Wider stops for overnight holds
RISK_PARAMS['volatility_scalar'] = 2.5
```

### Scalper (Intraday Only)
```python
# Change to M15 or M30 timeframe
scanner.scan_symbol(symbol, category, timeframe=mt5.TIMEFRAME_M15)

# Tighter stops
RISK_PARAMS['volatility_scalar'] = 0.8
```

## Troubleshooting Quick Fixes

### "No setups found"
**Normal!** Not every day has ideal conditions. Wait for better opportunities rather than forcing trades.

### "Email not sending"
Check your spam folder. EmailJS free tier has daily limits. Report is still saved locally.

### "MT5 connection failed"
1. Open MT5 application
2. Login to your account
3. Go to Tools > Options > Expert Advisors
4. Check "Allow automated trading"
5. Re-run the script

### "Symbol not found"
Some brokers use different symbol names:
- GOLD might be XAUUSD
- SILVER might be XAGUSD
- Bitcoin might be BTCUSD or BTC

Edit `MARKET_UNIVERSE` in the script to match your broker's symbols.

## Next Steps

### Week 1: Learn & Observe
- Run daily reports
- Read all sections carefully
- Paper trade (virtual trades on paper/spreadsheet)
- Understand signal types

### Week 2-4: Demo Trading
- Execute trades on MT5 demo account
- Follow all risk management rules
- Log every trade
- Review performance weekly

### Month 2-3: Refine Strategy
- Identify which signal types work best for you
- Adjust timeframes to your schedule
- Optimize position sizing
- Build confidence

### Month 4+: Live Trading (Small Size)
- Start with minimum lot sizes
- Gradually increase as confidence grows
- Never exceed 2% risk per trade
- Keep learning and improving

## Getting Help

### Documentation
- **Full Guide**: `README_DAILY_QUANT_REPORT.md`
- **System Overview**: `SYSTEM_OVERVIEW.md`
- **Trading Concepts**: `TRADING_CONCEPTS_EXPLAINED.md`

### Common Questions
**Q: Can I run this multiple times per day?**
A: Yes! Run it every 4-6 hours to catch new opportunities.

**Q: Should I take every setup?**
A: No. Take only those matching your risk tolerance and confidence threshold.

**Q: What if I miss the entry price?**
A: Wait for a pullback or skip the trade. Don't chase.

**Q: Can I use this with prop firms?**
A: Yes, but ensure compliance with their specific rules (max lots, daily DD, etc.)

**Q: Do I need to trade all markets?**
A: No. Focus on 2-3 markets you understand well (e.g., forex majors + gold).

---

**You're Ready! Start with demo, be patient, follow the plan, and success will come. 📊✨**

**Remember**: The best traders are disciplined, not lucky.
