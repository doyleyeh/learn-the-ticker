$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../../../..')
$pythonCommand = if (Test-Path .venv/Scripts/python.exe) { '.venv/Scripts/python.exe' } else { 'python' }
& $pythonCommand -m scripts.verify fast @args
exit $LASTEXITCODE
