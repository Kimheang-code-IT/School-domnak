@echo off
REM Runs deploy-docker.ps1 without changing system ExecutionPolicy (Restricted-safe).
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy-docker.ps1" %*
exit /b %ERRORLEVEL%
