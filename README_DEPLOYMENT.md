# School Domnak — Production Deployment (Docker)

This guide runs the full stack with **non-conflicting host ports** (safe alongside other Docker projects on the same machine).

## Architecture

```
Browser → http://localhost:18080 (Nginx)
            ├── Vue/Nuxt static (Frontend/dist)
            ├── /api/*     → backend:8000/api/v1/*
            ├── /docs      → FastAPI docs
            └── /uploads/* → shared uploads volume

backend → postgres:5432 (host 15432)
backend → redis:6379 (host 16379)
redis → Celery worker / beat
```

| Service        | Container           | Host port | Internal        |
|----------------|---------------------|-----------|-----------------|
| PostgreSQL     | `school-postgres`   | 15432     | 5432            |
| Redis          | `school-redis`      | 16379     | 6379            |
| FastAPI        | `school-backend`    | 18000     | 8000            |
| Nginx HTTP     | `school-nginx`      | 18080     | 80              |
| Nginx HTTPS    | `school-nginx`      | 18443     | 443             |

**Access**

- Frontend: http://localhost:18080  
- API via Nginx: http://localhost:18080/api/…  
- FastAPI docs (Nginx): http://localhost:18080/docs  
- FastAPI direct: http://localhost:18000/docs  
- PostgreSQL (host tools): `localhost:15432`  
- Redis (host tools): `localhost:16379`  

## Prerequisites

- Docker & Docker Compose v2
- Node 22 + pnpm (to build frontend static files)
- Google service account JSON (optional, for Sheets backup)
- Telegram bot token (optional, for alerts/reports)

## 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

- Set `SECRET_KEY` to a long random string.
- Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` if using Telegram.
- Set `GOOGLE_SPREADSHEET_ID` and place the JSON key at:

  `secrets/service-account-key.json`

  (mounted read-only at `/app/secrets/service-account-key.json` in containers)

**Never commit** `.env`, `secrets/service-account-key.json`, or Telegram tokens.

## 2. Build frontend static assets

The frontend is **Nuxt 4** (Vue). Production API base is `/api` (Nginx proxies to FastAPI `/api/v1`).

**Linux / macOS (bash):**

```bash
cd Frontend
pnpm install
pnpm run generate
mkdir -p dist
cp -r .output/public/. dist/
cd ..
```

**Windows (PowerShell)** — use `;` instead of `&&`:

```powershell
cd Frontend
pnpm install
$env:NUXT_PUBLIC_API_BASE="/api"
$env:NUXT_PUBLIC_USE_BACKEND_API="true"
pnpm run generate
New-Item -ItemType Directory -Force -Path dist | Out-Null
Copy-Item -Path ".output\public\*" -Destination dist -Recurse -Force
cd ..
```

Or use the optional Docker build:

```bash
docker build -f Frontend/Dockerfile -o Frontend/dist Frontend
```

## 3. Start the stack

```bash
docker compose up -d --build
```

Check health:

```bash
docker compose ps
curl http://localhost:18000/health
curl http://localhost:18080/health
```

## 4. Celery schedules

When `CELERY_BEAT_HANDLES_SCHEDULES=true` (default in `.env.example`):

| Job                    | Schedule              | Task                                      |
|------------------------|-----------------------|-------------------------------------------|
| Daily Telegram summary | 20:00 (Asia/Phnom_Penh) | `send_daily_summary_report_task`        |
| Google Sheets backup   | 23:00                 | `backup_all_to_google_sheets_task`        |
| Weekly summary         | Sunday 20:00          | `send_weekly_summary_report_task`         |

APScheduler in the FastAPI process is **disabled** in this mode to avoid duplicate backups.

## 5. Student registration + background jobs

After a successful student create (or new student via invoice checkout):

1. Database commit completes first.
2. `send_student_register_telegram_alert_task` is queued via Celery.
3. If Celery/Redis is unavailable, the API falls back to in-process Telegram alerts.

Telegram/Google Sheets failures **do not** roll back registration.

`password_hash` is **excluded** from Google Sheets exports.

---

## SQLite → PostgreSQL migration

### Step 1: Backup SQLite

```bash
cp backend/school.db backend/school.db.backup-$(date +%Y%m%d)
```

### Step 2: Start PostgreSQL only

```bash
docker compose up -d postgres
```

### Step 3: Update `DATABASE_URL`

In `.env`:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/school_db
```

For host-side tools use port **15432**:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:15432/school_db
```

### Step 4: Run Alembic migrations

```bash
cd backend
# with venv active and DATABASE_URL pointing at Postgres
alembic upgrade head
```

Migrations live in `backend/alembic/versions/`.

### Step 5: If Alembic was never used on this DB

Alembic is already configured (`backend/alembic.ini`, `alembic/env.py` reads `DATABASE_URL` from settings). Run `alembic upgrade head` on an empty Postgres DB before importing data.

### Step 6: Export from SQLite / import to PostgreSQL

```bash
cd backend
export SQLITE_URL=sqlite:///./school.db
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:15432/school_db
python scripts/migrate_sqlite_to_postgres.py
```

Tables are copied in FK-safe order: roles → users → categories → courses → classes → students → enrollments → invoices → invoice_lines → commissions → finance → audit_logs → refresh_tokens.

### Step 7: Verify row counts

Compare counts in SQLite vs PostgreSQL per table (e.g. `SELECT COUNT(*) FROM students`).

### Step 8: Test backend against PostgreSQL

```bash
docker compose up -d backend
curl http://localhost:18000/health
curl http://localhost:18000/api/v1/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"..."}'
```

### Step 9: Run full Docker system

```bash
docker compose up -d --build
```

### Step 10: Smoke test UI

Open http://localhost:18080, log in, create a test student, confirm Telegram alert (if configured).

---

## Security notes

- Do not commit `.env` or service account JSON.
- `password_hash` is never written to Google Sheets.
- Host ports 15432/16379 are for **local development** only; in production, do not publish Postgres/Redis to the public internet.
- Use strong `POSTGRES_PASSWORD` and `SECRET_KEY` in production.
- Mount `secrets/` read-only; never bake JSON keys into images.

## Troubleshooting

| Issue | Check |
|-------|--------|
| 502 on `/api` | `docker logs school-backend` |
| Empty frontend | Rebuild `Frontend/dist` (`pnpm run generate`) |
| Celery not running | `docker logs school-celery-worker` / `school-celery-beat` |
| Sheets backup fails | `GOOGLE_SERVICE_ACCOUNT_FILE`, spreadsheet shared with service account email |
| Pinia/API errors locally | Use `NUXT_PUBLIC_API_BASE=/api` only behind Nginx (port 18080) |

## Useful commands

```bash
docker compose logs -f backend
docker compose exec backend alembic upgrade head
docker compose exec celery_worker celery -A app.core.celery_app.celery_app inspect ping
docker compose down
docker compose down -v   # WARNING: deletes Postgres volume
```
