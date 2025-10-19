@echo off
title Trading Reports - System Status
color 0A

:menu
cls
echo ================================================================================
echo     COMPLETE TRADING INTELLIGENCE - SYSTEM STATUS
echo ================================================================================
echo.

REM Count pythonw processes
for /f %%i in ('tasklist /fi "imagename eq pythonw.exe" 2^>NUL ^| find /c "pythonw.exe"') do set PROCESS_COUNT=%%i

if %PROCESS_COUNT% GTR 0 (
    echo Running Processes: [%PROCESS_COUNT%] Active
    echo.
    if %PROCESS_COUNT% EQU 2 (
        echo   [✓] COMPLETE SYSTEM Running (Scheduled + Alerts)
    ) else (
        echo   [!] Partial System Running (%PROCESS_COUNT%/2 systems)
    )
) else (
    echo Status: [STOPPED] No systems running
)
echo.

echo ================================================================================
echo     SYSTEM COMPONENTS
echo ================================================================================
echo.

REM Check Scheduled Reports Task
schtasks /query /tn "TradingReports_Scheduled" >NUL 2>&1
if "%ERRORLEVEL%"=="0" (
    echo [1] Scheduled Reports: [CONFIGURED]
    for /f "tokens=*" %%i in ('schtasks /query /tn "TradingReports_Scheduled" /fo list ^| findstr "Status:"') do echo     %%i
) else (
    echo [1] Scheduled Reports: [NOT CONFIGURED]
)

REM Check Real-Time Alerts Task
schtasks /query /tn "TradingReports_RealTimeAlerts" >NUL 2>&1
if "%ERRORLEVEL%"=="0" (
    echo [2] Real-Time Alerts: [CONFIGURED]
    for /f "tokens=*" %%i in ('schtasks /query /tn "TradingReports_RealTimeAlerts" /fo list ^| findstr "Status:"') do echo     %%i
) else (
    echo [2] Real-Time Alerts: [NOT CONFIGURED]
)

REM Check legacy task
schtasks /query /tn "TradingReports_Autonomous" >NUL 2>&1
if "%ERRORLEVEL%"=="0" (
    echo.
    echo [Legacy] Old Autonomous Task: [EXISTS] (can be deleted)
)

echo.
echo ================================================================================
echo     QUICK ACTIONS
echo ================================================================================
echo.
echo   1. View recent logs
echo   2. Start system now
echo   3. Stop system
echo   4. Restart system
echo   5. Open log file
echo   6. Check email schedule
echo   7. Exit
echo.
echo ================================================================================
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto viewlogs
if "%choice%"=="2" goto start
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto openlog
if "%choice%"=="6" goto schedule
if "%choice%"=="7" goto end
goto menu

:viewlogs
cls
echo ================================================================================
echo     RECENT LOG ENTRIES (Last 30 lines)
echo ================================================================================
echo.
if exist "report_scheduler.log" (
    powershell -command "Get-Content report_scheduler.log -Tail 30"
) else (
    echo No log file found yet. System hasn't run.
)
echo.
echo ================================================================================
pause
goto menu

:start
cls
echo ================================================================================
echo     STARTING SYSTEM
echo ================================================================================
echo.
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
set PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%

echo Starting autonomous trading reports...
start "" "%PYTHONW_PATH%" "%~dp0auto_scheduler_reports.py"
echo.
echo [OK] System started in background!
echo Check report_scheduler.log for activity.
echo.
timeout /t 3
goto menu

:stop
cls
echo ================================================================================
echo     STOPPING SYSTEM
echo ================================================================================
echo.
echo Stopping all pythonw.exe processes running auto_scheduler_reports.py...
taskkill /f /im pythonw.exe 2>NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] System stopped successfully
) else (
    echo [INFO] No running instances found
)
echo.
timeout /t 2
goto menu

:restart
cls
echo ================================================================================
echo     RESTARTING SYSTEM
echo ================================================================================
echo.
echo Stopping current instance...
taskkill /f /im pythonw.exe 2>NUL
timeout /t 2

echo.
echo Starting fresh instance...
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
set PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%
start "" "%PYTHONW_PATH%" "%~dp0auto_scheduler_reports.py"
echo.
echo [OK] System restarted!
echo.
timeout /t 3
goto menu

:openlog
cls
echo ================================================================================
echo     OPENING LOG FILE
echo ================================================================================
echo.
if exist "report_scheduler.log" (
    notepad report_scheduler.log
) else (
    echo No log file found yet.
    pause
)
goto menu

:schedule
cls
echo ================================================================================
echo     EMAIL REPORT SCHEDULE
echo ================================================================================
echo.
echo You receive 5 reports daily at:
echo.
echo   06:00 AM  -  Pre-market analysis
echo   10:00 AM  -  Morning session review
echo   02:00 PM  -  Midday market update
echo   06:00 PM  -  Evening session review
echo   10:00 PM  -  End of day summary
echo.
echo Total: 5 emails per day
echo.
echo To change schedule: Edit auto_scheduler_reports.py (line 20-26)
echo.
echo ================================================================================
pause
goto menu

:end
exit
