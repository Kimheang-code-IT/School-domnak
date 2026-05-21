# Wipe all application data; keep only Admin role + admin user (DESTRUCTIVE).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (docker info 2>$null)) {
    Write-Error "Docker is not running. Start Docker Desktop first."
}

Write-Host "=== Reset database (all students, classes, invoices, etc. removed) ===" -ForegroundColor Yellow
Write-Host "Keeps: Admin role + admin@gmail.com" -ForegroundColor Cyan
$confirm = Read-Host "Type YES to continue"
if ($confirm -ne "YES") {
    Write-Host "Cancelled."
    exit 0
}

docker compose exec -T backend python scripts/reset_database.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Done. Login: admin@gmail.com / admin12!@$" -ForegroundColor Green
Write-Host "Optional: refresh Google Sheet backup:" -ForegroundColor DarkGray
Write-Host "  docker compose exec backend python scripts/run_google_sheets_backup.py"
