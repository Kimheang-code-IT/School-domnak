# Start School Domnak via Docker Compose with Nginx load balancing (Windows)
# If "running scripts is disabled", use:  scripts\deploy-docker.cmd
# Or:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy-docker.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Get-EnvInt([string]$Name, [int]$Default) {
    if (-not (Test-Path ".env")) { return $Default }
    $line = Get-Content ".env" | Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*=" } | Select-Object -First 1
    if (-not $line) { return $Default }
    $val = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
    if ($val -match '^\d+$') { return [int]$val }
    return $Default
}

$backendReplicas = Get-EnvInt "BACKEND_REPLICAS" 2
$celeryReplicas = Get-EnvInt "CELERY_WORKER_REPLICAS" 2
if ($backendReplicas -lt 1) { $backendReplicas = 1 }
if ($celeryReplicas -lt 1) { $celeryReplicas = 1 }

Write-Host "=== 1/2 Preflight ===" -ForegroundColor Cyan
& "$PSScriptRoot\preflight-docker.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 2/2 docker compose up (backend x$backendReplicas, celery_worker x$celeryReplicas) ===" -ForegroundColor Cyan
docker compose up -d --build --scale "backend=$backendReplicas" --scale "celery_worker=$celeryReplicas"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Ready (Nginx load-balances API across $backendReplicas backend container(s)):" -ForegroundColor Green
Write-Host "  App:    http://localhost:18080"
Write-Host "  API:    http://localhost:18080/docs"
Write-Host "  Wi-Fi:  run .\scripts\open-wifi-access.ps1 for LAN URLs"
Write-Host ""
Write-Host "Tune in .env: BACKEND_REPLICAS, CELERY_WORKER_REPLICAS, UVICORN_WORKERS, CELERY_WORKER_CONCURRENCY"
Write-Host "First login (after seed): admin@gmail.com / admin12!@$"
Write-Host "Seed DB:     docker compose exec backend python scripts/seed_data.py"
Write-Host "Reset DB:    docker compose exec backend python scripts/reset_database.py"
Write-Host "Logs:    docker compose logs -f backend nginx"
