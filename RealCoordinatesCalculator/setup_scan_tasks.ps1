# Creates two daily Task Scheduler tasks for the tern scan.
# Run this in PowerShell (right-click -> Run with PowerShell).
# It will ask for your Windows password once, to allow running when logged out.

$python = "C:\Users\user\anaconda3\python.exe"
$script = "F:\My Drive\tern_project\Chicks\terns-project-chick\RealCoordinatesCalculator\run_scan.py"
$workdir = "F:\My Drive\tern_project\Chicks\terns-project-chick\RealCoordinatesCalculator"

# Ask for Windows password (needed for "run when logged out")
$password = Read-Host "Enter your Windows login password (needed to run when logged out)"

# Shared settings
$settings = New-ScheduledTaskSettingsSet `
    -RunOnlyIfNetworkAvailable `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$action_morning = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$script`"" `
    -WorkingDirectory $workdir

$action_afternoon = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$script`"" `
    -WorkingDirectory $workdir

# Morning: 10:01 daily (script sleeps to :50 internally)
$trigger_morning = New-ScheduledTaskTrigger -Daily -At "10:01:00"

# Afternoon: 15:01 daily
$trigger_afternoon = New-ScheduledTaskTrigger -Daily -At "15:01:00"

# Register morning task
try {
    Unregister-ScheduledTask -TaskName "TernScan_Morning" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName "TernScan_Morning" `
        -Action $action_morning `
        -Trigger $trigger_morning `
        -Settings $settings `
        -RunLevel Limited `
        -User $env:USERNAME `
        -Password $password `
        -Force
    Write-Host "Morning task created OK (10:01:50 daily)" -ForegroundColor Green
} catch {
    Write-Host "ERROR creating morning task: $_" -ForegroundColor Red
}

# Register afternoon task
try {
    Unregister-ScheduledTask -TaskName "TernScan_Afternoon" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName "TernScan_Afternoon" `
        -Action $action_afternoon `
        -Trigger $trigger_afternoon `
        -Settings $settings `
        -RunLevel Limited `
        -User $env:USERNAME `
        -Password $password `
        -Force
    Write-Host "Afternoon task created OK (15:01:50 daily)" -ForegroundColor Green
} catch {
    Write-Host "ERROR creating afternoon task: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done. To verify, open Task Scheduler and look for TernScan_Morning and TernScan_Afternoon."
Write-Host "To test immediately: right-click the task -> Run"
Write-Host ""
pause
