# Run before git push - ensure secrets are not committed.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$fail = 0
function Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:fail++ }
function Ok($msg) { Write-Host "[OK]   $msg" -ForegroundColor Green }

Write-Host "=== Pre-push safety check ===" -ForegroundColor Cyan

if (-not (Test-Path ".git")) { Fail "Not a git repository"; exit 1 }

foreach ($secret in @(".env", "backend\.env", "secrets\service-account-key.json")) {
    if (Test-Path $secret) {
        $ignored = git check-ignore -v $secret 2>$null
        if ($ignored) { Ok "$secret is gitignored" } else { Fail "$secret is NOT gitignored - fix .gitignore" }
    }
}

$staged = git diff --cached --name-only 2>$null
if ($staged) {
    foreach ($bad in @(".env", "backend/.env")) {
        if ($staged -match [regex]::Escape($bad)) { Fail "Staged file must not be committed: $bad" }
    }
    foreach ($line in $staged) {
        if ($line -match 'service-account|\.json$' -and $line -match 'secret') { Fail "Staged secret file: $line" }
    }
}

$untrackedEnv = git status --porcelain | Where-Object { $_ -match '\.env$' -and $_ -notmatch '\.env\.example' }
if ($untrackedEnv) {
    Write-Host "[INFO] .env files present locally (should stay untracked):" -ForegroundColor DarkGray
    $untrackedEnv | ForEach-Object { Write-Host "       $_" -ForegroundColor DarkGray }
}

if (-not (Test-Path ".env.example")) { Fail "Missing .env.example" } else { Ok ".env.example present" }
if (-not (Test-Path "docker-compose.yml")) { Fail "Missing docker-compose.yml" } else { Ok "docker-compose.yml present" }
if (-not (Test-Path "docs\DEPLOY-ANY-PC.md")) { Fail "Missing docs\DEPLOY-ANY-PC.md" } else { Ok "Deploy docs present" }

Write-Host ""
if ($fail -gt 0) {
    Write-Host "Fix $fail issue(s) before git push." -ForegroundColor Red
    exit 1
}
Write-Host "Safe to push. On the other PC: git clone, copy .env from .env.example, docker compose up -d --build" -ForegroundColor Green
Write-Host "See docs\GITHUB-PUSH.md" -ForegroundColor DarkGray
exit 0
