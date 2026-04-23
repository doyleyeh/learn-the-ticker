param(
  [switch]$PreflightOnly,
  [switch]$CommitFailures
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

$CodexModel = if ($env:LTT_CODEX_MODEL) { $env:LTT_CODEX_MODEL } else { "gpt-5.3-codex-spark" }
$CodexReasoningEffort = if ($env:LTT_CODEX_REASONING_EFFORT) { $env:LTT_CODEX_REASONING_EFFORT } else { "high" }

function Require-Command {
  param([string]$Name)

  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name is required but was not found on PATH."
  }
}

function Get-IterationBudget {
  $TaskText = Get-Content -LiteralPath "TASKS.md" -Raw
  $Match = [regex]::Match($TaskText, "Max\s+(\d+)")

  if ($Match.Success) {
    return [int]$Match.Groups[1].Value
  }

  return 3
}

function Get-ConventionalCommitType {
  param([string]$Title)

  $LowerTitle = $Title.ToLowerInvariant()

  if ($LowerTitle -match "(^|[^a-z0-9])fix(es|ed)?([^a-z0-9]|$)") {
    return "fix"
  }
  if ($LowerTitle -match "(^|[^a-z0-9])(test|tests|eval|evals)([^a-z0-9]|$)") {
    return "test"
  }
  if ($LowerTitle -match "(^|[^a-z0-9])(doc|docs|documentation)([^a-z0-9]|$)") {
    return "docs"
  }
  if ($LowerTitle -match "(^|[^a-z0-9])(scaffold|prepare|setup|chore)([^a-z0-9]|$)") {
    return "chore"
  }
  if ($LowerTitle -match "(^|[^a-z0-9])refactor([^a-z0-9]|$)") {
    return "refactor"
  }

  return "feat"
}

function Get-CommitSubject {
  param([string]$Title)

  if ([string]::IsNullOrWhiteSpace($Title)) {
    return "current task"
  }

  if ($Title.Length -eq 1) {
    return $Title.ToLowerInvariant()
  }

  return $Title.Substring(0, 1).ToLowerInvariant() + $Title.Substring(1)
}

function Get-CodexExecArgs {
  return @(
    "-m", $CodexModel,
    "-c", "reasoning.effort=""$CodexReasoningEffort"""
  )
}

$Root = (git rev-parse --show-toplevel).Trim()
Set-Location $Root

Require-Command git
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
  $TaskTitle = "current task"
} else {
  $TaskId = [regex]::Match($TaskLine.Line, "^### ([^: ]+)").Groups[1].Value
  $TaskTitleMatch = [regex]::Match($TaskLine.Line, "^### [^: ]+:\s*(.+)$")
  if ($TaskTitleMatch.Success) {
    $TaskTitle = $TaskTitleMatch.Groups[1].Value.Trim()
  } else {
    $TaskTitle = "current task"
  }
}

$Branch = "agent/$TaskId-$RunId"
$IterationBudget = Get-IterationBudget
$CommitType = Get-ConventionalCommitType -Title $TaskTitle
$TaskCommitSubject = Get-CommitSubject -Title $TaskTitle

Write-Host "== Agent run: $RunId =="
Write-Host "== Task: $TaskId =="
Write-Host "== Task title: $TaskTitle =="
Write-Host "== Branch: $Branch =="
Write-Host "== Codex model: $CodexModel =="
Write-Host "== Codex reasoning effort: $CodexReasoningEffort =="
Write-Host "== Commit subject: ${CommitType}(${TaskId}): $TaskCommitSubject =="
Write-Host "== Iteration budget: $IterationBudget =="

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

$QualityStatus = 1
$CodexStatus = 0

