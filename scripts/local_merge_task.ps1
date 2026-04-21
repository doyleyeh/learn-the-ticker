param(
  [string]$Branch,
  [string]$MainBranch = "main"
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

function Require-CleanTree {
  $Status = git status --porcelain
  if ($Status) {
    git status --short
    throw "Working tree is not clean. Commit, stash, or discard unrelated changes before continuing."
  }
}

function Get-TaskInfo {
  param([string]$TaskBranch)

  $TaskIdMatch = [regex]::Match($TaskBranch, "(^|/)agent/(T-\d+)-")
  if (-not $TaskIdMatch.Success) {
    throw "Branch '$TaskBranch' does not look like an agent task branch: agent/T-000-..."
  }

  $TaskId = $TaskIdMatch.Groups[2].Value
  $TaskText = Get-Content -LiteralPath "TASKS.md" -Raw
  $TitleMatch = [regex]::Match($TaskText, "(?m)^###\s+$([regex]::Escape($TaskId)):\s*(.+)$")

  if (-not $TitleMatch.Success) {
    throw "Could not find a TASKS.md heading for $TaskId."
  }

  return @{
    Id = $TaskId
    Title = $TitleMatch.Groups[1].Value.Trim()
  }
}

function Get-MergeSubject {
  param([string]$Title)

  if ([string]::IsNullOrWhiteSpace($Title)) {
    return "merge task"
  }

  if ($Title.Length -eq 1) {
    $Subject = $Title.ToLowerInvariant()
  } else {
    $Subject = $Title.Substring(0, 1).ToLowerInvariant() + $Title.Substring(1)
  }

  $Subject = [regex]::Replace($Subject, "^(add|create|implement|update)\s+", "")
  return "merge $Subject"
}

$Root = (git rev-parse --show-toplevel).Trim()
Set-Location $Root

Require-Command git

Require-CleanTree

if ([string]::IsNullOrWhiteSpace($Branch)) {
  $Branch = (git branch --show-current).Trim()
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
  throw "Could not determine the current branch. Pass -Branch explicitly."
}

$CurrentBranch = (git branch --show-current).Trim()
$TaskInfo = Get-TaskInfo -TaskBranch $Branch
$MergeSubject = Get-MergeSubject -Title $TaskInfo.Title
$MergeMessage = "chore($($TaskInfo.Id)): $MergeSubject"

Write-Host "== Local task merge =="
Write-Host "== Task branch: $Branch =="
Write-Host "== Main branch: $MainBranch =="
Write-Host "== Merge message: $MergeMessage =="

git rev-parse --verify "$Branch^{commit}" | Out-Null
git rev-parse --verify "$MainBranch^{commit}" | Out-Null

if ($Branch -eq $MainBranch) {
  throw "Task branch and main branch are the same."
}

if ($CurrentBranch -ne $Branch) {
  git switch $Branch
}

Require-CleanTree

Write-Host "== Running quality gate on $Branch =="
& .\scripts\run_quality_gate.ps1
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

git switch $MainBranch
Require-CleanTree

git merge-base --is-ancestor $Branch $MainBranch
if ($LASTEXITCODE -eq 0) {
  Write-Host "$Branch is already merged into $MainBranch."
  exit 0
}

Write-Host "== Preparing no-commit merge =="
git merge --no-ff --no-commit $Branch
if ($LASTEXITCODE -ne 0) {
  Write-Host "Merge stopped before commit, likely because of conflicts."
  Write-Host "Resolve conflicts and commit manually, or run: git merge --abort"
  exit $LASTEXITCODE
}

Write-Host "== Running quality gate on merged result =="
& .\scripts\run_quality_gate.ps1
$QualityStatus = $LASTEXITCODE
if ($QualityStatus -ne 0) {
  Write-Host "Quality gate failed on the uncommitted merge result."
  Write-Host "Inspect the working tree. To cancel this merge, run: git merge --abort"
  exit $QualityStatus
}

Write-Host "== Creating merge commit =="
git commit `
  -m $MergeMessage `
  -m "Merged local branch: $Branch" `
  -m "Quality gate: passed"

Write-Host "== Final status =="
git status --short
git log --oneline -5
