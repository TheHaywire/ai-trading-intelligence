@echo off
echo ================================================================================
echo     AUTOMATED DAILY TRADING REPORTS - STARTUP
echo     Professional Quantitative Analysis System
echo ================================================================================
echo.
echo Starting automated report scheduler...
echo Reports will be sent to your email at regular intervals
echo.
echo Press Ctrl+C to stop the scheduler
echo.
echo ================================================================================
echo.

python auto_scheduler_reports.py

echo.
echo ================================================================================
echo Scheduler stopped.
echo ================================================================================
pause
