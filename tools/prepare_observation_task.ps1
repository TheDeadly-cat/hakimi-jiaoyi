param(
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'HakimiResearch\builds\ci-33969915599'),
    [string]$JobRoot = (Join-Path $env:LOCALAPPDATA 'HakimiResearch\observation-job-20260913'),
    [string]$TaskName = 'HakimiReadOnlyObservation',
    [switch]$Apply,
    [switch]$SchedulingAuthoritySwitchConfirmed
)
$ErrorActionPreference = 'Stop'
$runtime = [IO.Path]::GetFullPath($RuntimeRoot)
$jobDirectory = [IO.Path]::GetFullPath($JobRoot)
$launcher = Join-Path $PSScriptRoot 'observation_job.py'
$pythonWindowless = Join-Path $runtime 'venv\Scripts\pythonw.exe'
if ($jobDirectory -eq $runtime -or $jobDirectory.StartsWith($runtime.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'JobRoot must be outside the frozen deployment.'
}
foreach ($path in @($runtime, $launcher, $pythonWindowless)) {
    if (-not (Test-Path -LiteralPath $path)) { throw 'A required local runtime or launcher path is unavailable.' }
    if ($path.Contains('"') -or $path.Contains("`r") -or $path.Contains("`n")) { throw 'Unsupported path characters.' }
}
if ($jobDirectory.Contains('"') -or $jobDirectory.Contains("`r") -or $jobDirectory.Contains("`n")) { throw 'Unsupported JobRoot characters.' }
$wrapper = Join-Path $runtime 'tools\forward_reliability.py'
if ((Get-FileHash -LiteralPath $wrapper -Algorithm SHA256).Hash.ToLowerInvariant() -ne '213e855414e125b419c0153f189b01415bb22d68e0f3f168c21e5014ac4472da') {
    throw 'Frozen wrapper hash changed.'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$clock = Get-Date
$firstRun = $clock.Date.AddHours($clock.Hour).AddMinutes(1)
if ($firstRun -le $clock) { $firstRun = $firstRun.AddHours(1) }
$arguments = '-I -B "{0}" --runtime-root "{1}" --job-root "{2}"' -f $launcher, $runtime, $jobDirectory
$preview = [ordered]@{
    status = 'NOT_ACTIVATED'
    task_name = $TaskName
    current_user = $identity
    execute = $pythonWindowless
    arguments = $arguments
    working_directory = $runtime
    launcher_sha256 = (Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash.ToLowerInvariant()
    first_local_run = $firstRun.ToString('o')
    repetition = 'PT1H; minute 01; indefinite'
    wake_to_run = $true
    start_when_available = $true
    multiple_instances = 'IgnoreNew'
    execution_time_limit = 'PT10M; launcher-owned child deadline PT5M plus bounded cleanup'
    child_execution_timeout_seconds = 300
    child_cleanup_timeout_seconds = 5
    child_combined_output_limit_bytes = 4194304
    process_ownership = 'Private Windows job; kill all assigned descendants when launcher exits'
    logon_type = 'Interactive; current user must be logged on'
    scheduler_clock_evidence = 'PROCESS_START_ONLY; underlying frozen wrapper uses MANUAL'
    notification_delivery = 'NOT_SENT_BY_THIS_TOOL'
    activation_prerequisite = 'Explicitly approve and complete the single scheduling authority switch; pause the existing heartbeat through the app before applying.'
}
$preview | ConvertTo-Json -Depth 5
if (-not $Apply) { return }
if (-not $SchedulingAuthoritySwitchConfirmed) {
    throw 'Apply requires explicit confirmation that the existing heartbeat has been paused and the scheduling authority switch is approved.'
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw 'Task already exists; refusing to overwrite or create a second scheduling authority.'
}
$action = New-ScheduledTaskAction -Execute $pythonWindowless -Argument $arguments -WorkingDirectory $runtime
$trigger = New-ScheduledTaskTrigger -Once -At $firstRun -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$definition = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Pinned public-data observer. No accounts/orders. PROCESS_START_ONLY; no fabricated scheduler event time. Local receipts only.'
Register-ScheduledTask -TaskName $TaskName -InputObject $definition | Select-Object TaskName, State
