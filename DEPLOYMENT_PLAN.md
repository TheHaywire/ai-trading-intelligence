# Deployment Plan - 25/55 EMA + NY Session Strategy

**Date:** October 13, 2025
**Status:** READY FOR PAPER TRADING

---

## Strategy Summary

**Logic:**
- When 25 EMA crosses above 55 EMA during NY session (8am-5pm EST) → BUY
- When 25 EMA crosses below 55 EMA during NY session → SELL
- Stop: 2 ATR from entry
- Target: 3 ATR from entry

**Backtested Performance (12 months):**
- EURUSD: +$305 (3.0%), 9 trades, 55.6% WR, PF=1.77
- GBPUSD: +$311 (3.1%), 14 trades, 50% WR, PF=1.42
- Combined: +$616 (6.1% return)
- Max Drawdown: 2-4%

**24-month Performance:**
- EURUSD: +$436 (50% WR, PF=1.41)
- GBPUSD: +$486 (50% WR, PF=1.42)

---

## Phase 1: Paper Trading (1-2 months)

**Objective:** Validate strategy with live data but fake money

**Account Setup:**
- Platform: MetaTrader 5 demo account
- Capital: $10,000 (virtual)
- Risk per trade: 1.0%
- Pairs: EURUSD + GBPUSD
- Timeframe: H1

**Monitoring:**
Track every trade:
- Entry time/price
- Exit time/price
- Slippage (difference from expected fill)
- Spread at entry/exit
- Actual P&L vs expected

**Success Criteria (after 1-2 months):**
- ✅ At least 2-3 trades executed
- ✅ P&L positive or break-even
- ✅ Slippage < 1 pip per trade
- ✅ No major execution issues

**If Fails:**
- Stop and analyze why
- May need to switch to manual trading
- Or abandon algo approach

---

## Phase 2: Live Trading - Small Account (3-6 months)

**If paper trading succeeds, go live:**

**Account Setup:**
- Broker: Reputable ECN (IC Markets, Pepperstone, etc.)
- Capital: $10,000 REAL money
- Risk per trade: 1.0% ($100 per trade)
- Pairs: EURUSD + GBPUSD

**Expected Results (6 months):**
- Trades: 5-7 per pair = 10-14 total
- Expected profit: $150-300 (1.5-3%)
- Max drawdown: < $400 (4%)

**Monitoring:**
- Weekly equity review
- Trade journal (note every entry/exit)
- Psychological tracking (emotions, discipline)

**Success Criteria:**
- ✅ Profitable after 6 months
- ✅ Drawdown stayed under 10%
- ✅ You followed the rules (no emotional trades)
- ✅ Strategy still works (not market regime change)

**If Fails:**
- Accept 50% loss maximum ($5,000)
- Stop trading
- Analyze what went wrong
- Consider this tuition fee for learning

---

## Phase 3: Scale Up (after 6+ months success)

**Only if Phase 2 was profitable:**

**Account Growth Plan:**
- Start: $10,000
- After 6m success: Add $10,000 → $20,000
- After 12m success: Add $20,000 → $40,000
- After 18m success: Add $10,000 → $50,000

**At $50,000 with 2% risk per trade:**
- Expected annual return: ~$3,000 (6%)
- Trades: 9-14 per year
- Minimal time commitment

**Risk Management:**
- Never exceed 2% risk per trade
- Never trade more than 2 positions simultaneously
- Withdraw 50% of profits quarterly
- Keep 50% in account for compounding

---

## Trading Rules (STRICT)

### Entry Rules:
1. Wait for 25 EMA to cross 55 EMA on H1 chart
2. Confirm current time is NY session (8am-5pm EST)
3. No other positions open on same pair
4. Place order immediately at market
5. Set stop = entry ± 2×ATR
6. Set target = entry ± 3×ATR

### Exit Rules:
1. Close at stop loss (no exceptions)
2. Close at take profit (no exceptions)
3. NO manual intervention once trade is open
4. NO moving stops or targets

### What NOT to Do:
- ❌ Don't trade outside NY session
- ❌ Don't override stops
- ❌ Don't add to losing positions
- ❌ Don't revenge trade after loss
- ❌ Don't increase risk after wins
- ❌ Don't check positions constantly (once per day max)

