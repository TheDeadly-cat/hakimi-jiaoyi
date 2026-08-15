$ErrorActionPreference = "Stop"

function Test-PythonCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [string[]]$Args = @()
    )

    try {
        $version = & $Exe @Args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
            return $null
        }
        return [pscustomobject]@{
            Exe = $Exe
            Args = $Args
            Version = $version.Trim()
            Display = (($Exe) + $(if ($Args.Count -gt 0) { " " + ($Args -join " ") } else { "" })).Trim()
        }
    } catch {
        return $null
    }
}

function Find-Python {
    $candidates = New-Object System.Collections.Generic.List[object]

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $candidates.Add([pscustomobject]@{ Exe = $pythonCmd.Source; Args = @() })
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        foreach ($version in @("-3.14", "-3.13", "-3.12", "-3.11", "-3")) {
            $candidates.Add([pscustomobject]@{ Exe = $pyCmd.Source; Args = @($version) })
        }
    }

    $roots = @(
        "$env:LocalAppData\Python",
        "$env:LocalAppData\Programs\Python",
        "C:\Program Files",
        "C:\Program Files (x86)"
    )
    foreach ($root in $roots) {
        foreach ($tag in @("pythoncore-3.14-64", "pythoncore-3.13-64", "pythoncore-3.12-64", "Python314", "Python313", "Python312", "Python311", "Python310")) {
            $path = Join-Path (Join-Path $root $tag) "python.exe"
            if (Test-Path $path) {
                $candidates.Add([pscustomobject]@{ Exe = $path; Args = @() })
            }
        }
    }

    $registryRoots = @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\WOW6432Node\Python\PythonCore"
    )
    foreach ($registryRoot in $registryRoots) {
        if (-not (Test-Path $registryRoot)) {
            continue
        }
        foreach ($versionKey in Get-ChildItem $registryRoot -ErrorAction SilentlyContinue) {
            $installPathKey = Join-Path $versionKey.PSPath "InstallPath"
            if (-not (Test-Path $installPathKey)) {
                continue
            }
            $installPath = (Get-ItemProperty $installPathKey -ErrorAction SilentlyContinue)."(default)"
            if ([string]::IsNullOrWhiteSpace($installPath)) {
                $installPath = (Get-ItemProperty $installPathKey -ErrorAction SilentlyContinue).ExecutablePath
                if (-not [string]::IsNullOrWhiteSpace($installPath)) {
                    $candidates.Add([pscustomobject]@{ Exe = $installPath; Args = @() })
                    continue
                }
            }
            if (-not [string]::IsNullOrWhiteSpace($installPath)) {
                $path = Join-Path $installPath "python.exe"
                if (Test-Path $path) {
                    $candidates.Add([pscustomobject]@{ Exe = $path; Args = @() })
                }
            }
        }
    }

    foreach ($candidate in $candidates) {
        $found = Test-PythonCommand -Exe $candidate.Exe -Args $candidate.Args
        if ($found) {
            return $found
        }
    }

    return $null
}
