# Optional: add this PC's LAN URLs to BACKEND_CORS_ORIGINS (not required if BACKEND_CORS_ALLOW_LAN=true).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"
$Port = 18080

if (-not (Test-Path $envFile)) {
    Write-Error "Missing .env - copy .env.example to .env first."
}

function Get-LanIpv4 {
    @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notlike '169.254*' -and
            $_.InterfaceAlias -match 'Wi-Fi|WiFi|Ethernet' -and
            $_.InterfaceAlias -notmatch 'vEthernet|VMware|Virtual|WSL|Hyper-V'
        } |
        Select-Object -ExpandProperty IPAddress -Unique)
}

$origins = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($base in @("http://localhost:$Port", "http://127.0.0.1:$Port")) {
    [void]$origins.Add($base)
}
foreach ($ip in Get-LanIpv4) {
    [void]$origins.Add("http://${ip}:$Port")
}

$corsLine = "BACKEND_CORS_ORIGINS=$($origins -join ',')"
$content = Get-Content $envFile -Raw
if ($content -match '(?m)^BACKEND_CORS_ORIGINS=.*$') {
    $content = [regex]::Replace($content, '(?m)^BACKEND_CORS_ORIGINS=.*$', $corsLine)
} else {
    $content = $content.TrimEnd() + "`n$corsLine`n"
}
Set-Content -Path $envFile -Value $content.TrimEnd() -NoNewline
Add-Content -Path $envFile -Value ""

Write-Host "Updated BACKEND_CORS_ORIGINS:" -ForegroundColor Green
$origins | Sort-Object | ForEach-Object { Write-Host "  $_" }
Write-Host "`nRestart API: docker compose restart backend" -ForegroundColor DarkGray
