$ErrorActionPreference = "Stop"

$repositoryRoot = $PSScriptRoot
$sourceRoot = Join-Path $repositoryRoot "src"
$legacyProjectRoot = Join-Path $repositoryRoot "outputs\python_quant_bot"
$pythonCommand = Get-Command python -ErrorAction Stop
$previousPythonPath = $env:PYTHONPATH
$pathItems = @($sourceRoot, $legacyProjectRoot)
if ($previousPythonPath) {
    $pathItems += $previousPythonPath
}

$env:PYTHONPATH = $pathItems -join [IO.Path]::PathSeparator
Push-Location -LiteralPath $legacyProjectRoot
try {
    & $pythonCommand.Source -B -m hakimi_research @args
    $processExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
}

exit $processExitCode
