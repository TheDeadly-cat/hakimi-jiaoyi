param([Parameter(Mandatory=$true)][string]$RequestPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$result = [ordered]@{ schema_version='observation-windows-notification-v1'; status='NOT_STARTED'; shown_at=$null; clicked_at=$null; closed_at=$null; submitted_at=$null; user_state=$null; request_file_sha256=$null; notification_id=$null }
$icon = $null
try {
    $bytes = [IO.File]::ReadAllBytes([IO.Path]::GetFullPath($RequestPath))
    if ($bytes.Length -gt 16384) { throw 'request_too_large' }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $result.request_file_sha256 = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
    $request = [Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json
    if ($request.schema_version -ne 'observation-notification-payload-v1' -or $request.notification_id -notmatch '^[a-f0-9]{64}$' -or $request.title.Length -gt 48 -or $request.body.Length -gt 200 -or [string]::IsNullOrWhiteSpace($request.title) -or [string]::IsNullOrWhiteSpace($request.body) -or $request.icon -notin @('Info','Warning')) { throw 'invalid_notification_request' }
    $result.notification_id = $request.notification_id
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class HakimiNotificationState {
    [DllImport("shell32.dll", PreserveSig=true)]
    public static extern int SHQueryUserNotificationState(out int state);
}
'@
    $state = 0
    $hr = [HakimiNotificationState]::SHQueryUserNotificationState([ref]$state)
    $result.user_state = $state
    if ($hr -ne 0 -or -not [Environment]::UserInteractive) {
        $result.status = 'USER_STATE_UNAVAILABLE'
    } elseif ($state -ne 5) {
        # Respect quiet time, presentation mode, lock/away state and OS policy.
        $result.status = 'DEFERRED_BY_USER_STATE'
    } else {
        $icon = New-Object System.Windows.Forms.NotifyIcon
        $icon.Icon = [Drawing.SystemIcons]::Information
        $icon.Text = 'Hakimi Research'
        $icon.BalloonTipTitle = [string]$request.title
        $icon.BalloonTipText = [string]$request.body
        $icon.BalloonTipIcon = [Enum]::Parse([System.Windows.Forms.ToolTipIcon], [string]$request.icon)
        $icon.add_BalloonTipShown({ $result.shown_at = [DateTime]::UtcNow.ToString('o'); $result.status='OS_DISPLAY_REPORTED' })
        $icon.add_BalloonTipClicked({ $result.clicked_at = [DateTime]::UtcNow.ToString('o'); $result.status='USER_CLICK_REPORTED' })
        $icon.add_BalloonTipClosed({ $result.closed_at = [DateTime]::UtcNow.ToString('o') })
        $icon.Visible = $true
        $timer = [Diagnostics.Stopwatch]::StartNew()
        $result.submitted_at = [DateTime]::UtcNow.ToString('o')
        $result.status = 'DISPLAY_UNCONFIRMED'
        $icon.ShowBalloonTip(10000)
        # The OS controls display duration. Keep a finite local message loop;
        # no assumption that a timeout, API return or dismissal means seen.
        while ($timer.Elapsed.TotalSeconds -lt 20) {
            [System.Windows.Forms.Application]::DoEvents()
            if ($result.clicked_at -or $result.closed_at) { break }
            if (-not $result.shown_at -and $timer.Elapsed.TotalSeconds -ge 10) { break }
            Start-Sleep -Milliseconds 20
        }
        $timer.Stop()
    }
} catch {
    $result.status = 'WORKER_ERROR'
    $result.error_type = $_.Exception.GetType().Name
} finally {
    if ($null -ne $icon) { $icon.Visible=$false; $icon.Dispose() }
}
$result.ended_at = [DateTime]::UtcNow.ToString('o')
$result | ConvertTo-Json -Depth 4 -Compress
if ($result.status -eq 'WORKER_ERROR') { exit 1 }
