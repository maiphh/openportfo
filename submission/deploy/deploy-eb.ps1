<#
.SYNOPSIS
  BL-036: roll a new application version onto the EXISTING Elastic Beanstalk env.

.DESCRIPTION
  1. Packages the current tree (scripts/package-eb.ps1).
  2. Uploads eb-bundle.zip to the EB versions bucket.
  3. Creates a new application version.
  4. Updates openportfo-api-env in place (same env id / CNAME).

  Does not create an application, environment, stack, Lambda, or HTTP API.
  Does not run CloudFormation.

  Usage (repo root, Academy lab session must be started):
    .\scripts\deploy-eb.ps1

.PARAMETER AppUrl
  Public https origin baked into the frontend (Cognito). Override with $env:EB_APP_URL.

.PARAMETER ApiUrl
  HTTP API origin baked as NEXT_PUBLIC_API_URL. Override with $env:EB_API_URL.

.PARAMETER SkipWait
  Return after update-environment is accepted (do not poll Ready).
#>
param(
  [string]$AppUrl = $(if ($env:EB_APP_URL) { $env:EB_APP_URL } else { "https://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com" }),
  [string]$ApiUrl = $(if ($env:EB_API_URL) { $env:EB_API_URL } else { "https://7duvngr98b.execute-api.us-east-1.amazonaws.com" }),
  [string]$ApplicationName = $(if ($env:EB_APPLICATION) { $env:EB_APPLICATION } else { "openportfo-api" }),
  [string]$EnvironmentName = $(if ($env:EB_ENVIRONMENT) { $env:EB_ENVIRONMENT } else { "openportfo-api-env" }),
  [string]$Region = $(if ($env:EB_REGION) { $env:EB_REGION } else { "us-east-1" }),
  [string]$S3Bucket = $(if ($env:EB_S3_BUCKET) { $env:EB_S3_BUCKET } else { "elasticbeanstalk-us-east-1-059358625850" }),
  [string]$S3Prefix = "openportfo-api",
  [switch]$SkipWait
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PackageScript = Join-Path $PSScriptRoot "package-eb.ps1"
$ZipPath = Join-Path $RepoRoot "eb-bundle.zip"

if (-not (Test-Path -LiteralPath $PackageScript)) {
  throw "missing $PackageScript"
}
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
  throw "aws CLI not found. Start the Academy lab and configure credentials first."
}

Write-Host "[deploy-eb] application: $ApplicationName"
Write-Host "[deploy-eb] environment: $EnvironmentName (update existing only)"
Write-Host "[deploy-eb] region:      $Region"
Write-Host "[deploy-eb] app-url:     $AppUrl"
Write-Host "[deploy-eb] api-url:     $ApiUrl"

$envJson = aws elasticbeanstalk describe-environments `
  --environment-names $EnvironmentName `
  --region $Region `
  --query "Environments[0].{Id:EnvironmentId,Name:EnvironmentName,App:ApplicationName,Status:Status,Health:Health,CNAME:CNAME,Version:VersionLabel}" `
  --output json
if ($LASTEXITCODE -ne 0) { throw "describe-environments failed (exit $LASTEXITCODE)" }

$envInfo = $envJson | ConvertFrom-Json
if (-not $envInfo -or -not $envInfo.Id -or $envInfo.Id -eq "None") {
  throw "Elastic Beanstalk environment '$EnvironmentName' was not found. This script updates an existing env; it will not create one."
}
if ($envInfo.App -ne $ApplicationName) {
  throw "Environment '$EnvironmentName' belongs to application '$($envInfo.App)', expected '$ApplicationName'."
}
if ($envInfo.Status -eq "Terminated") {
  throw "Environment '$EnvironmentName' is Terminated. This script will not create a replacement."
}
if ($envInfo.Status -eq "Updating" -or $envInfo.Status -eq "Launching") {
  throw "Environment '$EnvironmentName' is $($envInfo.Status). Wait until Ready, then rerun."
}

