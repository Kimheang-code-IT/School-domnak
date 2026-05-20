# One-time helper: install GitHub Actions self-hosted runner for School-domnak.
# Run in PowerShell from an empty folder (e.g. D:\actions-runner-schooldomnak).

param(
    [string]$RunnerDir = "D:\actions-runner-schooldomnak",
    [string]$RepoUrl = "https://github.com/Kimheang-code-IT/School-domnak"
)

$ErrorActionPreference = "Stop"

Write-Host "=== School-domnak self-hosted runner setup ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open in browser:" -ForegroundColor Yellow
Write-Host "   $RepoUrl/settings/actions/runners/new?arch=x64&os=win"
Write-Host ""
Write-Host "2. Copy the CONFIGURE token command from GitHub (not the download URL only)."
Write-Host ""
Write-Host "3. This script will create folder: $RunnerDir"
Write-Host ""

if (-not (Test-Path $RunnerDir)) {
    New-Item -ItemType Directory -Path $RunnerDir | Out-Null
}

Set-Location $RunnerDir

if (-not (Test-Path ".\config.cmd")) {
    Write-Host "Download runner package from GitHub page above, extract into:" -ForegroundColor Yellow
    Write-Host "   $RunnerDir"
    Write-Host ""
    Write-Host "Then run GitHub's config.cmd line, for example:"
    Write-Host '   .\config.cmd --url https://github.com/Kimheang-code-IT/School-domnak --token YOUR_TOKEN'
    Write-Host ""
    Write-Host "4. Install as Windows service (optional, recommended):"
    Write-Host "   .\svc install"
    Write-Host "   .\svc start"
    Write-Host ""
    Write-Host "5. Or run interactively (keep window open):"
    Write-Host "   .\run.cmd"
    exit 0
}

Write-Host "Runner files found. Start with:" -ForegroundColor Green
Write-Host "   cd $RunnerDir"
Write-Host "   .\run.cmd"
Write-Host "   # or: .\svc start"
