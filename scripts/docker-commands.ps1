# Print common Docker commands (copy-paste reference).
$root = Split-Path -Parent $PSScriptRoot
Write-Host @"

School-domnak — Docker commands (run from: $root)

DEPLOY
  .\scripts\deploy-docker.ps1
  docker compose up -d --build --scale backend=2 --scale celery_worker=2

STOP
  docker compose down
  docker compose down -v          # also deletes DB volume

STATUS / LOGS
  docker compose ps
  docker compose logs -f backend
  docker compose logs -f nginx telegram_bot

DATABASE
  docker compose exec backend python scripts/reset_database.py
  docker compose exec backend python scripts/seed_data.py
  .\scripts\reset-database.ps1    # reset with YES prompt

GOOGLE SHEETS
  .\scripts\verify-google-sheets-backup.ps1
  docker compose exec backend python scripts/run_google_sheets_backup.py

RESTART (after .env edit)
  docker compose restart backend
  docker compose up -d --force-recreate telegram_bot

URLs: http://localhost:18080  |  docs: http://localhost:18080/docs

Full list: docs\DOCKER-COMMANDS.md

"@ -ForegroundColor Cyan
