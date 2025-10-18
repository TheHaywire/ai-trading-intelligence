# Setup Autonomous Operation - Set It and Forget It

## Overview

This guide will set up your trading report system to run **completely autonomously** 24/7. You'll receive emails automatically without any manual intervention.

## Method 1: Windows Task Scheduler (Recommended - Runs on PC Startup)

### Step-by-Step Setup (5 Minutes)

#### 1. Open Task Scheduler
- Press `Win + R`
- Type: `taskschd.msc`
- Press Enter

#### 2. Create New Task
- Click "Create Task" (not "Create Basic Task")
- Name: `Daily Trading Reports - Autonomous`
- Description: `Automated quantitative trading analysis - sends 5 reports daily`
- ✅ Check "Run whether user is logged on or not"
- ✅ Check "Run with highest privileges"
- ✅ Check "Hidden" (runs silently in background)

#### 3. Triggers Tab
Click "New" and configure:

**Trigger 1: At Startup**
- Begin the task: `At startup`
- Delay task for: `2 minutes`
- ✅ Enabled

**Why?** This ensures the system starts automatically when your PC boots.

#### 4. Actions Tab
Click "New" and configure:

- Action: `Start a program`
- Program/script: `pythonw.exe` (note the 'w' - runs hidden)
- Add arguments: `auto_scheduler_reports.py`
- Start in: `C:\Users\manan\OneDrive\Desktop\PropShop- IF`

**Important:** Use `pythonw.exe` (not `python.exe`) to run without showing a window!

#### 5. Conditions Tab
- ✅ Uncheck "Start the task only if the computer is on AC power"
- ✅ Check "Wake the computer to run this task"

#### 6. Settings Tab
- ✅ Allow task to be run on demand
- ✅ If the task fails, restart every: `10 minutes`
- ✅ Attempt to restart up to: `3 times`
- ✅ If the running task does not end when requested, force it to stop
- Stop the task if it runs longer than: `3 hours`

#### 7. Save Task
- Click "OK"
- Enter your Windows password when prompted
- Task is now created!

### Verify It's Working

1. Right-click the task → "Run"
2. Check Task Scheduler → Task should show "Running"
3. Wait 5 minutes
4. Check your email - you should receive the first report
5. Check `C:\Users\manan\OneDrive\Desktop\PropShop- IF\report_scheduler.log`

### Start It Now (Without Rebooting)

Option A: Through Task Scheduler
- Find your task in Task Scheduler
- Right-click → "Run"

Option B: Command Line
```cmd
schtasks /run /tn "Daily Trading Reports - Autonomous"
```

---

## Method 2: Windows Service (Advanced - True Background Service)

For ultimate reliability, convert to a Windows Service:

### Install NSSM (Non-Sucking Service Manager)

1. Download NSSM: https://nssm.cc/download
2. Extract to `C:\nssm`
3. Open Command Prompt as Administrator

```cmd
cd C:\nssm\win64

nssm install TradingReports "C:\Users\manan\AppData\Local\Programs\Python\Python311\pythonw.exe" "C:\Users\manan\OneDrive\Desktop\PropShop- IF\auto_scheduler_reports.py"

nssm set TradingReports AppDirectory "C:\Users\manan\OneDrive\Desktop\PropShop- IF"
nssm set TradingReports DisplayName "Autonomous Trading Reports"
nssm set TradingReports Description "Sends 5 quantitative trading reports daily via email"
nssm set TradingReports Start SERVICE_AUTO_START

nssm start TradingReports
```

**Verify Service:**
```cmd
nssm status TradingReports
```

**Service Commands:**
```cmd
nssm stop TradingReports     # Stop service
nssm start TradingReports    # Start service
nssm restart TradingReports  # Restart service
nssm remove TradingReports   # Remove service (confirm when prompted)
```

---

## Method 3: Startup Folder (Simplest - But Shows Window)

### Quick Setup

1. Press `Win + R`
2. Type: `shell:startup`
3. Press Enter
4. Copy `START_AUTOMATED_REPORTS.bat` into this folder

**That's it!** The system will start every time you log in to Windows.

**Drawback:** Shows a command window (can minimize it)

---

## Method 4: VPS Cloud Deployment (24/7 Even When PC is Off)

### Why Use a VPS?

- Runs 24/7 even when your PC is off
- More reliable internet connection
- Professional uptime (99.9%+)
- Cost: $3-10/month

### Recommended VPS Providers

1. **Vultr** - $3.50/month (cheapest)
2. **DigitalOcean** - $5/month (most popular)
3. **AWS EC2** - Free tier for 12 months
4. **Contabo** - $4.50/month (best value)

### Setup on VPS (Windows Server)

1. **Create VPS** with Windows Server 2019/2022
2. **Connect via RDP** (Remote Desktop)
3. **Install Python:**
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add to PATH"
   - Install

4. **Install MT5:**
   - Download from broker
   - Login to account
   - Enable AutoTrading

5. **Upload Trading System:**
   ```cmd
   # Use RDP to copy files, or:
   git clone https://github.com/TheHaywire/ai-trading-intelligence.git
   cd ai-trading-intelligence
   ```

6. **Install Dependencies:**
   ```cmd
   pip install MetaTrader5 pandas numpy requests schedule
   ```

7. **Configure Email:**
   - Edit `exhaustive_daily_quant_report.py`
   - Update `EMAIL_TO` with your email

8. **Setup Task Scheduler** (follow Method 1 above)

9. **Disconnect RDP** - System keeps running!

---

## Monitoring Your Autonomous System

### Check If It's Running

