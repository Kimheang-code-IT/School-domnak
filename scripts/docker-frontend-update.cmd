@echo off
REM Rebuild frontend only and copy static files into the nginx volume (no backend rebuild).
setlocal
cd /d "%~dp0.."
echo === Building frontend image ===
docker compose -p schooldomnak build frontend
if errorlevel 1 exit /b 1
echo === Copying static files to nginx volume ===
docker compose -p schooldomnak run --rm frontend
if errorlevel 1 exit /b 1
echo.
echo Frontend updated. Open http://localhost:18080 and hard-refresh (Ctrl+F5).
exit /b 0
