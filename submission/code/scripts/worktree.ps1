#Requires -Version 5.1
<#
.SYNOPSIS
  Create a git worktree + branch for an unrelated feature (orchestration rule).

.DESCRIPTION
  One worktree per unrelated feature. Related BLs may share integration branch only if orchestrator batches them.
  Creates branch feat/BL-XXX-slug and worktree at D:\rmit\cloud\a3-wt-blXXX (Windows) or ../a3-wt-blXXX.

.PARAMETER Id
  Backlog ID, e.g., BL-027 (with or without BL- prefix).

.PARAMETER Slug
  Kebab slug, e.g., portfolio-csv, notifications.

.PARAMETER Base
  Base branch to branch from (default: main).

.PARAMETER WorktreeRoot
  Parent dir for worktrees (default: D:\rmit\cloud).

.EXAMPLE
  .\scripts\worktree.ps1 -Id BL-027 -Slug portfolio-csv
  .\scripts\worktree.ps1 -Id 028 -Slug chatbot-memory -Base main
#>
param(
  [Parameter(Mandatory=$true)][string]$Id,
  [Parameter(Mandatory=$true)][string]$Slug,
  [string]$Base = "main",
  [string]$WorktreeRoot = "D:\rmit\cloud"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Normalize Id to BL-XXX
if ($Id -match '^\d+$') { $Id = "BL-$($Id.PadLeft(3,'0'))" }
elseif ($Id -match '^BL-?(\d+)$') { $Id = "BL-$($Matches[1].PadLeft(3,'0'))" }
elseif ($Id -notmatch '^BL-\d{3}$') { throw "Id must be BL-XXX or XXX, got: $Id" }

$Slug = $Slug.ToLower() -replace '[^a-z0-9]+','-' -replace '^-|-$',''
if (-not $Slug) { throw "Slug empty after sanitization" }

$Branch = "feat/$Id-$Slug"
$Num = $Id -replace 'BL-',''
$WorktreePath = Join-Path $WorktreeRoot "a3-wt-bl$Num"

Write-Host "Base: $Base" -ForegroundColor Cyan
Write-Host "Branch: $Branch" -ForegroundColor Cyan
Write-Host "Worktree: $WorktreePath" -ForegroundColor Cyan

# Preflight: git worktree list
Write-Host "`nExisting worktrees:" -ForegroundColor Yellow
git worktree list

# Validate base exists, fetch optional
$baseExists = git branch --list $Base
if (-not $baseExists) {
  $originBase = git branch -r --list "origin/$Base"
  if (-not $originBase) { throw "Base branch $Base not found locally or on origin" }
  Write-Host "Base $Base not local, using origin/$Base" -ForegroundColor Yellow
}

if (Test-Path -LiteralPath $WorktreePath) {
  throw "Worktree path already exists: $WorktreePath (remove or choose different Id)"
}

$branchExists = git branch --list $Branch
if ($branchExists) {
  throw "Branch already exists: $Branch (choose different slug or delete branch)"
}

# Ensure clean worktree before branching (optional check)
$status = git status --porcelain
if ($status) {
  Write-Host "Warning: working tree has uncommitted changes on $(git branch --show-current). Proceeding anyway." -ForegroundColor Yellow
}

Write-Host "`nCreating branch $Branch from $Base..." -ForegroundColor Green
git branch $Branch $Base
if (-not $?) { throw "Failed to create branch $Branch from $Base" }

Write-Host "Adding worktree at $WorktreePath..." -ForegroundColor Green
git worktree add $WorktreePath $Branch
if (-not $?) {
  git branch -D $Branch | Out-Null
  throw "Failed to add worktree"
}

Write-Host "`nDone. Next:" -ForegroundColor Green
Write-Host "  cd `"$WorktreePath`""
Write-Host "  git log --oneline -5"
Write-Host "  # hand to Implementor with workdir=$WorktreePath"
Write-Host "`nTo remove later:" -ForegroundColor Yellow
Write-Host "  git worktree remove `"$WorktreePath`""
Write-Host "  git branch -D $Branch  # if not merged"
git worktree list
