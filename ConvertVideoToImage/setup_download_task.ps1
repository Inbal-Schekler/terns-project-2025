# Registers Task Scheduler tasks to download camera videos automatically.
# Run this once: right-click -> Run with PowerShell (as Administrator)
#
# North camera (191): stores only ~1 day — download twice daily at 10:30 and 15:30,
#   shortly after each scan (10:00 and 15:00), before the footage expires.
# South camera (181): stores 7 days — download once a week (Sunday 17:00) is enough.
#   The script skips files already downloaded so running more often is also safe.

$pythonPath = "C:\Users\user\anaconda3\python.exe"
$scriptPath = "F:\My Drive\tern_project\Chicks\terns-project-chick\ConvertVideoToImage\extrac_scans_auto.py"
$logPath    = "F:\My Drive\tern_project\terns_movies\download_log.txt"

$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "`"$scriptPath`" >> `"$logPath`" 2>&1"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -RunOnlyIfNetworkAvailable `
    -StartWhenAvailable

# Task 1: daily at 10:30 (catches north camera morning scan at 10:00)
Register-ScheduledTask `
    -TaskName "TernsCameraDownload_1030" `
    -Action $action `
    -Trigger (New-ScheduledTaskTrigger -Daily -At "10:30") `
    -Settings $settings `
    -RunLevel Highest `
    -Force

# Task 2: daily at 15:30 (catches north camera afternoon scan at 15:00)
Register-ScheduledTask `
    -TaskName "TernsCameraDownload_1530" `
    -Action $action `
    -Trigger (New-ScheduledTaskTrigger -Daily -At "15:30") `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host "Done. Two daily tasks registered: 10:30 and 15:30."
Write-Host "Log file: $logPath"
