# Automated Email Reports Setup Guide

## Overview

Get **comprehensive trading reports delivered to your email automatically** at regular intervals throughout the day. Never miss a trading opportunity!

## What You'll Get

### Report Frequency (Configurable)
**Default Schedule: 5 Reports Daily**
- 📧 **06:00 AM** - Pre-market analysis
- 📧 **10:00 AM** - Morning session review
- 📧 **02:00 PM** - Midday market update
- 📧 **06:00 PM** - Evening session review
- 📧 **10:00 PM** - End-of-day summary

**Or** customize to any interval (e.g., every 2, 4, 6 hours)

### Each Report Contains
✅ **65+ instruments** scanned across all markets
✅ **High-probability trade setups** with precise entry/exit/stops
✅ **20+ technical indicators** per instrument
✅ **Market overview** with sentiment analysis
✅ **Top movers** and breakout opportunities
✅ **Risk calendar** with upcoming events
✅ **Performance tracking** of yesterday's trades
✅ **Beautiful HTML format** optimized for mobile & desktop

## Quick Setup (5 Minutes)

### Option 1: Use Batch Files (Easiest - Windows)

#### For Automated Reports (Multiple Times Daily)
1. **Double-click**: `START_AUTOMATED_REPORTS.bat`
2. Choose option 2 to run first report immediately
3. Leave window open - reports will auto-send at scheduled times
4. Minimize window and continue your day

#### For Single Report (On-Demand)
1. **Double-click**: `RUN_SINGLE_REPORT.bat`
2. Wait 2-5 minutes for completion
3. Check your email!

### Option 2: Command Line

```bash
# Install dependencies (one-time)
pip install schedule

# Run automated scheduler
python auto_scheduler_reports.py

# Or run single report
python exhaustive_daily_quant_report.py
```

## Configuration Options

### Change Report Times

Edit `auto_scheduler_reports.py` line 20-26:

```python
# Default: 5 times daily
REPORT_INTERVALS = [
    "06:00",  # 6 AM
    "10:00",  # 10 AM
    "14:00",  # 2 PM
    "18:00",  # 6 PM
    "22:00"   # 10 PM
]
```

**Custom Examples:**

**Every 4 Hours (6 reports/day):**
```python
REPORT_INTERVALS = [
    "00:00", "04:00", "08:00", "12:00", "16:00", "20:00"
]
```

**Business Hours Only (3 reports/day):**
```python
REPORT_INTERVALS = [
    "09:00",  # Market open
    "13:00",  # Lunch
    "17:00"   # Market close
]
```

**Continuous Interval (Every X Hours):**
```python
# Comment out REPORT_INTERVALS and add:
CONTINUOUS_INTERVAL_HOURS = 3  # Every 3 hours
```

### Change Email Address

Edit `exhaustive_daily_quant_report.py` line 25:

```python
EMAIL_TO = "your-email@example.com"  # Change this
```

**Multiple Recipients:**
Edit the `send_email_report()` function to send to multiple addresses:
```python
RECIPIENTS = [
    "trader1@example.com",
    "trader2@example.com",
    "alerts@yourcompany.com"
]
```

### Adjust Market Coverage

Edit `exhaustive_daily_quant_report.py` line 42-51 to add/remove markets:

```python
MARKET_UNIVERSE = {
    'Forex Majors': ['EURUSD', 'GBPUSD', 'USDJPY'],  # Customize symbols
    'Crypto': ['BTCUSD', 'ETHUSD'],  # Add/remove
    # Add your own categories
    'Your Watchlist': ['SYMBOL1', 'SYMBOL2']
}
```

### Change Risk Parameters

Edit `exhaustive_daily_quant_report.py` line 54-61:

```python
RISK_PARAMS = {
    'max_risk_per_trade': 1.5,     # Change from 2.0 to 1.5% for conservative
    'max_positions': 3,            # Reduce from 5 to 3
    'min_reward_risk': 2.5,        # Increase from 2.0 to 2.5 for better R:R
}
```

## Running as Background Service

### Windows - Task Scheduler (Auto-Start on Boot)

1. **Open Task Scheduler**: `Win + R` → type `taskschd.msc` → Enter

2. **Create Basic Task**:
   - Name: "Daily Trading Reports"
   - Description: "Automated quantitative trading analysis"

