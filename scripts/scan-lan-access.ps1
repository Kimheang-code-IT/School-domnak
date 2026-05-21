# Security + speed + LAN/Wi-Fi access scan for School Domnak (Docker Compose).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$Port = 18080

function Get-WifiLanIpv4 {
    @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notlike '169.254*' -and
            $_.InterfaceAlias -match 'Wi-Fi|WiFi'
        } |
        Select-Object -ExpandProperty IPAddress -Unique)
}

function Test-TcpPortOpen([string]$HostName, [int]$PortNum) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($HostName, $PortNum, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(2000, $false)
        if ($ok) { $client.EndConnect($iar); $client.Close(); return $true }
        $client.Close()
        return $false
    } catch { return $false }
}

Write-Host "`n=== School Domnak — LAN & production scan ===" -ForegroundColor Cyan

# --- Docker ---
if (-not (docker info 2>$null)) {
    Write-Host "[FAIL] Docker is not running." -ForegroundColor Red
    exit 1
}
$nginx = docker ps --filter "name=school-nginx" --format "{{.Names}}" 2>$null
if (-not $nginx) {
    Write-Host "[FAIL] school-nginx is not running. Run: .\scripts\deploy-docker.ps1" -ForegroundColor Red
} else {
    Write-Host "[OK]   Nginx container running (port $Port on all interfaces)" -ForegroundColor Green
}

# --- Health ---
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/health" -TimeoutSec 5
    Write-Host "[OK]   Health: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Health check: $_" -ForegroundColor Red
}

# --- Docs hidden (production) ---
try {
    $docs = Invoke-WebRequest -Uri "http://127.0.0.1:${Port}/docs" -UseBasicParsing -TimeoutSec 5
    Write-Host "[WARN] /docs returned $($docs.StatusCode) — set EXPOSE_OPENAPI=false and rebuild backend" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 404) {
        Write-Host "[OK]   /docs hidden (404)" -ForegroundColor Green
    } else {
        Write-Host "[WARN] /docs check: $_" -ForegroundColor Yellow
    }
}

# --- LAN IPs ---
$wifiIps = Get-WifiLanIpv4
Write-Host "`n--- Wi-Fi / LAN URLs (other PCs/tablets on same network) ---" -ForegroundColor Cyan
Write-Host "This PC:  http://localhost:$Port"
foreach ($ip in $wifiIps) {
    $url = "http://${ip}:$Port"
    $reachable = Test-TcpPortOpen "127.0.0.1" $Port
    Write-Host "LAN:      $url"
}

# --- CORS vs .env ---
$corsLine = ""
if (Test-Path ".env") {
    $corsLine = (Get-Content ".env" -Raw) -split "`n" | Where-Object { $_ -match '^BACKEND_CORS_ORIGINS=' } | Select-Object -First 1
}
Write-Host "`n--- CORS (browser API from LAN) ---" -ForegroundColor Cyan
if ($corsLine) {
    Write-Host $corsLine
    foreach ($ip in $wifiIps) {
        $need = "http://${ip}:$Port"
        if ($corsLine -notmatch [regex]::Escape($need)) {
            Write-Host "[FAIL] Missing in CORS: $need" -ForegroundColor Red
            Write-Host "       Run: .\scripts\open-wifi-access.ps1  (updates .env + firewall)" -ForegroundColor Yellow
        } else {
            Write-Host "[OK]   CORS includes $need" -ForegroundColor Green
        }
    }
} else {
    Write-Host "[WARN] No BACKEND_CORS_ORIGINS in .env" -ForegroundColor Yellow
}

# --- Security (quick) ---
Write-Host "`n--- Security (from .env, no secrets printed) ---" -ForegroundColor Cyan
$envMap = @{}
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') { $envMap[$matches[1].Trim()] = $matches[2].Trim() }
    }
}
$checks = @(
    @{ Name = "APP_ENV=production"; Ok = $envMap.APP_ENV -eq "production" },
    @{ Name = "SECRET_KEY set (not default)"; Ok = $envMap.SECRET_KEY -and $envMap.SECRET_KEY -notmatch 'change-me' -and $envMap.SECRET_KEY.Length -ge 32 },
    @{ Name = "EXPOSE_OPENAPI=false"; Ok = $envMap.EXPOSE_OPENAPI -eq "false" },
    @{ Name = "AUTO_CREATE_TABLES=false"; Ok = $envMap.AUTO_CREATE_TABLES -eq "false" },
    @{ Name = "LOGIN_RATE_LIMIT_ENABLED"; Ok = $envMap.LOGIN_RATE_LIMIT_ENABLED -eq "true" },
    @{ Name = "REDIS_CACHE_ENABLED"; Ok = $envMap.REDIS_CACHE_ENABLED -eq "true" },
    @{ Name = "Postgres not exposed on LAN"; Ok = (docker ps --format "{{.Ports}}" --filter "name=school-postgres" 2>$null) -match "127.0.0.1" },
    @{ Name = "Redis not exposed on LAN"; Ok = (docker ps --format "{{.Ports}}" --filter "name=school-redis" 2>$null) -match "127.0.0.1" }
)
foreach ($c in $checks) {
    if ($c.Ok) { Write-Host "[OK]   $($c.Name)" -ForegroundColor Green }
    else { Write-Host "[WARN] $($c.Name)" -ForegroundColor Yellow }
}
if ($envMap.POSTGRES_PASSWORD -eq "postgres") {
    Write-Host "[WARN] POSTGRES_PASSWORD is still default 'postgres' — change for production" -ForegroundColor Yellow
}

Write-Host "`n--- Other devices ---`n1. Same Wi-Fi as this PC`n2. Open http://<LAN-IP>:$Port in Chrome/Edge`n3. Login with your school account`n4. If API errors in browser console (CORS): run .\scripts\open-wifi-access.ps1 then docker compose restart backend`n" -ForegroundColor DarkGray