**Windows Task Manager:**
1. Press `Ctrl + Shift + Esc`
2. Go to "Details" tab
3. Look for `pythonw.exe` with command line containing `auto_scheduler_reports.py`

**Command Line:**
```cmd
tasklist | findstr pythonw
```

**Task Scheduler:**
- Open Task Scheduler
- Check "Task Scheduler Library"
- Your task should show "Running" or "Ready"

### View Logs

Check the log file:
```cmd
type "C:\Users\manan\OneDrive\Desktop\PropShop- IF\report_scheduler.log"
```

**Tail logs in real-time** (PowerShell):
```powershell
Get-Content "C:\Users\manan\OneDrive\Desktop\PropShop- IF\report_scheduler.log" -Wait -Tail 20
```

### Email Schedule

You'll receive reports at:
- **06:00 AM** - Pre-market analysis
- **10:00 AM** - Morning session
- **02:00 PM** - Midday update
- **06:00 PM** - Evening session
- **10:00 PM** - End of day summary

**Total: 5 emails per day**

### Check Last Run

Log file shows:
```
2025-10-19 06:00:03 - INFO - SCHEDULED REPORT TRIGGER
2025-10-19 06:00:03 - INFO - EXECUTING DAILY REPORT
2025-10-19 06:02:15 - INFO - [OK] Email sent successfully
2025-10-19 06:02:15 - INFO - Next report scheduled for: 2025-10-19 10:00:00
```

---

## Troubleshooting Autonomous Operation

### System Not Starting Automatically

**Check Task Scheduler:**
1. Task status shows "Disabled" → Right-click → Enable
2. Task shows error → Check "Last Run Result" column
3. "Triggers" misconfigured → Edit trigger settings

**Check Windows Event Viewer:**
1. Press `Win + R` → `eventvwr.msc`
2. Windows Logs → Application
3. Look for errors from Task Scheduler

### Reports Not Being Sent

**Check MT5:**
- Is MT5 running?
- Is account logged in?
- Is "AutoTrading" enabled?

**Check Email Limits:**
- EmailJS free tier: 200 emails/month
- 5 reports/day × 30 days = 150 emails/month (within limit)
- Check https://dashboard.emailjs.com for usage

**Check Internet:**
- System requires internet for email delivery
- MT5 requires internet for market data

### High CPU Usage

**Normal during report generation** (2-5 minutes every report)
- Scanning 65+ instruments
- Calculating 20+ indicators each
- Returns to idle after report sent

**Reduce load:**
Edit `exhaustive_daily_quant_report.py`:
```python
# Scan fewer instruments
MARKET_UNIVERSE = {
    'Forex Majors': ['EURUSD', 'GBPUSD', 'USDJPY']
}
```

### PC Goes to Sleep

**Prevent sleep during scheduled times:**

Windows Settings:
1. Settings → System → Power & Sleep
2. Set "Sleep" to "Never" (when plugged in)

OR use this command (run as Administrator):
```cmd
powercfg -change -standby-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0
```

---

## Stopping/Pausing the System

### Temporary Pause (Resume Later)

**Task Scheduler Method:**
1. Open Task Scheduler
2. Right-click task → "Disable"
3. To resume: Right-click → "Enable"

**Kill Process Method:**
```cmd
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq auto_scheduler_reports.py"
```

### Permanent Stop

**Remove Task:**
1. Task Scheduler → Find task
2. Right-click → "Delete"

**Remove Service (if using NSSM):**
```cmd
nssm stop TradingReports
nssm remove TradingReports confirm
```

**Remove from Startup Folder:**
1. `Win + R` → `shell:startup`
2. Delete the .bat file

---

## Recommended Setup for You

### Best Configuration: Task Scheduler + Auto-Start

**Why?**
- ✅ Runs on PC startup automatically
- ✅ No window visible (silent operation)
- ✅ Auto-restarts on failure
- ✅ Easy to monitor in Task Scheduler
- ✅ Free (no VPS needed)

**Your Action Plan:**

1. **Now:** Follow "Method 1: Windows Task Scheduler" above (5 minutes)
2. **Start:** Right-click task → "Run"
3. **Verify:** Check email in 5 minutes
4. **Forget:** System runs autonomously forever!

### When to Consider VPS

Use VPS if:
- ❌ Your PC isn't on 24/7
- ❌ Unreliable internet at home
- ❌ Want true 24/7 operation
- ✅ Trading is your business
- ✅ Worth $5-10/month for reliability

---

## System is Now Autonomous! ✅

Once setup, the system:

✅ **Starts automatically** when PC boots
✅ **Runs in background** (completely invisible)
✅ **Scans markets** 5 times daily
✅ **Sends email reports** automatically
✅ **Recovers from errors** (auto-retry)
✅ **Logs everything** for your review
✅ **Never needs manual intervention**

### Your Only Job

📧 **Check your email** whenever you want:
- Morning: See pre-market & morning reports
- Afternoon: Review midday update
- Evening: Check evening & EOD reports

**Trading opportunities delivered to your inbox - completely hands-free!**

---

## Quick Reference Commands

```cmd
# Check if running
tasklist | findstr pythonw

# View logs
type report_scheduler.log

# Start manually
START_AUTOMATED_REPORTS.bat

# Stop running instance
taskkill /f /im pythonw.exe

# Run scheduled task
schtasks /run /tn "Daily Trading Reports - Autonomous"

# Check task status
schtasks /query /tn "Daily Trading Reports - Autonomous"
```

---

**System Status: 🟢 AUTONOMOUS**

Set it up once, receive insights forever! 🚀📈
