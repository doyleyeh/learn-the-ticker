$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pythonCommand = if (Test-Path .venv/Scripts/python.exe) { '.venv/Scripts/python.exe' } else { 'python' }
& $pythonCommand -m scripts.verify milestone @args
exit $LASTEXITCODE
