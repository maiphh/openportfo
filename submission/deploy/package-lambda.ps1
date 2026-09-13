<#
.SYNOPSIS
  Package openportfo-jobs.zip with Linux (manylinux) wheels for Lambda.

.DESCRIPTION
  Uses Docker linux/amd64 so Windows pip wheels are not uploaded.
  Output: <repo>/openportfo-jobs.zip (gitignored).
#>
param(
  [string]$OutputZip = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutputZip)) {
  $OutputZip = Join-Path $RepoRoot "openportfo-jobs.zip"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker is required to build a Linux Lambda zip on Windows. Start Docker Desktop."
}

$req = Join-Path $RepoRoot "infra\lambda\requirements-lambda.txt"
$handler = Join-Path $RepoRoot "backend\lambda_handler.py"
$appDir = Join-Path $RepoRoot "backend\app"
$inner = Join-Path $RepoRoot "infra\lambda\package-in-container.sh"
if (-not (Test-Path -LiteralPath $req)) { throw "missing $req" }
if (-not (Test-Path -LiteralPath $handler)) { throw "missing $handler" }
if (-not (Test-Path -LiteralPath $appDir)) { throw "missing $appDir" }
if (-not (Test-Path -LiteralPath $inner)) { throw "missing $inner" }

Write-Host "[package-lambda] docker linux/amd64 pip + app -> $OutputZip"
docker run --rm --platform linux/amd64 -v "${RepoRoot}:/opt/src" -w /opt/src public.ecr.aws/sam/build-python3.12:latest bash /opt/src/infra/lambda/package-in-container.sh
if ($LASTEXITCODE -ne 0) { throw "docker package-lambda failed (exit $LASTEXITCODE)" }

$built = Join-Path $RepoRoot "openportfo-jobs.zip"
if (-not (Test-Path -LiteralPath $built)) { throw "missing $built after docker package" }
if ($OutputZip -ne $built) {
  Copy-Item -LiteralPath $built -Destination $OutputZip -Force
}

$sizeMB = [math]::Round((Get-Item -LiteralPath $OutputZip).Length / 1MB, 2)
Write-Host "[package-lambda] wrote $OutputZip ($sizeMB MB)"
