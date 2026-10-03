$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pythonCommand = if (Test-Path .venv/Scripts/python.exe) { '.venv/Scripts/python.exe' } else { 'python' }
& $pythonCommand -m pytest tests -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonCommand evals/run_static_evals.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
foreach ($step in @('test', 'typecheck', 'build')) {
    & npm run $step
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host 'Quality gate passed. Live providers and native release checks are separate.'
