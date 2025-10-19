@echo off
echo ================================================================================
echo     COMPLETE AUTONOMOUS SETUP
echo     Scheduled Reports + Real-Time Alerts
echo ================================================================================
echo.
echo This will configure your system to run COMPLETELY AUTONOMOUSLY:
echo.
echo   SYSTEM 1: Scheduled Reports
echo   - Sends 5 comprehensive reports daily
echo   - 06:00 AM, 10:00 AM, 02:00 PM, 06:00 PM, 10:00 PM
echo   - Full market analysis, all trade setups
echo.
echo   SYSTEM 2: Real-Time Alerts
echo   - Monitors markets continuously (every 5 minutes)
echo   - Instant email for high-confidence setups (^>75%%)
echo   - Major moves (^>2%%), breakouts, volume spikes
echo   - NEVER miss a great opportunity!
echo.
echo Both systems start on PC boot and run silently forever.
echo.
echo ================================================================================
pause
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges
    echo.
    echo Please:
    echo   1. Right-click this file
    echo   2. Select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

REM Get Python paths
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
if "%PYTHON_PATH%"=="" (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

set PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo Python found: %PYTHONW_PATH%
echo Script directory: %SCRIPT_DIR%
echo.

REM Create Task 1: Scheduled Reports
echo [1/2] Creating scheduled task for daily reports...
schtasks /create /tn "TradingReports_Scheduled" /tr "\"%PYTHONW_PATH%\" \"%SCRIPT_DIR%\auto_scheduler_reports.py\"" /sc onstart /delay 0002:00 /rl highest /f

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create scheduled reports task
    pause
    exit /b 1
)

echo [OK] Scheduled reports task created
echo.

REM Create Task 2: Real-Time Alerts
echo [2/2] Creating scheduled task for real-time alerts...
schtasks /create /tn "TradingReports_RealTimeAlerts" /tr "\"%PYTHONW_PATH%\" \"%SCRIPT_DIR%\real_time_signal_alerts.py\"" /sc onstart /delay 0003:00 /rl highest /f

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create real-time alerts task
    pause
    exit /b 1
)

echo [OK] Real-time alerts task created
echo.

echo ================================================================================
echo     SETUP COMPLETE!
echo ================================================================================
echo.
echo Your COMPLETE trading intelligence system is now autonomous!
echo.
echo What's configured:
echo   [✓] Scheduled Reports - 5x daily via email
echo   [✓] Real-Time Alerts  - Continuous monitoring every 5 min
echo   [✓] Auto-start on PC boot (2-min delay for system startup)
echo   [✓] Silent background execution (no windows)
echo   [✓] Auto-restart on failure
echo.
echo Both systems will start automatically when you boot your PC.
echo.
echo ================================================================================
echo.
choice /c YN /m "Do you want to start BOTH systems RIGHT NOW"
if errorlevel 2 goto end
if errorlevel 1 goto startnow

:startnow
echo.
echo Starting scheduled reports system...
start "" "%PYTHONW_PATH%" "%SCRIPT_DIR%\auto_scheduler_reports.py"
timeout /t 2 /nobreak > nul

echo Starting real-time alerts system...
start "" "%PYTHONW_PATH%" "%SCRIPT_DIR%\real_time_signal_alerts.py"
timeout /t 2 /nobreak > nul

echo.
echo [OK] Both systems started in background!
echo.
echo Check your email in 5-10 minutes for:
echo   - First scheduled report (if during scheduled time)
echo   - Real-time alerts (if market opportunities detected)
echo.
echo Logs:
echo   - report_scheduler.log (scheduled reports)
echo   - Console output for alerts
echo.

:end
echo ================================================================================
echo.
echo WHAT TO EXPECT:
echo.
echo SCHEDULED REPORTS (5x daily):
echo   06:00 AM - Pre-market analysis
echo   10:00 AM - Morning session review
echo   02:00 PM - Midday market update
echo   06:00 PM - Evening session review
echo   10:00 PM - End of day summary
echo.
echo REAL-TIME ALERTS (continuous):
echo   - High-confidence setups (^>75%% confidence)
echo   - Major price moves (^>2%% in 1 hour)
echo   - Breakouts from 50-period high/low
echo   - Volume spikes (2x normal)
echo   - Alerts sent with 60-min cooldown per symbol
echo.
echo TO CHECK STATUS:
echo   Run: CHECK_SYSTEM_STATUS.bat
echo.
echo TO STOP SYSTEMS:
echo   Task Manager ^> pythonw.exe ^> End Task
echo   Or disable tasks in Task Scheduler
echo.
echo ================================================================================
echo.
echo     YOU'RE ALL SET! ENJOY AUTONOMOUS TRADING INTELLIGENCE!
echo.
echo ================================================================================
pause
