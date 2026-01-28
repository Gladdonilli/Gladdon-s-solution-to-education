# Canvas Sync Startup Setup Script
# Run this once as Administrator to register the startup task

$taskName = "CanvasSyncStartup"
$scriptPath = "C:\Users\li859\Documents\Personal-projects\canvas-obsidian-sync\startup_sync.bat"

# Create the scheduled task action
$action = New-ScheduledTaskAction -Execute $scriptPath

# Trigger on user logon
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Run with normal priority, don't require AC power
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register the task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force

Write-Host "Startup task '$taskName' created successfully!" -ForegroundColor Green
Write-Host "The daily sync will run and TODO.md will open in Obsidian on every login."
