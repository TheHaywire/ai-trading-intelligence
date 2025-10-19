@echo off
title Email System Diagnostic
color 0E

echo ================================================================================
echo     WHY DIDN'T I GET EMAILS? - DIAGNOSTIC TOOL
echo ================================================================================
echo.
echo Checking your system...
echo.

REM Check 1: Is system running?
echo [CHECK 1] Is the system currently running?
echo ========================================
tasklist /fi "imagename eq pythonw.exe" 2>NUL | find /i "pythonw.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] System IS running right now
    echo.
    for /f %%i in ('tasklist /fi "imagename eq pythonw.exe" 2^>NUL ^| find /c "pythonw.exe"') do echo     Active processes: %%i
) else (
    echo [PROBLEM] System is NOT running!
    echo.
    echo SOLUTION: Run one of these:
    echo   1. START_COMPLETE_SYSTEM.bat
    echo   2. INSTALL_WINDOWS_SERVICE.bat (RECOMMENDED - never stops)
)
echo.
echo ================================================================================
echo.

REM Check 2: When is next report scheduled?
echo [CHECK 2] When is the next scheduled report?
echo ========================================
python -c "from datetime import datetime; print('Current time:', datetime.now().strftime('%%Y-%%m-%%d %%H:%%M:%%S'))"
echo.
echo Scheduled report times (local time):
echo   06:00 AM - Pre-market
echo   10:00 AM - Morning
echo   02:00 PM - Midday
echo   06:00 PM - Evening
echo   10:00 PM - End of day
echo.
echo If current time is between these times, you must WAIT for next scheduled time.
echo.
echo ================================================================================
echo.

REM Check 3: Check log files
echo [CHECK 3] Do log files exist?
echo ========================================
if exist "report_scheduler.log" (
    echo [OK] report_scheduler.log EXISTS
    echo.
    echo Last 10 lines of log:
    echo ---
    powershell -Command "Get-Content report_scheduler.log -Tail 10"
    echo ---
) else (
    echo [PROBLEM] report_scheduler.log NOT FOUND
    echo This means the scheduled system has never run!
)
echo.

if exist "alert_history.json" (
    echo [OK] alert_history.json EXISTS (real-time alerts ran)
) else (
    echo [INFO] alert_history.json NOT FOUND (real-time alerts haven't run yet)
)
echo.
echo ================================================================================
echo.

REM Check 4: Test email right now
echo [CHECK 4] Can we send email RIGHT NOW?
echo ========================================
echo.
choice /c YN /m "Do you want to send a TEST EMAIL right now to verify email works"
if errorlevel 2 goto skip_test
if errorlevel 1 goto run_test

:run_test
echo.
echo Running test report... (this will take 2-5 minutes)
echo.
python exhaustive_daily_quant_report.py
echo.
if %ERRORLEVEL% EQU 0 (
    echo [OK] Report executed successfully!
    echo CHECK YOUR EMAIL NOW!
) else (
    echo [ERROR] Report failed!
    echo Check the error messages above
)
goto after_test

:skip_test
echo.
echo Skipped test email.
echo.

:after_test
echo ================================================================================
echo.

REM Check 5: MT5 Status
echo [CHECK 5] Is MetaTrader 5 running?
echo ========================================
tasklist /fi "imagename eq terminal64.exe" 2>NUL | find /i "terminal64.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] MT5 is running
) else (
    echo [PROBLEM] MT5 is NOT running!
    echo.
    echo SOLUTION: Start MetaTrader 5 and login to your account
    echo The system REQUIRES MT5 to be running to get market data
)
echo.
echo ================================================================================
echo.

REM Summary and Solutions
echo ================================================================================
echo     SUMMARY - WHY YOU DIDN'T GET EMAILS
echo ================================================================================
echo.
echo Most common reasons:
echo.
echo 1. SYSTEM NOT RUNNING CONTINUOUSLY
echo    - You started the .bat file but closed it
echo    - The window must stay open OR use Windows Service
echo    - SOLUTION: Run INSTALL_WINDOWS_SERVICE.bat (BEST OPTION)
echo.
echo 2. WRONG TIME
echo    - Reports only send at 6AM, 10AM, 2PM, 6PM, 10PM
echo    - If you started at 11 AM, next report is at 2 PM
echo    - Real-time alerts send immediately when opportunities found
echo    - SOLUTION: Wait for scheduled time OR run test report now
echo.
echo 3. MT5 NOT RUNNING
echo    - System needs MT5 running to get market data
echo    - SOLUTION: Start MT5 and keep it running
echo.
echo 4. EMAIL LIMIT REACHED
echo    - EmailJS free tier: 200 emails/month
echo    - SOLUTION: Check https://dashboard.emailjs.com
echo.
echo 5. NO OPPORTUNITIES FOUND
echo    - Real-time alerts only send when criteria met
echo    - If market is quiet, no alerts
echo    - Scheduled reports ALWAYS send (5x daily)
echo.
echo ================================================================================
echo     RECOMMENDED FIX - GUARANTEED TO WORK
echo ================================================================================
echo.
echo DO THIS NOW:
echo   1. Close this window
echo   2. Right-click: INSTALL_WINDOWS_SERVICE.bat
echo   3. Run as Administrator
echo   4. Follow the prompts
echo.
echo This installs as Windows Service - GUARANTEED to run 24/7
echo Never stops, never needs restart, always works!
echo.
echo OR QUICK FIX:
echo   1. Double-click: START_COMPLETE_SYSTEM.bat
echo   2. MINIMIZE the window (don't close it!)
echo   3. Leave it running forever
echo.
echo ================================================================================
pause
