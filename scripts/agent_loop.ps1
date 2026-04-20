param(
  [switch]$PreflightOnly
)

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

$Root = (git rev-parse --show-toplevel).Trim()
Set-Location $Root

Require-Command git
Require-Command bash
Require-Command codex

$CodexVersion = (& codex --version 2>&1)
if ($LASTEXITCODE -ne 0) {
  throw "Codex CLI was found but could not start: $CodexVersion"
}

if ($PreflightOnly) {
  Write-Host "Codex preflight passed: $CodexVersion"
  exit 0
}

$RunId = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$TaskLine = Select-String -Path "TASKS.md" -Pattern "^### T-" | Select-Object -First 1

if ($null -eq $TaskLine) {
  $TaskId = "T-unknown"
} else {
  $TaskId = [regex]::Match($TaskLine.Line, "^### ([^: ]+)").Groups[1].Value
}

$Branch = "agent/$TaskId-$RunId"

Write-Host "== Agent run: $RunId =="
Write-Host "== Task: $TaskId =="
Write-Host "== Branch: $Branch =="

$Status = git status --porcelain
if ($Status) {
  Write-Host "Working tree is not clean. Commit or stash your changes first."
  git status --short
  exit 1
}

git checkout -b $Branch

$RunDir = ".agent-runs/$RunId"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
New-Item -ItemType Directory -Force -Path "docs/agent-journal" | Out-Null

$PromptPath = "$RunDir/prompt.txt"
$Prompt = @"
You are working on this repository as a coding agent.

First read:
- AGENTS.md
- SPEC.md
- TASKS.md
- EVALS.md
- docs/learn_the_ticker_PRD.md if present
- docs/learn_the_ticker_technical_design_spec.md if present

Work only on the current task in TASKS.md.

Rules:
- Do not run git commit.
- Do not run git push.
- Do not run git reset --hard.
- Do not run git clean -fd.
- Do not change unrelated files.
- Keep changes small.
- Run the required tests/evals from EVALS.md.
- If tests fail, make one focused revision and run them again.
- Stop after the iteration budget in TASKS.md.

Before finishing, write a concise Markdown summary to:
docs/agent-journal/$RunId.md

The summary must include:
- task id
- files changed
- tests/evals run
- pass/fail status
- remaining risks
"@

Set-Content -LiteralPath $PromptPath -Value $Prompt -Encoding UTF8

Write-Host "== Running Codex =="
$CodexOutputPath = "$RunDir/codex-final.md"
& codex exec --sandbox workspace-write --ask-for-approval never $Prompt |
  Tee-Object -FilePath $CodexOutputPath
$CodexStatus = $LASTEXITCODE
if ($CodexStatus -ne 0) {
  throw "Codex exited with status $CodexStatus. See $CodexOutputPath for details."
}

Write-Host "== Running quality gate =="
$QualityLogPath = "$RunDir/quality-gate.log"
& bash scripts/run_quality_gate.sh *> $QualityLogPath
$QualityStatus = $LASTEXITCODE
Get-Content -LiteralPath $QualityLogPath

Write-Host "== Capturing Git status =="
git status --short | Tee-Object -FilePath "$RunDir/git-status.txt"
git diff | Set-Content -LiteralPath "$RunDir/diff.patch" -Encoding UTF8

$JournalPath = "docs/agent-journal/$RunId.md"
if (-not (Test-Path -LiteralPath $JournalPath)) {
  $FallbackJournal = @"
# Agent run $RunId

Task: $TaskId

## Result

Codex completed a run, but did not create a detailed journal entry.

## Quality gate

Exit status: $QualityStatus

See local ignored logs:

- .agent-runs/$RunId/codex-final.md
- .agent-runs/$RunId/quality-gate.log
- .agent-runs/$RunId/diff.patch
"@
  Set-Content -LiteralPath $JournalPath -Value $FallbackJournal -Encoding UTF8
}

git add -A

$StagedFiles = git diff --cached --name-only
if (-not $StagedFiles) {
  Write-Host "No changes to commit."
  exit $QualityStatus
}

if ($QualityStatus -eq 0) {
  git commit `
    -m "agent($TaskId): implement current task" `
    -m "Run ID: $RunId" `
    -m "Quality gate: passed"
} else {
  git commit `
    -m "wip($TaskId): agent attempt with failing quality gate" `
    -m "Run ID: $RunId" `
    -m "Quality gate: failed. Review before merge."
}

Write-Host "== Final status =="
git status --short
git log --oneline -5

exit $QualityStatus
