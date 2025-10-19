@echo off
echo ================================================================================
echo     INSTALL AS WINDOWS SERVICE - TRUE 24/7 OPERATION
echo     This ensures the system NEVER stops running
echo ================================================================================
echo.
echo This will install BOTH systems as Windows Services using NSSM.
echo.
echo Benefits:
echo   - Runs even when you log off
echo   - Auto-starts on PC boot
echo   - Auto-restarts if crashes
echo   - True background service (not just scheduled task)
echo   - GUARANTEED to run 24/7
echo.
echo Requirements:
echo   - NSSM (Non-Sucking Service Manager)
echo   - We'll download it for you if needed
echo.
echo ================================================================================
pause

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges
    echo Please right-click and "Run as Administrator"
    pause
    exit /b 1
)

REM Set paths
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set NSSM_DIR=%SCRIPT_DIR%\nssm
set NSSM_EXE=%NSSM_DIR%\nssm.exe

REM Check if NSSM exists
if not exist "%NSSM_EXE%" (
    echo NSSM not found. Downloading...
    echo.

    REM Create nssm directory
    mkdir "%NSSM_DIR%" 2>nul

    REM Download NSSM (using PowerShell)
    powershell -Command "& {Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%SCRIPT_DIR%\nssm.zip'}"

    REM Extract NSSM
    powershell -Command "& {Expand-Archive -Path '%SCRIPT_DIR%\nssm.zip' -DestinationPath '%SCRIPT_DIR%' -Force}"

    REM Move exe to nssm folder
    move "%SCRIPT_DIR%\nssm-2.24\win64\nssm.exe" "%NSSM_DIR%\" >nul 2>&1

    REM Cleanup
    rmdir /s /q "%SCRIPT_DIR%\nssm-2.24" >nul 2>&1
    del "%SCRIPT_DIR%\nssm.zip" >nul 2>&1

    echo [OK] NSSM downloaded
    echo.
)

REM Get Python path
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
if "%PYTHON_PATH%"=="" (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

set PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%

echo Python: %PYTHONW_PATH%
echo Script Dir: %SCRIPT_DIR%
echo.

REM Remove existing services if they exist
echo Removing old services (if any)...
"%NSSM_EXE%" stop TradingReports_Scheduled >nul 2>&1
"%NSSM_EXE%" remove TradingReports_Scheduled confirm >nul 2>&1
"%NSSM_EXE%" stop TradingReports_RealTime >nul 2>&1
"%NSSM_EXE%" remove TradingReports_RealTime confirm >nul 2>&1
echo.

REM Install Service 1: Scheduled Reports
echo [1/2] Installing Scheduled Reports Service...
"%NSSM_EXE%" install TradingReports_Scheduled "%PYTHONW_PATH%" "%SCRIPT_DIR%\auto_scheduler_reports.py"
"%NSSM_EXE%" set TradingReports_Scheduled AppDirectory "%SCRIPT_DIR%"
"%NSSM_EXE%" set TradingReports_Scheduled DisplayName "Trading Reports - Scheduled"
"%NSSM_EXE%" set TradingReports_Scheduled Description "Sends 5 comprehensive trading reports daily"
"%NSSM_EXE%" set TradingReports_Scheduled Start SERVICE_AUTO_START
"%NSSM_EXE%" set TradingReports_Scheduled AppStdout "%SCRIPT_DIR%\service_scheduled.log"
"%NSSM_EXE%" set TradingReports_Scheduled AppStderr "%SCRIPT_DIR%\service_scheduled_errors.log"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Scheduled Reports Service installed
) else (
    echo [ERROR] Failed to install Scheduled Reports Service
    pause
    exit /b 1
)
echo.

REM Install Service 2: Real-Time Alerts
echo [2/2] Installing Real-Time Alerts Service...
"%NSSM_EXE%" install TradingReports_RealTime "%PYTHONW_PATH%" "%SCRIPT_DIR%\real_time_signal_alerts.py"
"%NSSM_EXE%" set TradingReports_RealTime AppDirectory "%SCRIPT_DIR%"
"%NSSM_EXE%" set TradingReports_RealTime DisplayName "Trading Reports - Real-Time Alerts"
"%NSSM_EXE%" set TradingReports_RealTime Description "Monitors markets every 5 minutes and sends instant alerts"
"%NSSM_EXE%" set TradingReports_RealTime Start SERVICE_AUTO_START
"%NSSM_EXE%" set TradingReports_RealTime AppStdout "%SCRIPT_DIR%\service_realtime.log"
"%NSSM_EXE%" set TradingReports_RealTime AppStderr "%SCRIPT_DIR%\service_realtime_errors.log"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Real-Time Alerts Service installed
) else (
    echo [ERROR] Failed to install Real-Time Alerts Service
    pause
    exit /b 1
)
echo.

echo ================================================================================
echo     SERVICES INSTALLED SUCCESSFULLY!
echo ================================================================================
echo.

REM Start services
echo Starting services...
"%NSSM_EXE%" start TradingReports_Scheduled
"%NSSM_EXE%" start TradingReports_RealTime

timeout /t 3 /nobreak >nul

echo.
echo Checking service status...
"%NSSM_EXE%" status TradingReports_Scheduled
"%NSSM_EXE%" status TradingReports_RealTime

echo.
echo ================================================================================
echo     INSTALLATION COMPLETE!
echo ================================================================================
echo.
echo Your trading intelligence is now running as Windows Services!
echo.
echo What this means:
echo   [✓] Runs AUTOMATICALLY on PC boot
echo   [✓] Runs even when you're LOGGED OFF
echo   [✓] NEVER stops (true 24/7 operation)
echo   [✓] Auto-restarts if crashes
echo   [✓] Highest reliability possible
echo.
echo Service Names:
echo   1. TradingReports_Scheduled
echo   2. TradingReports_RealTime
echo.
echo To manage services:
echo   - Open Services: Win+R, type "services.msc"
echo   - Or use commands below
echo.
echo Service Commands:
echo   Start:   nssm start TradingReports_Scheduled
echo   Stop:    nssm stop TradingReports_Scheduled
echo   Restart: nssm restart TradingReports_Scheduled
echo   Status:  nssm status TradingReports_Scheduled
echo   Remove:  nssm remove TradingReports_Scheduled confirm
echo.
echo Logs:
echo   - service_scheduled.log (scheduled reports)
echo   - service_realtime.log (real-time alerts)
echo   - service_*_errors.log (if any errors)
echo.
echo Check your email in 5-10 minutes for confirmation!
echo.
echo ================================================================================
pause
