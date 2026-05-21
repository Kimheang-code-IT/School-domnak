# Wi-Fi / LAN access (other computers)

Other PCs, phones, or tablets on the **same Wi-Fi** can use the app if:

1. Docker is running and Nginx is up on port **18080**
2. Windows Firewall allows inbound TCP **18080**
3. **`BACKEND_CORS_ALLOW_LAN=true`** (default) — API accepts any private LAN IP on port 18080

## Quick setup

```powershell
.\scripts\open-wifi-access.ps1
```

This will:

- Allow firewall port 18080 (run PowerShell as Administrator if it fails)
- Print URLs to open on other devices

CORS is **automatic** — you do not need to edit IPs in `.env` when the Wi-Fi address changes.

## URLs

| Device | URL |
|--------|-----|
| This PC | http://localhost:18080 |
| Other device on Wi-Fi | http://YOUR_LAN_IP:18080 |

Find `YOUR_LAN_IP`: Wi-Fi settings, or run `.\scripts\scan-system.ps1`.

**Important:** If your Wi-Fi IP changes (DHCP), only the URL changes — CORS still works. Run `.\scripts\show-lan-urls.ps1` to see the new address.

## What is NOT exposed on LAN

- PostgreSQL (`127.0.0.1:15432` only)
- Redis (`127.0.0.1:16379` only)
- Backend port 8000 (internal Docker network only)

Only Nginx **18080** is public on the LAN.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Page loads but login/API fails | Check `BACKEND_CORS_ALLOW_LAN=true` in `.env`, restart backend |
| Cannot open page at all | Run `open-wifi-access.ps1` as Administrator |
| Wrong IP in browser | Use IP from `scan-system.ps1`, not an old one |

## Full scan

```powershell
.\scripts\scan-system.ps1
```

Checks health, Redis cache, CORS, production `.env`, and LAN binding.
