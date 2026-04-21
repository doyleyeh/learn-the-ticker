$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

function Require-Command {
  param([string]$Name)

  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name is required but was not found on PATH."
  }
}

function Invoke-Step {
  param(
    [string]$Name,
    [scriptblock]$Command
  )

  Write-Host "== $Name =="
  & $Command
  $Status = $LASTEXITCODE
  if ($Status -ne 0) {
    exit $Status
  }
}

function Get-PythonCommand {
  if ($env:PYTHON) {
    return $env:PYTHON
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    return "python"
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return "py"
  }

  throw "Python is required, but neither python nor py was found on PATH."
}

$Root = (git rev-parse --show-toplevel).Trim()
Set-Location $Root

$Python = Get-PythonCommand

Write-Host "== Quality gate started =="
Write-Host "== Python: $(& $Python --version) =="

Invoke-Step -Name "Python tests" -Command {
  & $Python -m pytest tests -q
}

Invoke-Step -Name "Static evals" -Command {
  & $Python evals/run_static_evals.py
}

if (Test-Path -LiteralPath "package.json") {
  Require-Command npm

  if (($env:OS -eq "Windows_NT") -and (Test-Path -LiteralPath "package-lock.json") -and -not (Test-Path -LiteralPath "node_modules/.bin/tsc.cmd")) {
    Write-Host "== Refreshing Windows npm command shims =="
    & npm ci
    if ($LASTEXITCODE -ne 0) {
      exit $LASTEXITCODE
    }
  }

  Invoke-Step -Name "Frontend checks" -Command {
    & npm run lint --if-present
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & npm run test --if-present
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & npm run typecheck --if-present
  }
}

if (Test-Path -LiteralPath "backend" -PathType Container) {
  Invoke-Step -Name "Backend checks" -Command {
    & $Python -m pytest backend tests -q
  }
}

Write-Host "== Quality gate passed =="
