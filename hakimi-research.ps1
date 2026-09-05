$ErrorActionPreference = "Stop"

$pythonCommand = Get-Command python -ErrorAction Stop
& $pythonCommand.Source -B -m hakimi_research @args
$processExitCode = $LASTEXITCODE

exit $processExitCode
