param(
    [ValidateSet("Install", "Uninstall", "Status", "RunNow")]
    [string]$Mode = "Install",
    [ValidatePattern("^([01]\d|2[0-3]):[0-5]\d$")]
    [string]$DailyAt = "02:20"
)

$ErrorActionPreference = "Stop"
$TaskName = "HakimiTradeV2-PortfolioForwardBackup"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $ProjectRoot "run_portfolio_evidence_archive.py"

if ($Mode -eq "Uninstall") {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    [pscustomobject]@{ ok = $true; status = "UNINSTALLED"; task_name = $TaskName } | ConvertTo-Json
    exit 0
}

if ($Mode -eq "Status") {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        [pscustomobject]@{ ok = $false; status = "NOT_INSTALLED"; task_name = $TaskName } | ConvertTo-Json
        exit 1
    }
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    [pscustomobject]@{
        ok = $true
        status = [string]$task.State
        enabled = [bool]$task.Settings.Enabled
        task_name = $TaskName
        last_run_time = $info.LastRunTime
        last_task_result = $info.LastTaskResult
        next_run_time = $info.NextRunTime
    } | ConvertTo-Json
    exit 0
}

if ($Mode -eq "RunNow") {
    Start-ScheduledTask -TaskName $TaskName
    [pscustomobject]@{ ok = $true; status = "STARTED"; task_name = $TaskName } | ConvertTo-Json
    exit 0
}

if (-not (Test-Path -LiteralPath $Runner)) {
    throw "Portfolio evidence archive runner not found: $Runner"
}
$null = Get-Command python.exe -ErrorAction Stop
$PythonExe = (& python.exe -c "import sys; print(sys.executable)").Trim()
if (-not $PythonExe -or -not (Test-Path -LiteralPath $PythonExe)) {
    throw "Unable to resolve the real Python interpreter path."
}
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$Runner`"" `
    -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Description "Daily self-contained backup and restore rehearsal for research-only portfolio evidence. No order authority." `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

[pscustomobject]@{
    ok = $true
    status = "INSTALLED"
    task_name = $TaskName
    daily_at = $DailyAt
    python = $PythonExe
    runner = $Runner
    backup_only = $true
    paper_authorized = $false
    live_order_allowed = $false
} | ConvertTo-Json
