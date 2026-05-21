# School-domnak — Docker setup checklist

Full command reference: **[docs/DOCKER-COMMANDS.md](../docs/DOCKER-COMMANDS.md)**

Quick list in terminal: `.\scripts\docker-commands.ps1`

---

## One-time

1. Install **Docker Desktop** and keep it running.
2. Copy env: `copy .env.example .env` (edit secrets; never commit `.env`).
3. Create folders: `secrets`, `uploads` (optional: `secrets\service-account-key.json` for Google Sheets).

## Run the app

```powershell
cd "D:\project\School Domnak"
.\scripts\deploy-docker.ps1
```

Or manually (match scale to your `.env`):

```powershell
docker compose up -d --build --scale backend=2 --scale celery_worker=2
```

## URLs

| Where | URL |
|-------|-----|
| This PC | http://localhost:18080 |
| Wi‑Fi / LAN | http://\<your-PC-IP\>:18080 — `.\scripts\open-wifi-access.ps1` |
| API docs | http://localhost:18080/docs |

## Docker — daily commands

```powershell
docker compose ps
docker compose logs -f backend
docker compose down
docker compose up -d --build --scale backend=2 --scale celery_worker=2
```

## Load balancing

In `.env`: `BACKEND_REPLICAS=2`, `CELERY_WORKER_REPLICAS=2`.  
`deploy-docker.ps1` applies scale automatically; Nginx load-balances `/api/`.

## Database (Docker)

| Action | Command |
|--------|---------|
| Reset everything → admin only | `docker compose exec backend python scripts/reset_database.py` |
| Reset with prompt | `.\scripts\reset-database.ps1` |
| Seed / fix admin | `docker compose exec backend python scripts/seed_data.py` |

Login: `admin@gmail.com` / `admin12!@$`

## Google Sheets backup (Docker)

```powershell
.\scripts\verify-google-sheets-backup.ps1
docker compose exec backend python scripts/run_google_sheets_backup.py
```

## Restart after `.env` change

```powershell
docker compose restart backend
docker compose up -d --force-recreate telegram_bot
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Docker not running | Start Docker Desktop |
| Missing `.env` | `copy .env.example .env` |
| Empty app / 404 | `docker compose up -d --build --scale backend=2 --scale celery_worker=2` |
| Phone cannot connect | `.\scripts\open-wifi-access.ps1` (Admin) |
| API CORS on LAN | Add `http://<your-ip>:18080` to `BACKEND_CORS_ORIGINS`, then `docker compose restart backend` |
