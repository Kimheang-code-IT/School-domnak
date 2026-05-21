# Verify DB export matches all tables/columns before or after a Google Sheets backup.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (docker info 2>$null)) {
    Write-Error "Docker is not running."
}

Write-Host "=== Export coverage (all tables / columns) ===" -ForegroundColor Cyan
docker compose exec -T backend python scripts/verify_google_sheets_backup.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== Optional: run live backup to Google Sheets ===" -ForegroundColor Cyan
Write-Host "  docker compose exec backend python scripts/run_google_sheets_backup.py"
