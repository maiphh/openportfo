<#
.SYNOPSIS
  BL-037: update the EXISTING openportfo-jobs Lambda and EventBridge rules.

.DESCRIPTION
  1. Packages a Linux zip (scripts/package-lambda.ps1).
  2. update-function-code on openportfo-jobs (does not create a function).
  3. Merges SMTP_* from backend/.env into the existing Lambda env (no echo).
  4. Aligns EventBridge: news/price/snapshot at 00:00 ICT; email at 00:15 ICT.
  5. Smokes {"job":"email"}.

  Does not run CloudFormation. Does not create a new Lambda.

  Usage (repo root, Academy lab + Docker running):
    .\scripts\deploy-lambda.ps1
#>
param(
  [string]$FunctionName = $(if ($env:JOBS_LAMBDA_NAME) { $env:JOBS_LAMBDA_NAME } else { "openportfo-jobs" }),
  [string]$Region = $(if ($env:EB_REGION) { $env:EB_REGION } else { "us-east-1" }),
  [switch]$SkipPackage,
  [switch]$SkipEventBridge,
  [switch]$SkipEnv,
  [switch]$SkipInvoke
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PackageScript = Join-Path $PSScriptRoot "package-lambda.ps1"
$ZipPath = Join-Path $RepoRoot "openportfo-jobs.zip"
$DotEnv = Join-Path $RepoRoot "backend\.env"
$Account = "059358625850"
$FunctionArn = "arn:aws:lambda:${Region}:${Account}:function:${FunctionName}"

function To-AwsFileUri([string]$Path, [string]$Scheme = "file") {
  $full = (Resolve-Path -LiteralPath $Path).Path
  $unix = $full -replace '\\', '/'
  return "${Scheme}://${unix}"
}

function Read-DotEnvFile([string]$Path) {
  $map = @{}
  if (-not (Test-Path -LiteralPath $Path)) { return $map }
  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $k = $line.Substring(0, $eq).Trim()
    $v = $line.Substring($eq + 1).Trim()
    if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
      $v = $v.Substring(1, $v.Length - 2)
    }
    $map[$k] = $v
  }
  return $map
}

function Wait-LambdaReady([string]$Name, [string]$AwsRegion) {
  $deadline = (Get-Date).AddMinutes(5)
  do {
    Start-Sleep -Seconds 3
    $st = aws lambda get-function-configuration --function-name $Name --region $AwsRegion --query LastUpdateStatus --output text
    if ($LASTEXITCODE -ne 0) { throw "get-function-configuration failed (exit $LASTEXITCODE)" }
    Write-Host "[deploy-lambda] LastUpdateStatus=$st"
  } while ($st -eq "InProgress" -and (Get-Date) -lt $deadline)
  if ($st -eq "Failed") { throw "Lambda update Failed" }
  if ($st -ne "Successful") { throw "Lambda not ready (LastUpdateStatus=$st)" }
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
  throw "aws CLI not found. Start the Academy lab and configure credentials first."
}

Write-Host "[deploy-lambda] function: $FunctionName (update existing only)"
Write-Host "[deploy-lambda] region:   $Region"

$fn = aws lambda get-function-configuration --function-name $FunctionName --region $Region --query "{Name:FunctionName,Runtime:Runtime,Handler:Handler,State:State}" --output json
if ($LASTEXITCODE -ne 0) {
  throw "Lambda function '$FunctionName' was not found. This script updates an existing function; it will not create one."
}
Write-Host "[deploy-lambda] current: $fn"

if (-not $SkipPackage) {
  Write-Host "[deploy-lambda] packaging Linux zip..."
  & $PackageScript -OutputZip $ZipPath
  if ($LASTEXITCODE -ne 0) { throw "package-lambda.ps1 failed (exit $LASTEXITCODE)" }
}
if (-not (Test-Path -LiteralPath $ZipPath)) {
  throw "missing $ZipPath - run package-lambda first"
}

Write-Host "[deploy-lambda] update-function-code"
$zipUri = To-AwsFileUri $ZipPath "fileb"
aws lambda update-function-code --function-name $FunctionName --zip-file $zipUri --region $Region --query "{CodeSize:CodeSize,LastModified:LastModified}" --output json
if ($LASTEXITCODE -ne 0) { throw "update-function-code failed (exit $LASTEXITCODE)" }
Wait-LambdaReady -Name $FunctionName -AwsRegion $Region

