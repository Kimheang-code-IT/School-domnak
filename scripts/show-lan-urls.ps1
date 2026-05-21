# Print URLs for this machine (copy .env to a new PC and run deploy - CORS is automatic).
$Port = if ($env:APP_PUBLIC_PORT) { $env:APP_PUBLIC_PORT } else { 18080 }
$ErrorActionPreference = "SilentlyContinue"

function Get-LanIpv4 {
    Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notlike '169.254*' -and
            $_.InterfaceAlias -match 'Wi-Fi|WiFi|Ethernet' -and
            $_.InterfaceAlias -notmatch 'vEthernet|VMware|Virtual|WSL|Hyper-V'
        } |
        Select-Object InterfaceAlias, IPAddress
}

Write-Host ""
Write-Host "=== School Domnak URLs (port $Port) ===" -ForegroundColor Cyan
Write-Host "This PC:       http://localhost:$Port"
Write-Host "Other devices (same Wi-Fi):"
$lan = @(Get-LanIpv4)
if (-not $lan -or $lan.Count -eq 0) {
    Write-Host "  (no LAN IP found - connect Wi-Fi or Ethernet)"
} else {
    foreach ($row in $lan) {
        $alias = $row.InterfaceAlias
        $ip = $row.IPAddress
        Write-Host "  ${alias}: http://${ip}:$Port"
    }
}
Write-Host ""
Write-Host "CORS: BACKEND_CORS_ALLOW_LAN=true accepts any private LAN IP on port $Port." -ForegroundColor DarkGray
Write-Host "Deploy on another PC: copy project + .env, run docker compose up -d --build, then run this script again." -ForegroundColor DarkGray
Write-Host ""
