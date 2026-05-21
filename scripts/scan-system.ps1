# Security, speed, LAN access, and production readiness scan (local Docker).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$Port = 18080
$fail = 0
$warn = 0

function Write-Ok($msg) { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow; $script:warn++ }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:fail++ }

Write-Host "=== School Domnak system scan ===" -ForegroundColor Cyan
Write-Host ""

# --- Docker ---
if (docker info 2>$null) {
    Write-Ok "Docker is running"
} else {
    Write-Fail "Docker is not running"
}

$nginx = docker ps --filter "name=school-nginx" --format "{{.Names}}" 2>$null
if ($nginx) { Write-Ok "school-nginx is up" } else { Write-Fail "school-nginx is not running" }

$backendHealthy = docker ps --filter "name=backend" --filter "health=healthy" --format "{{.Names}}" 2>$null
if ($backendHealthy) { Write-Ok "Backend replica(s) healthy: $($backendHealthy -join ', ')" } else { Write-Warn "No healthy backend container" }

# --- Health & cache ---
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/health" -TimeoutSec 8
    if ($health.status -eq "ok") { Write-Ok "HTTP /health -> ok" } else { Write-Warn "/health status: $($health.status)" }
    if ($health.redis_cache -eq "ok") { Write-Ok "Redis API cache ping ok" } elseif ($health.redis_cache) { Write-Warn "Redis cache: $($health.redis_cache)" } else { Write-Warn "Redis cache not reported (disabled?)" }
} catch {
    Write-Fail "Cannot reach http://127.0.0.1:${Port}/health - $_"
}

try {
    $docs = Invoke-WebRequest -Uri "http://127.0.0.1:${Port}/docs" -UseBasicParsing -TimeoutSec 5
    Write-Warn "/docs returned $($docs.StatusCode) - set EXPOSE_OPENAPI=false and rebuild if production"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 404) { Write-Ok "/docs hidden (404)" } else { Write-Warn "/docs check: $_" }
}

# --- LAN / Wi-Fi ---
function Get-LanIpv4 {
    @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notlike '169.254*' -and
            $_.InterfaceAlias -match 'Wi-Fi|WiFi|Ethernet' -and
            $_.InterfaceAlias -notmatch 'vEthernet|VMware|Virtual|WSL|Hyper-V'
        } |
        Select-Object InterfaceAlias, IPAddress)
}

Write-Host ""
Write-Host "--- LAN access (other computers on same Wi-Fi) ---" -ForegroundColor Cyan
$lan = Get-LanIpv4
if ($lan.Count -eq 0) {
    Write-Warn "No Wi-Fi/Ethernet LAN IP detected"
} else {
    foreach ($row in $lan) {
        Write-Host "  $($row.InterfaceAlias): http://$($row.IPAddress):${Port}" -ForegroundColor White
    }
}

$dockerPorts = docker port school-nginx 80 2>$null
if ($dockerPorts -match '0\.0\.0\.0') {
    Write-Ok "Nginx port $Port is bound to all interfaces (0.0.0.0) - LAN can connect if firewall allows"
} else {
    Write-Warn "Check nginx port binding: $dockerPorts"
}

# CORS mode
if (Test-Path ".env") {
    $envText = Get-Content ".env" -Raw
    if ($envText -match 'BACKEND_CORS_ALLOW_LAN=false') {
        Write-Warn "BACKEND_CORS_ALLOW_LAN=false - you must set each LAN IP in BACKEND_CORS_ORIGINS"
        $cors = (Select-String -Path ".env" -Pattern '^BACKEND_CORS_ORIGINS=(.+)$').Matches.Groups[1].Value
        foreach ($row in $lan) {
            if ($cors -notlike "*$($row.IPAddress)*") {
                Write-Warn "Missing in CORS: http://$($row.IPAddress):$Port"
            }
        }
    } else {
        Write-Ok "Dynamic LAN CORS enabled (any private IP on port $Port)"
    }
}
try {
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/health" -TimeoutSec 5
    if ($h.cors_lan_dynamic -eq $true) { Write-Ok "API reports cors_lan_dynamic=true" }
} catch { }

# --- .env production ---
Write-Host ""
Write-Host "--- Production .env ---" -ForegroundColor Cyan
if (Test-Path ".env") {
    $envText = Get-Content ".env" -Raw
    if ($envText -match 'APP_ENV=production') { Write-Ok "APP_ENV=production" } else { Write-Warn "APP_ENV is not production" }
    if ($envText -match 'EXPOSE_OPENAPI=false') { Write-Ok "EXPOSE_OPENAPI=false" } else { Write-Warn "EXPOSE_OPENAPI not false" }
    if ($envText -match 'AUTO_CREATE_TABLES=false') { Write-Ok "AUTO_CREATE_TABLES=false" } else { Write-Warn "AUTO_CREATE_TABLES not false" }
    if ($envText -match 'SECRET_KEY=change-me') { Write-Fail "SECRET_KEY still default placeholder" }
    elseif ($envText -match 'SECRET_KEY=.{32,}') { Write-Ok "SECRET_KEY length looks ok" } else { Write-Warn "SECRET_KEY may be too short" }
    if ($envText -match 'POSTGRES_PASSWORD=postgres') { Write-Warn "POSTGRES_PASSWORD is still postgres - change for real production" }
    if ($envText -match 'LOGIN_RATE_LIMIT_ENABLED=true') { Write-Ok "Login rate limit enabled" } else { Write-Warn "LOGIN_RATE_LIMIT_ENABLED not true" }
    if ($envText -match 'REDIS_CACHE_ENABLED=true') { Write-Ok "Redis list cache enabled" } else { Write-Warn "REDIS_CACHE_ENABLED not true" }
} else {
    Write-Fail "No .env file"
}

# Postgres/Redis not on LAN
$pg = docker port school-postgres 5432 2>$null
$rd = docker port school-redis 6379 2>$null
if ($pg -match '127\.0\.0\.1') { Write-Ok "Postgres only on localhost ($pg)" } elseif ($pg) { Write-Warn "Postgres exposed: $pg" }
if ($rd -match '127\.0\.0\.1') { Write-Ok "Redis only on localhost ($rd)" } elseif ($rd) { Write-Warn "Redis exposed: $rd" }

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Failures: $fail  Warnings: $warn"
if ($fail -gt 0) {
    Write-Host "Fix failures before sharing on Wi-Fi." -ForegroundColor Red
    exit 1
}
if ($warn -gt 0) {
    Write-Host "LAN tip: .\scripts\open-wifi-access.ps1  (firewall + URLs)" -ForegroundColor Yellow
    Write-Host "CORS tip: .\scripts\sync-lan-cors.ps1 ; docker compose restart backend" -ForegroundColor Yellow
}
exit 0
