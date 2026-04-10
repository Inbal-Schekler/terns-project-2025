@echo off
REM Creates two Windows Task Scheduler tasks that run run_scan.py at exact times daily.
REM Run this file once as Administrator.

SET PYTHON=C:\Users\user\anaconda3\python.exe
SET SCRIPT=F:\My Drive\tern_project\Chicks\terns-project-chick\RealCoordinatesCalculator\run_scan.py
SET WORKDIR=F:\My Drive\tern_project\Chicks\terns-project-chick\RealCoordinatesCalculator

echo Creating morning scan task (10:01:50)...
schtasks /create /tn "TernScan_Morning" /tr "\"%PYTHON%\" \"%SCRIPT%\"" /sc daily /st 10:01 /sd 01/01/2026 /f
echo Done.

echo Creating afternoon scan task (15:01:50)...
schtasks /create /tn "TernScan_Afternoon" /tr "\"%PYTHON%\" \"%SCRIPT%\"" /sc daily /st 15:01 /sd 01/01/2026 /f
echo Done.

echo.
echo NOTE: Windows Task Scheduler only supports minute-level precision (not seconds).
echo The tasks will start at 10:01 and 15:01. To get :50 second precision,
echo add a 50-second sleep at the start of run_scan.py (see instructions below).
echo.
pause
