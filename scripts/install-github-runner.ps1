# Install GitHub Actions self-hosted runner on Windows (PowerShell).
# Run from any folder. Does NOT configure the runner (you need a fresh token from GitHub).

param(
    [string]$InstallDir = "D:\actions-runner-schooldomnak",
    [string]$RunnerVersion = "2.334.0"
)

$ErrorActionPreference = "Stop"

$zipName = "actions-runner-win-x64-$RunnerVersion.zip"
$zipPath = Join-Path $InstallDir $zipName
$downloadUrl = "https://github.com/actions/runner/releases/download/v$RunnerVersion/$zipName"
$expectedHash = "a0c896f3acf37841cc17f392a38111d39501e56f2990434567f027ee89cf8981"

Write-Host "=== GitHub Actions runner installer (Windows) ===" -ForegroundColor Cyan
Write-Host "Install folder: $InstallDir"
Write-Host ""

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
    Write-Host "Created folder: $InstallDir" -ForegroundColor Green
}

Set-Location $InstallDir

if (-not (Test-Path ".\config.cmd")) {
    Write-Host "Downloading runner $RunnerVersion ..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing

    $hash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToUpper()
    if ($hash -ne $expectedHash.ToUpper()) {
        throw "ZIP checksum mismatch. Delete $zipPath and retry."
    }
    Write-Host "Checksum OK. Extracting ..." -ForegroundColor Green

    Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "Runner already extracted (config.cmd found)." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== NEXT STEPS (do these manually) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open in browser (get a NEW one-time token):"
Write-Host "   https://github.com/Kimheang-code-IT/School-domnak/settings/actions/runners/new?arch=x64&os=win"
Write-Host ""
Write-Host "2. Copy ONLY the config.cmd line from GitHub (without leading `$)."
Write-Host "   It looks like:"
Write-Host '   .\config.cmd --url https://github.com/Kimheang-code-IT/School-domnak --token PASTE_TOKEN_HERE'
Write-Host ""
Write-Host "3. Run in PowerShell:"
Write-Host "   cd $InstallDir"
Write-Host '   .\config.cmd --url https://github.com/Kimheang-code-IT/School-domnak --token YOUR_NEW_TOKEN'
Write-Host ""
Write-Host "4. Start runner (pick one):"
Write-Host "   .\run.cmd"
Write-Host "   # OR install as Windows service:"
Write-Host "   .\svc install"
Write-Host "   .\svc start"
Write-Host ""
Write-Host "5. Verify on GitHub: Settings -> Actions -> Runners -> should show Idle (green)"
Write-Host ""
