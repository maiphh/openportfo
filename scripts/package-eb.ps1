<#
.SYNOPSIS
  BL-031: package single-EB bundle (Next.js static export served by FastAPI).

.DESCRIPTION
  1. Builds the frontend with NEXT_PUBLIC_API_URL="" (same-origin /api/*).
  2. Copies frontend/out/ -> backend/static_web/.
  3. Guards against baked absolute localhost API URLs.
  4. Zips backend (+static_web) into an EB application bundle, excluding
     .venv / __pycache__ / node_modules / .next via an explicit allow-list.

.PARAMETER AppUrl
  Public EB origin baked as NEXT_PUBLIC_APP_URL (Cognito callback fallback).
  Defaults to $env:APP_URL when set, else https://EB_PLACEHOLDER.
  Pass the real origin at deploy time, e.g.:
    .\scripts\package-eb.ps1 -AppUrl https://my-env.elasticbeanstalk.com

.PARAMETER OutputZip
  Destination zip path (default: <repo>/eb-bundle.zip).
#>
param(
  [string]$AppUrl = $(if ($env:APP_URL) { $env:APP_URL } else { "https://EB_PLACEHOLDER" }),
  [string]$OutputZip = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendDir = Join-Path $RepoRoot "backend"
$OutDir = Join-Path $FrontendDir "out"
$StaticWebDir = Join-Path $BackendDir "static_web"
if ([string]::IsNullOrWhiteSpace($OutputZip)) {
  $OutputZip = Join-Path $RepoRoot "eb-bundle.zip"
}

Write-Host "[package-eb] repo: $RepoRoot"
Write-Host "[package-eb] app-url: $AppUrl"

# 1. Build frontend with same-origin API base (BL-031 D3).
Push-Location $FrontendDir
try {
  $env:NEXT_PUBLIC_API_URL = ""
  $env:NEXT_PUBLIC_APP_URL = $AppUrl
  Write-Host "[package-eb] npm run build (NEXT_PUBLIC_API_URL=`"`")"
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "frontend build failed (exit $LASTEXITCODE)" }
}
finally {
  Pop-Location
}

# 2. Assert export output exists.
$indexHtml = Join-Path $OutDir "index.html"
$nextDir = Join-Path $OutDir "_next"
if (-not (Test-Path -LiteralPath $indexHtml)) { throw "missing $indexHtml - static export failed?" }
if (-not (Test-Path -LiteralPath $nextDir)) { throw "missing $nextDir - static export failed?" }
Write-Host "[package-eb] export OK: index.html + _next/ present"

# 3. Leak guard: baked absolute localhost API calls must not ship.
# NOTE: the inert `DEFAULT_API = "http://127.0.0.1:8000"` fallback literal in
# lib/api.ts is intentionally still bundled (dead branch when built with
# NEXT_PUBLIC_API_URL=""), so the guard fails only on absolute *API calls*
# (`127.0.0.1:8000/api`), which prove a stale absolute base survived.
$leaks = Get-ChildItem -LiteralPath $OutDir -Recurse -Include *.js, *.html, *.json -File |
  Select-String -Pattern "127\.0\.0\.1:8000/api" -SimpleMatch:$false
if ($leaks) {
  $leaks | Select-Object -First 5 | ForEach-Object { Write-Host $_.Path }
  throw "leak guard: absolute localhost API URL baked into frontend/out (rebuild with NEXT_PUBLIC_API_URL=`"`")"
}
$inert = (Get-ChildItem -LiteralPath $OutDir -Recurse -Include *.js -File |
  Select-String -Pattern "127\.0\.0\.1:8000" | Measure-Object).Count
Write-Host "[package-eb] leak guard OK (inert DEFAULT_API literal occurrences: $inert)"

# 4. Clean + copy out/ -> backend/static_web/.
if (Test-Path -LiteralPath $StaticWebDir) {
  Remove-Item -LiteralPath $StaticWebDir -Recurse -Force
}
New-Item -ItemType Directory -Path $StaticWebDir | Out-Null
Copy-Item -Path (Join-Path $OutDir "*") -Destination $StaticWebDir -Recurse -Force
if (-not (Test-Path -LiteralPath (Join-Path $StaticWebDir "index.html"))) { throw "copy failed: static_web/index.html missing" }
if (-not (Test-Path -LiteralPath (Join-Path $StaticWebDir "_next"))) { throw "copy failed: static_web/_next missing" }
Write-Host "[package-eb] copied out/ -> backend/static_web/"

# 5. Stage allow-list (excludes .venv/__pycache__/node_modules/.next by construction).
$stage = Join-Path ([System.IO.Path]::GetTempPath()) "openportfo-eb-stage"
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item -Path (Join-Path $BackendDir "app") -Destination (Join-Path $stage "app") -Recurse
foreach ($name in @("Procfile", "requirements.txt", ".ebextensions", "static_web")) {
  $src = Join-Path $BackendDir $name
  if (-not (Test-Path -LiteralPath $src)) { throw "missing backend/$name - cannot package" }
  Copy-Item -Path $src -Destination (Join-Path $stage $name) -Recurse
}
# Drop local-only artefacts from the staged app/ (pytest/app runs leave these).
# NOTE: filter via Where-Object, not -Include (PS 5.1 ignores -Include with
# -LiteralPath, which would match every file).
Get-ChildItem -LiteralPath (Join-Path $stage "app") -Recurse -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.PSIsContainer -and ($_.Name -eq "__pycache__") } |
  Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath (Join-Path $stage "app") -Recurse -Force -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
  Remove-Item -Force
if (Test-Path -LiteralPath (Join-Path $stage ".pytest_cache")) {
  Remove-Item -LiteralPath (Join-Path $stage ".pytest_cache") -Recurse -Force
}
Write-Host "[package-eb] staged: app/ Procfile requirements.txt .ebextensions/ static_web/"

# 6. Zip staging dir (zip root == EB application root).
if (Test-Path -LiteralPath $OutputZip) { Remove-Item -LiteralPath $OutputZip -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $OutputZip -Force

# 7. Contents check + size.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($OutputZip)
try {
  $entries = @($zip.Entries | ForEach-Object { $_.FullName -replace '\\', '/' })
  foreach ($required in @("static_web/index.html", "Procfile", "app/main.py")) {
    if (-not ($entries -contains $required)) { throw "bundle missing required entry: $required" }
  }
  $bad = @($entries | Where-Object { $_ -match "(\.venv/|__pycache__|node_modules/|\.next/)" })
  if ($bad.Count -gt 0) {
    $bad | Select-Object -First 5 | ForEach-Object { Write-Host $_ }
    throw "bundle contains excluded paths (see above)"
  }
  $hasNext = @($entries | Where-Object { $_ -like "static_web/_next/*" }).Count -gt 0
  if (-not $hasNext) { throw "bundle missing static_web/_next/ assets" }
  Write-Host ("[package-eb] contents OK: {0} entries (static_web/index.html, _next assets, Procfile, app/)" -f $entries.Count)
}
finally {
  $zip.Dispose()
}
$sizeMB = [math]::Round((Get-Item -LiteralPath $OutputZip).Length / 1MB, 2)
Write-Host "[package-eb] wrote $OutputZip ($sizeMB MB)"
