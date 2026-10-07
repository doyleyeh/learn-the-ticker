$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .venv/Scripts/python.exe)) {
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& .venv/Scripts/python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& npm ci
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Dependencies installed. Set LTT_PG_BIN, install Rust/MSVC build tools, then run npm run desktop.'
