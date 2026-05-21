# Pre-Docker checks for School Domnak (PowerShell)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== School Domnak preflight ===" -ForegroundColor Cyan

$checks = @()

function Test-Check($name, $ok, $hint) {
    $script:checks += [pscustomobject]@{ Name = $name; Ok = $ok; Hint = $hint }
    if ($ok) { Write-Host "[OK]   $name" -ForegroundColor Green }
    else { Write-Host "[FAIL] $name - $hint" -ForegroundColor Red }
}

Test-Check "Docker running" { (docker info 2>$null) -ne $null } "Start Docker Desktop"
Test-Check "Root .env" { Test-Path ".env" } "Copy .env.example to .env"
Test-Check "Frontend Dockerfile" { Test-Path "Frontend\Dockerfile" } ""
Test-Check "docker-compose.yml" { Test-Path "docker-compose.yml" } ""
Test-Check "nginx config" { Test-Path "nginx\conf.d\app.conf" } ""
Test-Check "secrets JSON (optional)" { Test-Path "secrets\service-account-key.json" } "Copy Google key to secrets\service-account-key.json"

try {
    docker compose config --quiet 2>$null | Out-Null
    Test-Check "Compose config valid" $true ""
} catch {
    Test-Check "Compose config valid" $false $_.Exception.Message
}

$failed = @($checks | Where-Object { -not $_.Ok })
if ($failed.Count -gt 0) {
    Write-Host "`nFix failures above before: docker compose up -d --build" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nAll checks passed. Run: docker compose up -d --build" -ForegroundColor Cyan
exit 0