for ($Attempt = 1; $Attempt -le $IterationBudget; $Attempt++) {
  $AttemptDir = "$RunDir/attempt-$Attempt"
  New-Item -ItemType Directory -Force -Path $AttemptDir | Out-Null

  $RetryContext = ""
  if ($Attempt -gt 1) {
    $PreviousAttempt = $Attempt - 1
    $RetryContext = @"

This is retry attempt $Attempt of $IterationBudget.
The previous attempt did not pass. Inspect these local logs before editing:
- .agent-runs/$RunId/attempt-$PreviousAttempt/codex-final.md
- .agent-runs/$RunId/attempt-$PreviousAttempt/quality-gate.log
- .agent-runs/$RunId/attempt-$PreviousAttempt/diff.patch
"@
  }

  $PromptPath = "$AttemptDir/prompt.txt"
  $Prompt = @"
You are working on this repository as a coding agent.

This is attempt $Attempt of $IterationBudget.

First read:
- AGENTS.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md
- docs/learn-the-ticker_proposal.md
- SPEC.md
- TASKS.md
- EVALS.md

Work only on the current task in TASKS.md.

Rules:
- Follow safety and advice-boundary rules first, then the updated PRD, technical design spec, proposal, SPEC, TASKS, and EVALS in that order.
- Leave changes uncommitted for the harness commit step after the quality gate.
- Do not push from inside a Codex attempt.
- Do not run git reset --hard.
- Do not run git clean -fd.
- Do not change unrelated files.
- Keep changes small.
- Run the required tests/evals from EVALS.md.
- If tests fail, make one focused revision and run them again.
- Stop after the iteration budget in TASKS.md.
$RetryContext

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

  Write-Host "== Running Codex attempt $Attempt/$IterationBudget =="
  $CodexOutputPath = "$AttemptDir/codex-final.md"
  $CodexExecArgs = Get-CodexExecArgs
  & codex @CodexExecArgs -a never exec --sandbox workspace-write $Prompt |
    Tee-Object -FilePath $CodexOutputPath
  $CodexStatus = $LASTEXITCODE

  if ($CodexStatus -ne 0) {
    Write-Host "Codex exited with status $CodexStatus."
    "Quality gate skipped because Codex exited with status $CodexStatus." |
      Set-Content -LiteralPath "$AttemptDir/quality-gate.log" -Encoding UTF8
    $QualityStatus = $CodexStatus
  } else {
    Write-Host "== Running quality gate for attempt $Attempt/$IterationBudget =="
    $QualityLogPath = "$AttemptDir/quality-gate.log"
    & .\scripts\run_quality_gate.ps1 *> $QualityLogPath
    $QualityStatus = $LASTEXITCODE
    Get-Content -LiteralPath $QualityLogPath
  }

  Write-Host "== Capturing Git status for attempt $Attempt/$IterationBudget =="
  git status --short | Tee-Object -FilePath "$AttemptDir/git-status.txt"
  git diff | Set-Content -LiteralPath "$AttemptDir/diff.patch" -Encoding UTF8

  if ($QualityStatus -eq 0) {
    Write-Host "== Quality gate passed on attempt $Attempt/$IterationBudget =="
    break
  }

  if ($Attempt -lt $IterationBudget) {
    Write-Host "== Quality gate failed; retrying with diagnostics from attempt $Attempt =="
  }
}

Write-Host "== Capturing final Git status =="
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
Iteration budget: $IterationBudget

See local ignored logs:

- .agent-runs/$RunId/attempt-*/codex-final.md
- .agent-runs/$RunId/attempt-*/quality-gate.log
- .agent-runs/$RunId/diff.patch
"@
  Set-Content -LiteralPath $JournalPath -Value $FallbackJournal -Encoding UTF8
}

if (($QualityStatus -ne 0) -and (-not $CommitFailures)) {
  Write-Host "Quality gate failed after $IterationBudget attempt(s)."
  Write-Host "Leaving changes uncommitted and unstaged for review."
  Write-Host "Rerun with -CommitFailures to create a WIP audit commit."
  exit $QualityStatus
}

git add -A

$StagedFiles = git diff --cached --name-only
if (-not $StagedFiles) {
  Write-Host "No changes to commit."
  exit $QualityStatus
}

if ($QualityStatus -eq 0) {
  git commit `
    -m "${CommitType}(${TaskId}): $TaskCommitSubject" `
    -m "Run ID: $RunId" `
    -m "Quality gate: passed"
} else {
  git commit `
    -m "chore(${TaskId}): record failed $TaskCommitSubject attempt" `
    -m "Run ID: $RunId" `
    -m "Quality gate: failed. Review before merge."
}

Write-Host "== Final status =="
git status --short
git log --oneline -5

exit $QualityStatus
