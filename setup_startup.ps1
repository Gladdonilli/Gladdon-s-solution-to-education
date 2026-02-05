# Canvas Sync Startup Setup Script
# Run this once as Administrator to register the startup task

$taskName = "CanvasSyncStartup"
$scriptPath = Join-Path $PSScriptRoot "startup_sync.bat"
$workingDirectory = $PSScriptRoot

# Create the scheduled task action
$action = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory $workingDirectory

# Trigger on user logon
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Run with normal priority, don't require AC power
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register the task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force

Write-Host "Startup task '$taskName' created successfully!" -ForegroundColor Green
Write-Host "The daily sync will run and TODO.md will open in Obsidian on every login."