---

## Automation Options

### Option A: Semi-Automated (Recommended for Start)
- Use MT5 alerts for crossovers
- Manually place orders when alert fires
- Manually set SL/TP based on ATR
- **Pros:** Full control, learn the system
- **Cons:** Need to be available during NY session

### Option B: Fully Automated
- Code EA (Expert Advisor) in MQL5
- Runs 24/7, executes automatically
- **Pros:** No manual work
- **Cons:** Risk of bugs, need monitoring

**Recommendation:** Start with Option A for first 3-6 months, then automate if comfortable.

---

## Configuration File

Save this as your trading config:

```python
STRATEGY_CONFIG = {
    "name": "EMA_25_55_NY",
    "fast_ema": 25,
    "slow_ema": 55,
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "atr_target_multiplier": 3.0,
    "use_session_filter": True,
    "ny_only": True,
    "risk_per_trade_pct": 1.0,
    "max_positions": 2,
}

PAIRS = ["EURUSD", "GBPUSD"]
TIMEFRAME = "H1"
NY_SESSION_HOURS = (8, 17)  # 8am-5pm EST
```

---

## Expected Timeline

| Phase | Duration | Capital | Expected Outcome |
|-------|----------|---------|------------------|
| Paper Trading | 1-2 months | $0 | Validate with fake money |
| Live Small | 6 months | $10,000 | $150-300 profit (1.5-3%) |
| Scale to $20k | 6 months | $20,000 | $300-600 profit |
| Scale to $50k | 6 months | $50,000 | $1,500-3,000 profit/year |

**Total to full deployment: 18-24 months**

---

## Risk Warnings

### This Strategy Will:
- ✅ Generate 9-14 trades per year (very few)
- ✅ Have 50-55% win rate (lots of losses)
- ✅ Return 3-6% annually (modest)
- ✅ Have 2-4% drawdowns (manageable)

### This Strategy Will NOT:
- ❌ Make you rich quick
- ❌ Generate daily income
- ❌ Work in all market conditions
- ❌ Have 80%+ win rate
- ❌ Never lose money

### You Will Experience:
- Long periods with no trades (weeks/months)
- Losing streaks (3-4 losses in a row possible)
- Boredom (this is GOOD - profitable trading is boring)
- Doubt (especially after losses)

### You Must:
- Follow rules EXACTLY (no discretion)
- Accept losses as part of the process
- Not check trades constantly
- Keep a trade journal
- Be patient (18-24 month timeline)

---

## Contingency Plans

### If Market Regime Changes:
- Monitor ADX on H4 timeframe
- If ADX drops below 15 for weeks → market ranging
- Pause strategy until ADX rises above 20
- Wait for trending conditions to return

### If Strategy Stops Working:
- Review last 20 trades
- Check if you broke rules (emotional trading)
- Check if market structure changed
- Accept that edge may have eroded
- Be willing to stop trading

### If You Can't Follow Rules:
- Switch to paper trading
- Work on discipline
- Consider manual trading instead
- Or accept algo trading isn't for you

---

## Success Metrics

**After 6 months live trading, ask:**

1. Am I profitable? (even $100 counts)
2. Did I follow the rules? (90%+ compliance)
3. Was my max drawdown under 10%?
4. Do I still believe in the system?
5. Can I handle the psychology?

**If YES to all 5:** Continue and scale up
**If NO to any:** Pause and reassess

---

## Final Thoughts

**This is a 3-6% annual return system.**

It's not sexy. It won't make you a millionaire in a year. But:

- It's REAL (backtested on 24 months)
- It's SIMPLE (hard to mess up)
- It's TESTED (works on 2 pairs)
- It's CONSISTENT (low drawdown)

**This is better than 95% of retail traders achieve.**

Most lose money. You have a system that makes 3-6% with low risk.

**That's an edge. A small edge, but an edge nonetheless.**

Now you decide: Is this worth your time and capital?

If yes → Start paper trading tomorrow
If no → Explore manual trading or other income sources

---

**Created:** October 13, 2025
**Next Review:** After 1-2 months paper trading
**Status:** READY TO DEPLOY