if (-not $SkipEnv) {
  $tmpCfg = Join-Path $env:TEMP "openportfo-lambda-cfg-$PID.json"
  $tmpEnv = Join-Path $env:TEMP "openportfo-lambda-env-$PID.json"
  try {
    aws lambda get-function-configuration --function-name $FunctionName --region $Region --query Environment.Variables --output json | Set-Content -LiteralPath $tmpCfg -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw "could not read current Lambda env" }
    $vars = Get-Content -LiteralPath $tmpCfg -Raw | ConvertFrom-Json
    $merged = @{}
    if ($vars) {
      $vars.PSObject.Properties | ForEach-Object { $merged[$_.Name] = [string]$_.Value }
    }
    $local = Read-DotEnvFile $DotEnv
    foreach ($key in @("SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_HOST", "SMTP_PORT", "SES_FROM_EMAIL")) {
      if ($local.ContainsKey($key) -and -not [string]::IsNullOrWhiteSpace($local[$key])) {
        $merged[$key] = [string]$local[$key]
      }
    }
    $hasSmtp = $merged.ContainsKey("SMTP_USERNAME") -and $merged.ContainsKey("SMTP_PASSWORD") -and $merged["SMTP_USERNAME"] -and $merged["SMTP_PASSWORD"]
    $payload = @{ Variables = $merged }
    $payload | ConvertTo-Json -Compress -Depth 8 | Set-Content -LiteralPath $tmpEnv -Encoding ascii
    Write-Host "[deploy-lambda] update-function-configuration (SMTP present: $hasSmtp)"
    $envUri = To-AwsFileUri $tmpEnv
    aws lambda update-function-configuration --function-name $FunctionName --region $Region --environment $envUri --query "{LastModified:LastModified,Timeout:Timeout}" --output json
    if ($LASTEXITCODE -ne 0) { throw "update-function-configuration failed (exit $LASTEXITCODE)" }
  }
  finally {
    Remove-Item -LiteralPath $tmpCfg -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tmpEnv -Force -ErrorAction SilentlyContinue
  }
  Wait-LambdaReady -Name $FunctionName -AwsRegion $Region
}

if (-not $SkipEventBridge) {
  $midnight = 'cron(0 17 * * ? *)'
  $emailCron = 'cron(15 17 * * ? *)'
  $rules = @(
    @{ Name = "openportfo-job-news"; Cron = $midnight; Desc = "Daily news ingest at 00:00 ICT (no FX)"; Id = "NewsJob"; Sid = "AllowEventBridgeNews"; Input = '{"job":"news"}' },
    @{ Name = "openportfo-job-price"; Cron = $midnight; Desc = "Price cache warm at 00:00 ICT (no FX)"; Id = "PriceJob"; Sid = "AllowEventBridgePrice"; Input = '{"job":"price"}' },
    @{ Name = "openportfo-job-snapshot"; Cron = $midnight; Desc = "Portfolio snapshot at 00:00 ICT (no FX)"; Id = "SnapshotJob"; Sid = "AllowEventBridgeSnapshot"; Input = '{"job":"snapshot"}' },
    @{ Name = "openportfo-job-email"; Cron = $emailCron; Desc = "Daily portfolio email at 00:15 ICT (after snapshot)"; Id = "EmailJob"; Sid = "AllowEventBridgeEmail"; Input = '{"job":"email"}' }
  )
  foreach ($r in $rules) {
    Write-Host "[deploy-lambda] put-rule $($r.Name) $($r.Cron)"
    aws events put-rule --name $r.Name --region $Region --schedule-expression $r.Cron --state ENABLED --description $r.Desc | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "put-rule $($r.Name) failed" }
    $escapedInput = $r.Input.Replace('\', '\\').Replace('"', '\"')
    $tgt = Join-Path $env:TEMP "openportfo-eb-target-$($r.Name).json"
    ('[{"Id":"' + $r.Id + '","Arn":"' + $FunctionArn + '","Input":"' + $escapedInput + '"}]') | Set-Content -LiteralPath $tgt -Encoding ascii
    $tgtUri = To-AwsFileUri $tgt
    aws events put-targets --rule $r.Name --region $Region --targets $tgtUri | Out-Null
    $tgtCode = $LASTEXITCODE
    Remove-Item -LiteralPath $tgt -Force -ErrorAction SilentlyContinue
    if ($tgtCode -ne 0) { throw "put-targets $($r.Name) failed" }
    $src = "arn:aws:events:${Region}:${Account}:rule/$($r.Name)"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $permOut = aws lambda add-permission --function-name $FunctionName --region $Region --statement-id $r.Sid --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn $src 2>&1 | Out-String
    $ErrorActionPreference = $prevEap
    if ($permOut -match "An error occurred" -and $permOut -notmatch "ResourceConflictException") {
      throw "add-permission $($r.Sid) failed: $permOut"
    }
  }
}

if (-not $SkipInvoke) {
  $outFile = Join-Path $RepoRoot ".workflows\runs\lambda-email-invoke.json"
  New-Item -ItemType Directory -Force -Path (Split-Path $outFile) | Out-Null
  $payloadPath = Join-Path $env:TEMP "openportfo-email-payload.json"
  '{"job":"email"}' | Set-Content -LiteralPath $payloadPath -Encoding ascii
  Write-Host '[deploy-lambda] invoke {"job":"email"}'
  $payloadUri = To-AwsFileUri $payloadPath
  aws lambda invoke --function-name $FunctionName --region $Region --cli-binary-format raw-in-base64-out --payload $payloadUri $outFile --query "{StatusCode:StatusCode,FunctionError:FunctionError}" --output json
  Remove-Item -LiteralPath $payloadPath -Force -ErrorAction SilentlyContinue
  if ($LASTEXITCODE -ne 0) { throw "lambda invoke failed (exit $LASTEXITCODE)" }
  Write-Host "[deploy-lambda] invoke result: $outFile"
}

Write-Host "[deploy-lambda] done. function=$FunctionName"
Write-Host "[deploy-lambda] schedules: news/price/snapshot 00:00 ICT; email 00:15 ICT"