3. **Trigger**:
   - "When I log on" (or "At startup" for dedicated trading PC)

4. **Action**:
   - Program: `C:\Windows\System32\cmd.exe`
   - Arguments: `/c "C:\Users\manan\OneDrive\Desktop\PropShop- IF\START_AUTOMATED_REPORTS.bat"`
   - Start in: `C:\Users\manan\OneDrive\Desktop\PropShop- IF`

5. **Conditions**:
   - ✅ Wake computer to run this task
   - ✅ Run whether user is logged on or not

6. **Settings**:
   - ✅ Allow task to be run on demand
   - ✅ If task fails, restart every: 10 minutes

7. **Save** and enter your Windows password

Now reports will auto-send even if you forget to start the script!

### Linux/Mac - Cron Job

Add to crontab (`crontab -e`):

```bash
# Run every 4 hours
0 */4 * * * cd /path/to/PropShop-IF && python3 exhaustive_daily_quant_report.py

# Or run scheduler on boot
@reboot cd /path/to/PropShop-IF && python3 auto_scheduler_reports.py
```

### Running on VPS/Cloud Server (24/7)

**Why?** Ensure reports are sent even when your PC is off.

**Options:**
- AWS EC2 (t2.micro - free tier)
- DigitalOcean Droplet ($5/month)
- Vultr VPS ($3.50/month)
- Any Windows/Linux VPS

**Setup:**
1. Upload project files to VPS
2. Install Python and dependencies
3. Setup cron job or systemd service
4. Reports will send 24/7 automatically

## Monitoring & Logs

### View Scheduler Logs

Check `report_scheduler.log` for:
- Execution timestamps
- Success/failure status
- Error messages
- Next scheduled run time

**Tail logs in real-time** (Linux/Mac):
```bash
tail -f report_scheduler.log
```

**View logs** (Windows):
```bash
type report_scheduler.log
```

### Email Delivery Confirmation

Each successful report logs:
```
✅ Email sent successfully to manankharbanda99@gmail.com
```

If email fails:
```
❌ Email failed: HTTP 429 (rate limit)
```

**Solutions:**
- EmailJS free tier: 200 emails/month limit
- Upgrade to paid plan for unlimited
- Or use alternative: Gmail SMTP, SendGrid, Mailgun

### Report Output Files

Each run creates:
- **HTML Report**: `daily_quant_report_YYYYMMDD_HHMMSS.html`
- **Log Entry**: Added to `report_scheduler.log`
- **Trade History**: Updated in `trades_log.json` (if trades logged)

**Automatic Cleanup** (Optional):

Add to `auto_scheduler_reports.py`:
```python
# Delete reports older than 7 days
import glob
from datetime import datetime, timedelta

def cleanup_old_reports():
    cutoff = datetime.now() - timedelta(days=7)
    for file in glob.glob("daily_quant_report_*.html"):
        file_time = datetime.fromtimestamp(os.path.getmtime(file))
        if file_time < cutoff:
            os.remove(file)
            logger.info(f"Deleted old report: {file}")
```

## Troubleshooting

### Reports Not Sending

**Check 1: Scheduler Running?**
```bash
# Should see python process
ps aux | grep auto_scheduler  # Linux/Mac
tasklist | findstr python     # Windows
```

**Check 2: Email Configuration**
```python
# Verify in exhaustive_daily_quant_report.py
EMAIL_TO = "correct-email@example.com"
```

**Check 3: EmailJS Limits**
- Free tier: 200 emails/month
- Check https://dashboard.emailjs.com

**Check 4: MT5 Running?**
- Reports require MT5 to be running
- Must be logged into trading account
- Enable "Allow automated trading" in settings

### Script Crashes

**Error: "MT5 initialization failed"**
- Start MetaTrader 5
- Login to account
- Re-run script

**Error: "Module not found"**
```bash
# Reinstall dependencies
pip install --upgrade MetaTrader5 pandas numpy requests schedule
```

**Error: "Symbol not found"**
- Check symbol names match your broker
- Edit `MARKET_UNIVERSE` to use correct symbols

### High CPU Usage

**Normal during report generation** (2-5 minutes)
- Scanning 65+ instruments
- Calculating 20+ indicators each
- CPU returns to normal after completion

