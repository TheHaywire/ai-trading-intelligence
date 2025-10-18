@echo off
echo ================================================================================
echo     AUTONOMOUS TRADING REPORTS - ONE-CLICK SETUP
echo     This will configure your system to run automatically 24/7
echo ================================================================================
echo.
echo This script will:
echo   1. Create a Windows Task that runs on PC startup
echo   2. Configure it to run silently in the background
echo   3. Auto-restart on failures
echo   4. Send you 5 email reports daily
echo.
echo You'll receive reports at: 6 AM, 10 AM, 2 PM, 6 PM, 10 PM
echo.
echo ================================================================================
pause
echo.
echo Setting up autonomous operation...
echo.

REM Get Python path
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
if "%PYTHON_PATH%"=="" (
    echo [ERROR] Python not found in PATH
    echo Please ensure Python is installed and in your PATH
    pause
    exit /b 1
)

REM Replace python.exe with pythonw.exe for silent execution
set PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%

echo Found Python: %PYTHONW_PATH%
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo Script directory: %SCRIPT_DIR%
echo.

REM Create the scheduled task
echo Creating Windows scheduled task...
echo.

schtasks /create /tn "TradingReports_Autonomous" /tr "\"%PYTHONW_PATH%\" \"%SCRIPT_DIR%\auto_scheduler_reports.py\"" /sc onstart /delay 0002:00 /rl highest /f

if %ERRORLEVEL% EQU 0 (
    echo [OK] Task created successfully!
    echo.
    echo ================================================================================
    echo     SETUP COMPLETE!
    echo ================================================================================
    echo.
    echo Your trading report system is now autonomous!
    echo.
    echo What happens next:
    echo   - System will start automatically when you boot your PC
    echo   - Runs silently in the background (no windows)
    echo   - Sends 5 email reports daily
    echo   - Auto-restarts if it crashes
    echo.
    echo To start it NOW (without rebooting):
    echo   1. This script will start it for you, OR
    echo   2. Double-click START_AUTOMATED_REPORTS.bat
    echo.
    echo To check status:
    echo   - Open Task Scheduler
    echo   - Look for "TradingReports_Autonomous"
    echo.
    echo To stop:
    echo   - Open Task Scheduler
    echo   - Right-click "TradingReports_Autonomous" ^> Disable
    echo.
    echo ================================================================================
    echo.
    choice /c YN /m "Do you want to start the system RIGHT NOW"
    if errorlevel 2 goto end
    if errorlevel 1 goto startnow
) else (
    echo [ERROR] Failed to create scheduled task
    echo.
    echo This might be because:
    echo   1. Script not run as Administrator
    echo   2. Task already exists
    echo.
    echo Solutions:
    echo   - Right-click this file ^> Run as Administrator
    echo   - Or manually delete existing task in Task Scheduler
    echo.
    pause
    exit /b 1
)

:startnow
echo.
echo Starting the autonomous system now...
echo.
start "" "%PYTHONW_PATH%" "%SCRIPT_DIR%\auto_scheduler_reports.py"
echo.
echo [OK] System started in background!
echo.
echo Check your email in 5 minutes for the first report.
echo Also check: %SCRIPT_DIR%\report_scheduler.log
echo.

:end
echo ================================================================================
echo.
echo Setup complete! Your system is now autonomous.
echo.
echo     YOU CAN CLOSE THIS WINDOW
echo.
echo ================================================================================
pause
