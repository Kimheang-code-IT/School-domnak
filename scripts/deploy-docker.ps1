# Build frontend + start School Domnak Docker stack (Windows)
# If "running scripts is disabled", use:  scripts\deploy-docker.cmd
# Or:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy-docker.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== 1/3 Build frontend (Docker) ===" -ForegroundColor Cyan
if (Test-Path "Frontend\dist") {
    Remove-Item -Recurse -Force "Frontend\dist"
}
New-Item -ItemType Directory -Path "Frontend\dist" | Out-Null
docker build -f Frontend/Dockerfile --output type=local,dest=Frontend/dist Frontend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path "Frontend\dist\index.html")) {
    Write-Error "Frontend build failed: Frontend\dist\index.html missing"
}

Write-Host "=== 2/3 Preflight ===" -ForegroundColor Cyan
& "$PSScriptRoot\preflight-docker.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 3/3 docker compose up ===" -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Ready:" -ForegroundColor Green
Write-Host "  App:    http://localhost:18080"
Write-Host "  WiFi:   http://192.168.18.28:18080  (use your ipconfig IPv4 if different)"
Write-Host "  API:    http://localhost:18000/docs"
Write-Host ""
Write-Host "First login (after seed): admin@gmail.com / admin12!@$"
Write-Host "Seed DB:     docker compose exec backend python scripts/seed_data.py"
Write-Host "Reset DB:    docker compose exec backend python scripts/reset_database.py"
Write-Host "Logs:    docker compose logs -f backend"
