# School-domnak — Docker setup checklist

## One-time

1. Install **Docker Desktop** and keep it running.
2. Copy env file: `cp .env.example .env` (edit secrets; never commit `.env`).
3. Create folders: `secrets`, `uploads` (optional: `secrets\service-account-key.json` for Google Sheets).

## Run the app

```powershell
cd "D:\project\School Domnak"
.\scripts\deploy-docker.ps1
```

Or manually:

```powershell
docker compose up -d --build
```

## URLs

| Where | URL |
|-------|-----|
| This PC | http://localhost:18080 |
| Wi‑Fi / LAN | http://\<your-PC-IP\>:18080 — run `.\scripts\open-wifi-access.ps1` |
| API docs | http://localhost:18080/docs |

## Load balancing

In `.env`: `BACKEND_REPLICAS=2`, `CELERY_WORKER_REPLICAS=2` (see `.env.example`).  
`deploy-docker.ps1` scales API + Celery workers; Nginx balances traffic across backends.

## Google Sheets backup

- Verify all tables/columns: `.\scripts\verify-google-sheets-backup.ps1`
- Run backup: `docker compose exec backend python scripts/run_google_sheets_backup.py`
- Telegram alerts: set `TELEGRAM_CHAT_ID` in `.env` (e.g. `8551167485`)

## Reset database (admin only)

Removes **all** students, classes, invoices, enrollments, audit logs, etc. Keeps only **Admin** role and **admin@gmail.com** (`admin12!@$`).

```powershell
.\scripts\reset-database.ps1
```

Or without prompt:

```powershell
docker compose exec backend python scripts/reset_database.py
```

## Useful commands

```powershell
docker compose ps
docker compose logs -f backend
docker compose exec backend python scripts/seed_data.py
docker compose down
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Docker not running | Start Docker Desktop |
| Missing `.env` | Copy from `.env.example` |
| Empty app / 404 from Nginx | `docker compose up -d --build` (rebuilds frontend into the Nginx volume) |
| Phone cannot open app | Run `open-wifi-access.ps1` as Administrator (firewall) |
| API CORS on LAN | Add `http://<your-ip>:18080` to `BACKEND_CORS_ORIGINS` in `.env`, then `docker compose restart backend` |
