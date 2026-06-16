@echo off
REM Rebuild frontend + backend and restart the stack (no PowerShell execution policy needed).
setlocal
cd /d "%~dp0.."
set COMPOSE_PROJECT_NAME=schooldomnak

echo === Preflight ===
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0preflight-docker.ps1"
if errorlevel 1 exit /b 1

echo === Build frontend + backend ===
docker compose -p schooldomnak build frontend backend backend_migrate celery_worker celery_beat telegram_bot
if errorlevel 1 exit /b 1

echo === Copy static frontend to nginx volume ===
docker compose -p schooldomnak run --rm frontend
if errorlevel 1 exit /b 1

echo === Restart services ===
docker compose -p schooldomnak up -d --no-build --scale backend=2 --scale celery_worker=2
if errorlevel 1 exit /b 1

echo.
echo Done. App: http://localhost:18080  (hard refresh: Ctrl+F5)
exit /b 0
