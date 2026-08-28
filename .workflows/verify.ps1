[CmdletBinding()]
param(
    [ValidateSet("quick", "full")]
    [string]$Profile = "full",
    [switch]$SkipLocalStack,
    [switch]$SkipE2E
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$resultsDir = Join-Path $PSScriptRoot "runs"
$results = [System.Collections.Generic.List[object]]::new()

$pythonCandidates = @(
    (Join-Path $backendDir ".venv\Scripts\python.exe"),
    (Join-Path $backendDir ".venv/bin/python")
)
$python = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $python) {
    $pythonCommand = Get-Command python3, python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pythonCommand) {
        $python = $pythonCommand.Source
    }
}
if (-not $python) {
    throw "No Python interpreter found. Create backend/.venv or install Python 3.12."
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)]
        [string]$Executable,
        [string[]]$Arguments = @()
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable exited with code $LASTEXITCODE"
    }
}

function Invoke-Gate {
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    $started = Get-Date
    $status = "pass"
    $detail = ""
    try {
        & $Action
    }
    catch {
        $status = "fail"
        $detail = $_.Exception.Message
        Write-Host "FAILED: $detail" -ForegroundColor Red
    }
    $duration = [Math]::Round(((Get-Date) - $started).TotalSeconds, 2)
    $results.Add([pscustomobject]@{
        gate = $Name
        status = $status
        durationSeconds = $duration
        detail = $detail
    })
}

Invoke-Gate "workflow-contract" {
    $required = @(
        "AGENTS.md",
        "backend/AGENTS.md",
        "frontend/AGENTS.md",
        ".workflows/feature-cycle.md",
        ".workflows/verify.ps1",
        ".agents/skills/playwright-verification/SKILL.md",
        ".agents/skills/localstack-verification/SKILL.md",
        ".agents/skills/localstack-verification/scripts/verify_localstack.py",
        "frontend/playwright.config.ts",
        "frontend/e2e/smoke.spec.ts"
    )
    $missing = $required | Where-Object { -not (Test-Path (Join-Path $repoRoot $_)) }
    if ($missing) {
        throw "Missing workflow files: $($missing -join ', ')"
    }

    & git check-ignore -q ".agents/skills/playwright-verification/SKILL.md"
    $ignoreCode = $LASTEXITCODE
    if ($ignoreCode -eq 0) {
        throw "Repository skills are still ignored by git."
    }
    if ($ignoreCode -ne 1) {
        throw "git check-ignore exited with code $ignoreCode"
    }
}

Invoke-Gate "ports-isolation" {
    $pattern = "^\s*(from\s+(boto3|botocore|httpx|requests)\b|import\s+(boto3|botocore|httpx|requests)\b)"
    $paths = @(
        (Join-Path $backendDir "app/services"),
        (Join-Path $backendDir "app/api"),
        (Join-Path $backendDir "app/domain"),
        (Join-Path $backendDir "app/jobs")
    )
    $matches = & rg -n $pattern @paths 2>&1
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "AWS or HTTP SDK imports were found outside backend/app/adapters."
    }
    if ($code -ne 1) {
        throw "rg ports-isolation check exited with code $code"
    }
}

Invoke-Gate "backend-tests" {
    Push-Location $backendDir
    try {
        Invoke-Checked -Executable $python -Arguments @("-m", "pytest", "-q", "-p", "no:cacheprovider")
    }
    finally {
        Pop-Location
    }
}

Invoke-Gate "frontend-lint" {
    Push-Location $frontendDir
    try {
        Invoke-Checked -Executable "npm" -Arguments @("run", "lint")
    }
    finally {
        Pop-Location
    }
}

Invoke-Gate "frontend-unit" {
    Push-Location $frontendDir
    try {
        Invoke-Checked -Executable "npm" -Arguments @("test")
    }
    finally {
        Pop-Location
    }
}

if ($Profile -eq "full") {
    Invoke-Gate "frontend-build" {
        Push-Location $frontendDir
        try {
            Invoke-Checked -Executable "npm" -Arguments @("run", "build")
        }
        finally {
            Pop-Location
        }
    }

    if (-not $SkipE2E) {
        Invoke-Gate "playwright-e2e" {
            Push-Location $frontendDir
            try {
                Invoke-Checked -Executable "npm" -Arguments @("run", "test:e2e")
            }
            finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipLocalStack) {
        Invoke-Gate "localstack-contract" {
            Push-Location $repoRoot
            try {
                Invoke-Checked -Executable "docker" -Arguments @("compose", "up", "-d", "--wait", "--wait-timeout", "120", "localstack")
                $probe = Join-Path $repoRoot ".agents/skills/localstack-verification/scripts/verify_localstack.py"
                $probePassed = $false
                for ($attempt = 1; $attempt -le 30; $attempt++) {
                    & $python $probe
                    if ($LASTEXITCODE -eq 0) {
                        $probePassed = $true
                        break
                    }
                    Start-Sleep -Seconds 2
                }
                if (-not $probePassed) {
                    throw "LocalStack contract did not become ready within 60 seconds."
                }
            }
            finally {
                Pop-Location
            }
        }
    }
}

New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$report = [pscustomobject]@{
    profile = $Profile
    generatedAt = (Get-Date).ToString("o")
    repository = $repoRoot
    passed = @($results | Where-Object status -eq "pass").Count
    failed = @($results | Where-Object status -eq "fail").Count
    gates = $results
}
$json = $report | ConvertTo-Json -Depth 6
$timestampedReport = Join-Path $resultsDir "verify-$stamp.json"
$latestReport = Join-Path $resultsDir "latest.json"
$latestProfileReport = Join-Path $resultsDir "latest-$Profile.json"
[System.IO.File]::WriteAllText($timestampedReport, $json)
[System.IO.File]::WriteAllText($latestReport, $json)
[System.IO.File]::WriteAllText($latestProfileReport, $json)

Write-Host ""
Write-Host "=== cycle summary ===" -ForegroundColor Cyan
$results | Format-Table gate, status, durationSeconds, detail -AutoSize
Write-Host "Evidence: $latestReport"

if ($report.failed -gt 0) {
    exit 1
}
exit 0
