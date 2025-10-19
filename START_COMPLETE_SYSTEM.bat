@echo off
echo ================================================================================
echo     COMPLETE TRADING INTELLIGENCE SYSTEM
echo     Scheduled Reports + Real-Time Alerts
echo ================================================================================
echo.
echo This will start TWO monitoring systems:
echo.
echo   1. SCHEDULED REPORTS (5x daily)
echo      - 06:00 AM, 10:00 AM, 02:00 PM, 06:00 PM, 10:00 PM
echo      - Comprehensive market analysis
echo      - All trade setups and opportunities
echo.
echo   2. REAL-TIME ALERTS (Continuous)
echo      - Monitors markets every 5 minutes
echo      - Instant alerts for high-confidence setups (^>75%%)
echo      - Major price movements (^>2%%)
echo      - Breakouts and volume spikes
echo      - Never miss a great opportunity!
echo.
echo ================================================================================
pause
echo.

REM Find pythonw.exe for silent execution
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
if "%PYTHON_PATH%"=="" (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

set PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%
set SCRIPT_DIR=%~dp0

echo Starting scheduled report system...
start "Scheduled Reports" "%PYTHONW_PATH%" "%SCRIPT_DIR%auto_scheduler_reports.py"
timeout /t 2 /nobreak > nul

echo Starting real-time alert system...
start "Real-Time Alerts" "%PYTHONW_PATH%" "%SCRIPT_DIR%real_time_signal_alerts.py"
timeout /t 2 /nobreak > nul

echo.
echo ================================================================================
echo     BOTH SYSTEMS STARTED!
echo ================================================================================
echo.
echo What's running:
echo   [1] Scheduled Reports - 5 emails daily
echo   [2] Real-Time Alerts  - Instant notifications
echo.
echo Both systems are running in the background (hidden windows)
echo.
echo To check status:
echo   - Run: CHECK_SYSTEM_STATUS.bat
echo   - Or check Task Manager for pythonw.exe processes
echo.
echo To stop:
echo   - Task Manager ^> pythonw.exe ^> End Task
echo   - Or run: taskkill /f /im pythonw.exe
echo.
echo Check your email for alerts!
echo.
echo ================================================================================
pause
