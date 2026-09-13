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

.PARAMETER ApiUrl
  Optional HTTP API Gateway origin baked as NEXT_PUBLIC_API_URL (BL-035).
  Empty (default) keeps same-origin `/api/*` (BL-031).
  Example:
    .\scripts\package-eb.ps1 -AppUrl https://my-env.elasticbeanstalk.com `
      -ApiUrl https://abc123.execute-api.us-east-1.amazonaws.com

.PARAMETER OutputZip
  Destination zip path (default: <repo>/eb-bundle.zip).
#>
param(
  [string]$AppUrl = $(if ($env:APP_URL) { $env:APP_URL } else { "https://EB_PLACEHOLDER" }),
  [string]$ApiUrl = $(if ($env:API_URL) { $env:API_URL } else { "" }),
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
$apiUrlBake = if ([string]::IsNullOrWhiteSpace($ApiUrl)) { "" } else { $ApiUrl.Trim().TrimEnd('/') }
Write-Host "[package-eb] api-url: $(if ($apiUrlBake) { $apiUrlBake } else { '(same-origin /api/*)' })"

# 1. Build frontend. Empty NEXT_PUBLIC_API_URL = same-origin (BL-031).
# Non-empty = HTTP API Gateway origin (BL-035). Chat SSE uses chatApiBase()
# same-origin on public hosts, so we do not bake NEXT_PUBLIC_CHAT_API_URL.
# IMPORTANT: PowerShell `$env:VAR = ""` *removes* the variable, so Next never
# sees an empty string and leaves a runtime env lookup that falls back to
# 127.0.0.1:8000 in the browser. Bake via .env.production.local instead.
$prodEnvLocal = Join-Path $FrontendDir ".env.production.local"
$prodEnvBackup = Join-Path $FrontendDir ".env.production.local.package-eb.bak"
$hadProdEnvLocal = Test-Path -LiteralPath $prodEnvLocal
if ($hadProdEnvLocal) {
  Copy-Item -LiteralPath $prodEnvLocal -Destination $prodEnvBackup -Force
}
@(
  "NEXT_PUBLIC_API_URL=$apiUrlBake"
  "NEXT_PUBLIC_APP_URL=$AppUrl"
) | Set-Content -LiteralPath $prodEnvLocal -Encoding utf8
# process.env wins over dotenv files. A stale shell NEXT_PUBLIC_APP_URL from a
# prior package (e.g. http:// EB) would otherwise override .env.production.local.
if ($apiUrlBake) {
  $env:NEXT_PUBLIC_API_URL = $apiUrlBake
} else {
  Remove-Item Env:NEXT_PUBLIC_API_URL -ErrorAction SilentlyContinue
}
$env:NEXT_PUBLIC_APP_URL = $AppUrl
# Drop turbopack/.next caches so a prior http:// APP_URL bake cannot stick.
foreach ($stale in @(".next", "out")) {
  $stalePath = Join-Path $FrontendDir $stale
  if (Test-Path -LiteralPath $stalePath) {
    Remove-Item -LiteralPath $stalePath -Recurse -Force
  }
}
Push-Location $FrontendDir
try {
  Write-Host "[package-eb] npm run build (NEXT_PUBLIC_API_URL baked via .env.production.local)"
  Write-Host "[package-eb] NEXT_PUBLIC_API_URL=$(if ($apiUrlBake) { $apiUrlBake } else { '(empty same-origin)' })"
  Write-Host "[package-eb] NEXT_PUBLIC_APP_URL=$AppUrl (process env + .env.production.local)"
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "frontend build failed (exit $LASTEXITCODE)" }
}
finally {
  Pop-Location
  Remove-Item Env:NEXT_PUBLIC_APP_URL -ErrorAction SilentlyContinue
  Remove-Item Env:NEXT_PUBLIC_API_URL -ErrorAction SilentlyContinue
  if ($hadProdEnvLocal -and (Test-Path -LiteralPath $prodEnvBackup)) {
    Move-Item -LiteralPath $prodEnvBackup -Destination $prodEnvLocal -Force
  } else {
    Remove-Item -LiteralPath $prodEnvLocal -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $prodEnvBackup -Force -ErrorAction SilentlyContinue
  }
}