Write-Host "[deploy-eb] current: $($envInfo.Id) status=$($envInfo.Status) health=$($envInfo.Health) version=$($envInfo.Version)"

Write-Host "[deploy-eb] packaging..."
& $PackageScript -AppUrl $AppUrl -ApiUrl $ApiUrl -OutputZip $ZipPath
if ($LASTEXITCODE -ne 0) { throw "package-eb.ps1 failed (exit $LASTEXITCODE)" }
if (-not (Test-Path -LiteralPath $ZipPath)) { throw "missing $ZipPath after package" }

$label = "v-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss")
$key = "$S3Prefix/eb-bundle-$label.zip"

Write-Host "[deploy-eb] upload s3://$S3Bucket/$key"
aws s3 cp $ZipPath "s3://$S3Bucket/$key" --region $Region
if ($LASTEXITCODE -ne 0) { throw "s3 cp failed (exit $LASTEXITCODE)" }

Write-Host "[deploy-eb] create application version $label"
aws elasticbeanstalk create-application-version `
  --application-name $ApplicationName `
  --version-label $label `
  --description "deploy-eb $label" `
  --source-bundle "S3Bucket=$S3Bucket,S3Key=$key" `
  --region $Region | Out-Null
if ($LASTEXITCODE -ne 0) { throw "create-application-version failed (exit $LASTEXITCODE)" }

Write-Host "[deploy-eb] update-environment $EnvironmentName -> $label"
aws elasticbeanstalk update-environment `
  --environment-name $EnvironmentName `
  --version-label $label `
  --region $Region | Out-Null
if ($LASTEXITCODE -ne 0) { throw "update-environment failed (exit $LASTEXITCODE)" }

if ($SkipWait) {
  Write-Host "[deploy-eb] SkipWait: update accepted. Version $label is rolling out."
  return
}

Write-Host "[deploy-eb] waiting until Ready..."
$deadline = (Get-Date).AddMinutes(10)
do {
  Start-Sleep -Seconds 15
  $envJson = aws elasticbeanstalk describe-environments `
    --environment-names $EnvironmentName `
    --region $Region `
    --query "Environments[0].{Status:Status,Health:Health,Version:VersionLabel,CNAME:CNAME}" `
    --output json
  $envInfo = $envJson | ConvertFrom-Json
  Write-Host ("[deploy-eb] {0} status={1} health={2} version={3}" -f (Get-Date -Format "HH:mm:ss"), $envInfo.Status, $envInfo.Health, $envInfo.Version)
} while ($envInfo.Status -eq "Updating" -and (Get-Date) -lt $deadline)

if ($envInfo.Status -ne "Ready") {
  throw "Environment did not become Ready (status=$($envInfo.Status) health=$($envInfo.Health) version=$($envInfo.Version))"
}

$healthUrl = "http://$($envInfo.CNAME)/health"
Write-Host "[deploy-eb] smoke $healthUrl"
$health = curl.exe -sS --max-time 20 $healthUrl
if ($health -notmatch '"status"\s*:\s*"ok"') {
  throw "health check failed: $health"
}
Write-Host "[deploy-eb] health OK"

$authMe = "$($ApiUrl.TrimEnd('/'))/api/auth/me"
Write-Host "[deploy-eb] smoke $authMe"
$gwOut = curl.exe -sS -w "`nhttp_code=%{http_code}" --max-time 20 $authMe
if ($gwOut -notmatch "http_code=401" -and $gwOut -notmatch "http_code=200") {
  Write-Host "[deploy-eb] warning: Gateway /api/auth/me unexpected: $gwOut"
} else {
  Write-Host "[deploy-eb] Gateway proxy OK"
}

Write-Host "[deploy-eb] done. env=$EnvironmentName version=$($envInfo.Version) health=$($envInfo.Health)"
Write-Host "[deploy-eb] UI: $AppUrl  (accept the EB cert warning; REST goes through $ApiUrl)"
