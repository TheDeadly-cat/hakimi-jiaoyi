$ErrorActionPreference = "Stop"

$repositoryRoot = $PSScriptRoot
$sourceRoot = Join-Path $repositoryRoot "src"
$pythonCommand = Get-Command python -ErrorAction Stop
$previousPythonPath = $env:PYTHONPATH
$pathItems = @($sourceRoot)
if ($previousPythonPath) {
    $pathItems += $previousPythonPath
}

$env:PYTHONPATH = $pathItems -join [IO.Path]::PathSeparator
Push-Location -LiteralPath $repositoryRoot
try {
    & $pythonCommand.Source -B -m hakimi_research @args
    $processExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
}

exit $processExitCode
