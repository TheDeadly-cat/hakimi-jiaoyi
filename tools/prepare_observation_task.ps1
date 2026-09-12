param(
    [string]$BundleRoot,
    [switch]$ValidateDefinitions,
    [switch]$Apply,
    [switch]$SchedulingAuthoritySwitchConfirmed
)
$ErrorActionPreference = 'Stop'
function Write-NewJson([string]$Path, $Value) {
    $temporary = $Path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    $bytes = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 14))
    $stream = [IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    [IO.File]::Move($temporary,$Path)
}
function New-ObservationDefinition($Service,$Task,[string]$Sid,[string]$BundleHash) {
    $definition = $Service.NewTask(0)
    $definition.RegistrationInfo.Description = 'Hakimi bounded 72h research trial; no orders. Bundle '+$BundleHash
    $definition.Principal.UserId = $Sid
    $definition.Principal.LogonType = 3
    $definition.Principal.RunLevel = 0
    $definition.Settings.Enabled = $false
    $definition.Settings.MultipleInstances = 2
    $definition.Settings.ExecutionTimeLimit = [Xml.XmlConvert]::ToString([TimeSpan]::FromSeconds($Task.execution_limit_seconds))
    $definition.Settings.AllowHardTerminate = $true
    $definition.Settings.DisallowStartIfOnBatteries = $false
    $definition.Settings.StopIfGoingOnBatteries = $false
    $definition.Settings.WakeToRun = $true
    $definition.Settings.StartWhenAvailable = $true
    $trigger = $definition.Triggers.Create(1)
    $trigger.StartBoundary = $Task.first_utc
    $trigger.EndBoundary = $Task.end_utc_exclusive
    $trigger.Repetition.Interval = [Xml.XmlConvert]::ToString([TimeSpan]::FromSeconds($Task.interval_seconds))
    $trigger.Repetition.StopAtDurationEnd = $false
    $action = $definition.Actions.Create(0)
    $action.Path = $Task.execute
    $action.Arguments = $Task.arguments
    $action.WorkingDirectory = $Task.working_directory
    return $definition
}
if ([string]::IsNullOrWhiteSpace($BundleRoot)) {
    if ($Apply -or $ValidateDefinitions) { throw 'A prepared control bundle is required.' }
    [ordered]@{ status='NOT_ACTIVATED'; preparation_required='Run observation_bundle.py create, then pass BundleRoot.'; task_count=2; observer_interval='PT1H'; watch_interval='PT1M'; observer_execution_limit='PT10M'; watch_execution_limit='PT50S'; old_heartbeat_changed=$false } | ConvertTo-Json
    return
}
$bundle = [IO.Path]::GetFullPath($BundleRoot)
$manifest = Get-Content -LiteralPath (Join-Path $bundle 'bundle.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$runner = Join-Path $bundle 'tools\observation_bundle.py'
if ((Get-FileHash -LiteralPath $runner -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.tool_sha256.'observation_bundle.py') { throw 'Prepared runner bytes changed.' }
$python = Join-Path $manifest.runtime_root 'venv\Scripts\python.exe'
$previewJson = & $python -I -B $runner preview --bundle-root $bundle
if ($LASTEXITCODE -ne 0) { throw 'Control bundle verification failed.' }
$preview = $previewJson | ConvertFrom-Json
if ($preview.tasks.Count -ne 2 -or $preview.bundle_hash -ne $manifest.receipt_hash) { throw 'Invalid fixed task preview.' }
if (-not $Apply -and -not $ValidateDefinitions) { $preview | ConvertTo-Json -Depth 8; return }
if ($Apply) {
    if (-not $SchedulingAuthoritySwitchConfirmed) { throw 'Explicit maintainer approval and verified pause of the old heartbeat are required before Apply.' }
    if (-not $preview.current_registration_window_valid) { throw 'Prepared start is too close or expired. Prepare a fresh window; do not edit this bundle.' }
    if ([IO.Path]::GetFullPath($PSCommandPath) -ne [IO.Path]::GetFullPath((Join-Path $bundle 'tools\prepare_observation_task.ps1'))) { throw 'Apply must use the script inside the fixed bundle.' }
    if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.tool_sha256.'prepare_observation_task.ps1') { throw 'Registration script identity changed.' }
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$service = New-Object -ComObject 'Schedule.Service'
$service.Connect()
$definitions = @()
foreach ($task in @($preview.tasks | Sort-Object { if ($_.role -eq 'watch') { 0 } else { 1 } })) {
    $definition = New-ObservationDefinition $service $task $identity.User.Value $preview.bundle_hash
    $definitions += [pscustomobject]@{ spec=$task; definition=$definition }
}
if (-not $Apply) {
    [ordered]@{ status='WINDOWS_DEFINITIONS_VALIDATED_NOT_REGISTERED'; preview=$preview; definitions=@($definitions | ForEach-Object { @{ task_name=$_.spec.task_name; xml=$_.definition.XmlText } }); registered=$false } | ConvertTo-Json -Depth 12
    return
}
foreach ($task in $preview.tasks) {
    if (Get-ScheduledTask -TaskPath '\' -TaskName $task.task_name -ErrorAction SilentlyContinue) { throw 'A target task already exists; refusing to overwrite it.' }
}
$folder = $service.GetFolder('\')
$created = New-Object 'System.Collections.Generic.List[object]'
$attemptId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'_'+[Guid]::NewGuid().ToString('N')
$receiptDirectory = Join-Path $bundle ('registration-attempts\'+$attemptId)
New-Item -ItemType Directory -Path $receiptDirectory | Out-Null
$activation = [ordered]@{ schema_version='observation-task-activation-v1'; bundle_hash=$preview.bundle_hash; started_at=[DateTime]::UtcNow.ToString('o'); status='NOT_ACTIVATED'; tasks=@(); old_heartbeat_pause='CALLER_CONFIRMED_NOT_PERFORMED_BY_SCRIPT' }
Write-NewJson (Join-Path $receiptDirectory 'started.json') $activation
try {
    foreach ($entry in $definitions) {
        # TASK_CREATE only. Both definitions are initially disabled.
        $registered = $folder.RegisterTaskDefinition($entry.spec.task_name,$entry.definition,2,$identity.User.Value,$null,3,$null)
        $created.Add($registered)
        $activation.tasks += [ordered]@{ task_name=$entry.spec.task_name; path=$registered.Path; definition_xml=$registered.Xml; initially_enabled=$registered.Enabled }
    }
    Write-NewJson (Join-Path $receiptDirectory 'registered-disabled.json') $activation
    if ([DateTimeOffset]::UtcNow.AddMinutes(1) -ge [DateTimeOffset]::Parse($preview.start_cutoff)) { throw 'Window start too close after staging registrations.' }
    foreach ($registered in $created) { $registered.Enabled = $true }
    $activation.status = 'REGISTERED_ENABLED_AWAITING_ACTUAL_RUNS'
    $activation.ended_at = [DateTime]::UtcNow.ToString('o')
    Write-NewJson (Join-Path $receiptDirectory 'ended.json') $activation
} catch {
    $activation.status = 'ACTIVATION_FAILED'
    $activation.error_type = $_.Exception.GetType().Name
    $activation.rollback = @()
    foreach ($registered in $created) {
        try { $registered.Enabled=$false; $activation.rollback += @{ path=$registered.Path; disabled=(-not $registered.Enabled) } }
        catch { $activation.rollback += @{ path=$registered.Path; disabled=$false; error_type=$_.Exception.GetType().Name } }
    }
    $activation.ended_at = [DateTime]::UtcNow.ToString('o')
    try { Write-NewJson (Join-Path $receiptDirectory 'failed.json') $activation } catch { }
    # Keep partial registrations disabled for diagnosis. Caller may resume the
    # old heartbeat only after verifying every new task is disabled.
    $activation | ConvertTo-Json -Depth 12
    throw
}
$activation | ConvertTo-Json -Depth 12
