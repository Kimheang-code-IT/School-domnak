# Show localhost / LAN URLs for Docker Compose (nginx on APP_PUBLIC_PORT, default 80).
$Port = if ($env:APP_PUBLIC_PORT) { $env:APP_PUBLIC_PORT } else { 80 }
if ($Port -eq "80") {
  Write-Host "App: http://localhost"
} else {
  Write-Host "App: http://localhost:$Port"
}
$ErrorActionPreference = "Stop"

function Get-LanIpv4 {
    $prefer = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notmatch '^127\.' -and $_.PrefixOrigin -eq 'Dhcp' -and
            $_.InterfaceAlias -match 'Wi-Fi|WiFi|Ethernet'
        } |
        Select-Object -ExpandProperty IPAddress -Unique
    if ($prefer) { return $prefer }
    return @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notlike '169.254*' } |
        Select-Object -ExpandProperty IPAddress -Unique)
}

if (-not (docker info 2>$null)) {
    Write-Error "Docker is not running. Start Docker Desktop, then: docker compose up -d --build"
}

$nginx = docker ps --filter "name=school-nginx" --format "{{.Names}}" 2>$null
if (-not $nginx) {
    Write-Warning "school-nginx is not running. Run: .\scripts\deploy-docker.ps1"
}

try {
    New-NetFirewallRule -DisplayName "School-domnak $Port" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -ErrorAction Stop | Out-Null
    Write-Host "Firewall: inbound TCP $Port allowed." -ForegroundColor Green
} catch {
    Write-Host "Firewall: run as Administrator if other devices cannot connect." -ForegroundColor Yellow
}

Write-Host "`n=== Open these URLs ===" -ForegroundColor Green
Write-Host "On this PC:     http://localhost:$Port"
foreach ($ip in @(Get-LanIpv4)) {
    Write-Host "On Wi-Fi/LAN:   http://${ip}:$Port"
}
Write-Host "CORS: dynamic LAN enabled (BACKEND_CORS_ALLOW_LAN=true) - any Wi-Fi IP on port $Port works." -ForegroundColor DarkGray
Write-Host "Optional legacy fix: .\scripts\sync-lan-cors.ps1" -ForegroundColor DarkGray