# 2. Assert export output exists.
$indexHtml = Join-Path $OutDir "index.html"
$nextDir = Join-Path $OutDir "_next"
if (-not (Test-Path -LiteralPath $indexHtml)) { throw "missing $indexHtml - static export failed?" }
if (-not (Test-Path -LiteralPath $nextDir)) { throw "missing $nextDir - static export failed?" }
Write-Host "[package-eb] export OK: index.html + _next/ present"

# 3. Leak guard: same-origin bake must actually inline NEXT_PUBLIC_API_URL.
# - Contiguous `127.0.0.1:8000/api` = stale absolute base survived.
# - Runtime `.env.NEXT_PUBLIC_API_URL` access = empty PowerShell env deleted
#   the var at build time (must not ship).
$outJs = Get-ChildItem -LiteralPath $OutDir -Recurse -Include *.js, *.html, *.json -File
$leaks = $outJs | Select-String -Pattern "127\.0\.0\.1:8000/api" -SimpleMatch:$false
if ($leaks) {
  $leaks | Select-Object -First 5 | ForEach-Object { Write-Host $_.Path }
  throw "leak guard: absolute localhost API URL baked into frontend/out (rebuild with NEXT_PUBLIC_API_URL=`"`")"
}
$runtimeEnv = $outJs | Select-String -Pattern "\.env\.NEXT_PUBLIC_API_URL"
if ($runtimeEnv) {
  $runtimeEnv | Select-Object -First 5 | ForEach-Object { Write-Host $_.Path }
  throw "leak guard: NEXT_PUBLIC_API_URL was not inlined (empty PowerShell env removes the var; bake via .env.production.local)"
}
$inert = ($outJs | Select-String -Pattern "127\.0\.0\.1:8000" | Measure-Object).Count
Write-Host "[package-eb] leak guard OK (inert DEFAULT_API literal occurrences: $inert)"
if ($apiUrlBake) {
  $bakedApi = $outJs | Select-String -SimpleMatch $apiUrlBake
  if (-not $bakedApi) {
    throw "API_URL guard: expected baked NEXT_PUBLIC_API_URL=$apiUrlBake in frontend/out"
  }
  Write-Host "[package-eb] API_URL bake OK: $apiUrlBake"
}
if ($AppUrl -match '^https://') {
  $httpBake = $outJs | Select-String -Pattern ('NEXT_PUBLIC_APP_URL:"' + ($AppUrl -replace '^https://','http://') + '"')
  if ($httpBake) {
    throw "APP_URL guard: expected https bake but found http:// NEXT_PUBLIC_APP_URL (clean .next and rebuild)"
  }
}

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
foreach ($name in @("Procfile", "requirements.txt", ".ebextensions", ".platform", "static_web")) {
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
Write-Host "[package-eb] staged: app/ Procfile requirements.txt .ebextensions/ .platform/ static_web/"

# 6. Zip staging dir with forward-slash entry names (Compress-Archive uses
# backslashes; Linux unzip on EB rejects those bundles). Preserve +x on
# .platform/hooks scripts so postdeploy hooks run.
if (Test-Path -LiteralPath $OutputZip) { Remove-Item -LiteralPath $OutputZip -Force }
python -c @"
import zipfile
from pathlib import Path
stage = Path(r'$stage')
out_zip = Path(r'$OutputZip')
with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(stage.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(stage).as_posix()
        info = zipfile.ZipInfo(rel)
        info.compress_type = zipfile.ZIP_DEFLATED
        # EB requires executable bit on .platform/hooks/*
        mode = 0o755 if '/hooks/' in rel and rel.endswith('.sh') else 0o644
        info.external_attr = (mode & 0xFFFF) << 16
        info.date_time = (2026, 1, 1, 0, 0, 0)
        zf.writestr(info, f.read_bytes())
"@
if ($LASTEXITCODE -ne 0) { throw "python zip failed (exit $LASTEXITCODE)" }

# 7. Contents check + size.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($OutputZip)
try {
  $entries = @($zip.Entries | ForEach-Object { $_.FullName -replace '\\', '/' })
  $rawNames = @($zip.Entries | ForEach-Object { $_.FullName })
  if (@($rawNames | Where-Object { $_ -match '\\' }).Count -gt 0) {
    throw "bundle has backslash path separators (EB Linux unzip will fail)"
  }
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
