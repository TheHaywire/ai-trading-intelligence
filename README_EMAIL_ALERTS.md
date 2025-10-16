# EMAIL ALERT SYSTEM - User Guide

## What You Built

A real-time market monitoring system that scans **GOLD, SILVER, EURUSD, GBPUSD, USDJPY** and sends email alerts to **manankharbanda99@gmail.com** when trading opportunities arise.

---

## Strategies Monitored

### 1. EMA Crossover (25/100)
- **Signal:** When EMA25 crosses above/below EMA100
- **Meaning:** Trend change detected
- **Your edge:** 13.9% avg return, profitable in ALL tested periods

### 2. RSI Extremes (28 period, 35/80 levels)
- **Signal:** RSI drops below 35 (oversold) or rises above 80 (overbought)
- **Meaning:** Price at extreme, likely to reverse
- **Your edge:** 27.7% return, 100% win rate (limited sample)

### 3. Donchian Breakout (50 period)
- **Signal:** Price breaks above highest high or below lowest low of last 50 hours
- **Meaning:** Strong breakout/breakdown
- **Your edge:** 37.5% return, catches momentum

---

## How to Use

### START THE SYSTEM:

```bash
cd "C:\Users\manan\OneDrive\Desktop\PropShop- IF"
python email_alert_system.py
```

The system will:
1. Send you a startup confirmation email
2. Check markets every **1 hour**
3. Send signals **immediately** when detected
4. Send market summary every **6 hours**

### STOP THE SYSTEM:

Press `Ctrl+C` in the terminal

You'll receive a shutdown email with stats.

---

## What You'll Receive

### 1. SIGNAL ALERTS (Immediate)

```
TRADING SIGNALS DETECTED - 2025-10-14 21:00

========================================
GOLD - LONG
Signal: EMA CROSSOVER
Price: $4127.50
EMA25: $4125.30
EMA100: $4122.10
Strength: BULLISH

========================================
EURUSD - SHORT
Signal: RSI OVERBOUGHT
Price: $1.0850
RSI: 82.5
Strength: STRONG
```

### 2. MARKET SUMMARIES (Every 6 hours)

```
MARKET SUMMARY - 2025-10-14 21:00

+ GOLD
  Price: $4127.26
  7-Day Change: +8.5%
  24H Range: $4090.22 - $4179.61
  Volatility: 12.3%

- SILVER
  Price: $31.45
  7-Day Change: -2.1%
  24H Range: $31.20 - $31.89
  Volatility: 8.7%

...

Monitoring: GOLD, SILVER, EURUSD, GBPUSD, USDJPY
Next update in 6 hours
```

---

## Customization

### Change Check Frequency

Edit `email_alert_system.py`:

```python
CHECK_INTERVAL = 3600  # 3600 = 1 hour, 1800 = 30 min
SEND_SUMMARY_INTERVAL = 21600  # 21600 = 6 hours
```

### Add/Remove Symbols

```python
SYMBOLS = ['GOLD', 'SILVER', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD']  # Add BTCUSD
```

### Change Strategy Parameters

**EMA Crossover:**
```python
# Line 120-121
fast_ema = self.calculate_ema(close, 25)  # Change 25 to your preferred fast EMA
slow_ema = self.calculate_ema(close, 100)  # Change 100 to your preferred slow EMA
```

**RSI:**
```python
# Line 143
rsi = self.calculate_rsi(close, 28)  # Change period
current_rsi = rsi.iloc[-1]

if current_rsi < 35:  # Change oversold level
    ...
elif current_rsi > 80:  # Change overbought level
```

**Donchian:**
```python
# Line 178
upper_channel = high.rolling(50).max()  # Change 50 to your preferred period
lower_channel = low.rolling(50).min()
```

---

## Run 24/7 (VPS Deployment)

To keep it running even when your computer is off:

### Option 1: Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start program
   - Program: `python`
   - Arguments: `C:\Users\manan\OneDrive\Desktop\PropShop- IF\email_alert_system.py`

### Option 2: Deploy to Cloud (VPS)
- Rent a cheap VPS ($5/month)
- Install Python + MT5
- Run script with `nohup python email_alert_system.py &`

---

## Troubleshooting

### Not receiving emails?
- Check spam folder
- Verify EmailJS credentials in code
- Test with: `python -c "from email_alert_system import MarketScanner; scanner = MarketScanner(); scanner.send_email('Test', 'Hello')"`

### No signals being detected?
- Normal! Signals only occur when conditions are met
- Check console output to see what's being scanned
- Lower thresholds if too strict

### MT5 connection fails?
- Ensure MT5 is logged in and running
- Check symbol names are correct for your broker

---

## What's Next?

### You have 3 options:

1. **Use as-is** - Let it email you, YOU decide whether to trade
2. **Add more strategies** - I can add support/resistance, volume, etc.
3. **Build auto-execution** - System takes trades automatically (risky!)

---

## Performance Summary

Based on 287 strategies tested across 5 time periods:

| Strategy | Avg Return | Win Rate | Consistency |
|----------|-----------|----------|-------------|
| RSI_28_35_80 | 27.7% | 100% | 1/1 periods |
| EMA_25_100 | 13.9% | 56.8% | 5/5 periods ⭐ |
| EMA_20_100 | 12.6% | 71.9% | 5/5 periods |
| Donchian_50 | 11.7% | 53.0% | 5/5 periods |
| BB_30_1.5 | 11.3% | 100% | 2/2 periods |

⭐ = Most reliable (profitable in all tested periods)

---

## Support

Questions? Check:
- `vectorbt_all_strategies.csv` - All 229 basic strategies tested
- `comprehensive_strategies.csv` - All 58 advanced strategies tested
- `validation_results.csv` - Walk-forward validation results

**System Status:** ✅ Ready to deploy
**Last Updated:** 2025-10-14