**Reduce load:**
```python
# Scan fewer instruments
MARKET_UNIVERSE = {
    'Forex Majors': ['EURUSD', 'GBPUSD', 'USDJPY']  # Only 3 instead of 65
}

# Or increase interval between reports
CONTINUOUS_INTERVAL_HOURS = 6  # Instead of 4
```

## Advanced Features

### Conditional Reports

Only send report if opportunities found:

```python
# In exhaustive_daily_quant_report.py, modify main():
if len(scan_results['high_probability_setups']) >= 3:
    send_email_report(subject, html_report)
else:
    print("No significant opportunities - skipping email")
```

### SMS/WhatsApp Alerts

Use Twilio for critical setups:

```python
from twilio.rest import Client

def send_sms_alert(message):
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(
        body=message,
        from_='+1234567890',
        to='+0987654321'
    )

# In report generation:
if setup['confidence'] > 80:
    send_sms_alert(f"HIGH CONFIDENCE: {setup['symbol']} - {setup['direction']}")
```

### Telegram Bot Integration

```python
import requests

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    })
```

### Webhook Integration (Trading View, Discord, Slack)

```python
# Discord Webhook
def send_discord_webhook(content):
    webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK"
    requests.post(webhook_url, json={"content": content})

# In report:
for setup in high_probability_setups:
    discord_message = f"🎯 **{setup['symbol']}** | {setup['direction']} | Confidence: {setup['confidence']}%"
    send_discord_webhook(discord_message)
```

## Performance Optimization

### Speed Up Scans

**Parallel Processing:**
```python
from concurrent.futures import ThreadPoolExecutor

def scan_all_markets_parallel(self):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for category, symbols in MARKET_UNIVERSE.items():
            for symbol in symbols:
                future = executor.submit(self.scan_symbol, symbol, category)
                futures.append(future)

        results = [f.result() for f in futures]
    return results
```

**Reduces scan time from 3-5 minutes to 30-60 seconds!**

### Database Storage (Optional)

Store results in SQLite for historical analysis:

```python
import sqlite3

def save_to_database(scan_results):
    conn = sqlite3.connect('trading_reports.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS scans
                     (timestamp TEXT, symbol TEXT, confidence REAL,
                      direction TEXT, entry REAL, stop_loss REAL)''')

    for result in scan_results['high_probability_setups']:
        cursor.execute("INSERT INTO scans VALUES (?,?,?,?,?,?)",
                      (datetime.now(), result['symbol'],
                       result['setup']['confidence'], ...))

    conn.commit()
    conn.close()
```

## Best Practices

### Do's ✅
1. **Keep MT5 running** 24/7 on dedicated machine/VPS
2. **Monitor logs** daily for errors
3. **Review email spam folder** initially (whitelist sender)
4. **Test with single report** before enabling automation
5. **Backup configuration** files regularly
6. **Update email** if changed
7. **Review performance** metrics weekly

### Don'ts ❌
1. **Don't close MT5** while scheduler is running
2. **Don't modify scripts** while execution is in progress
3. **Don't exceed EmailJS limits** (upgrade if needed)
4. **Don't ignore failed reports** - investigate immediately
5. **Don't run multiple schedulers** simultaneously (duplicates)

## Support Checklist

Before asking for help, verify:
- [ ] MT5 is running and logged in
- [ ] Python dependencies installed (`pip list`)
- [ ] Email address is correct
- [ ] Scheduler logs show no errors
- [ ] Test script runs manually: `python exhaustive_daily_quant_report.py`
- [ ] Internet connection is stable
- [ ] Antivirus not blocking Python

## Summary

You now have a **fully automated trading intelligence system** that:
- ✅ Scans 65+ global markets
- ✅ Identifies high-probability setups
- ✅ Calculates precise entry/exit/stops
- ✅ Emails comprehensive reports 5x daily (or custom)
- ✅ Tracks performance and learns
- ✅ Runs 24/7 in background

**Just double-click `START_AUTOMATED_REPORTS.bat` and let it run!**

Your trading edge is now on autopilot. 🚀📈

---

**Questions?** Check `README_DAILY_QUANT_REPORT.md` or `QUICK_START_GUIDE.md`
