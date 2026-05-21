# Deploy on any computer (dynamic IP)

The app is built to run on **different PCs** without editing IP addresses in `.env`.

## How it works

| Piece | Behavior |
|-------|----------|
| **Frontend** | Uses relative `/api` — always talks to the same host you opened in the browser |
| **Nginx** | Listens on port **18080** on all interfaces (`0.0.0.0`) |
| **Backend CORS** | `BACKEND_CORS_ALLOW_LAN=true` allows **any private LAN IP** on `APP_PUBLIC_PORT` (192.168.x.x, 10.x.x.x, 172.16–31.x.x, localhost) |

When you move the project to another computer, only the **host IP** changes — CORS updates automatically.

## Deploy on a new PC

1. Copy the whole project folder (include `.env`, `secrets/`, `uploads/` if needed).
2. Install Docker Desktop.
3. From project root:

```powershell
docker compose up -d --build
# or
.\scripts\deploy-docker.ps1
```

4. Open firewall (Administrator):

```powershell
.\scripts\open-wifi-access.ps1
```

5. Show URLs for **this** machine:

```powershell
.\scripts\show-lan-urls.ps1
```

6. On phones/laptops (same Wi-Fi), open the **Wi-Fi URL** printed (e.g. `http://192.168.18.48:18080`).

No need to run `sync-lan-cors.ps1` unless `BACKEND_CORS_ALLOW_LAN=false`.

## `.env` settings (recommended)

```env
BACKEND_CORS_ALLOW_LAN=true
APP_PUBLIC_PORT=18080
BACKEND_CORS_ORIGINS=
```

`BACKEND_CORS_ORIGINS` is only for **extra** fixed URLs (e.g. a domain name).

## Verify

```powershell
.\scripts\scan-system.ps1
```

`GET /health` should include `"cors_lan_dynamic": true`.

## Internet / public internet

This setup is for **school Wi-Fi / LAN**. Do not expose port 18080 to the public internet without TLS and a firewall. For internet access, use a reverse proxy with HTTPS and set `BACKEND_CORS_ORIGINS` to your real domain.
