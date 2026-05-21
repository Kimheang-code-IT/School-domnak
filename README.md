# School-domnak

School management system with a **Nuxt** frontend, **FastAPI** backend, **PostgreSQL**, **Redis**, **Celery**, **Telegram bot**, and **Nginx**.

**Repository:** https://github.com/Kimheang-code-IT/School-domnak.git

Deployment is **Docker Compose only** (local build). There is no Kubernetes or GitHub Actions CI/CD in this repo.

---

## Quick start

### 1. Prerequisites

- **Docker Desktop** (running)
- Project folder, e.g. `D:\project\School Domnak`

### 2. Environment

```powershell
copy .env.example .env
# Edit .env — never commit it
mkdir secrets, uploads -Force
```

### 3. Start everything

```powershell
.\scripts\deploy-docker.ps1
```

Or:

```powershell
docker compose up -d --build
```

(`deploy-docker.ps1` runs preflight, then Compose builds the Nuxt static site into a Docker volume for Nginx.)

### 4. Open the app

| Where | URL |
|-------|-----|
| This PC | http://localhost:18080 |
| Wi‑Fi / LAN | http://\<your-PC-IP\>:18080 |
| API (Swagger) | http://localhost:18080/docs |

For LAN access and firewall help:

```powershell
.\scripts\open-wifi-access.ps1
```

If the browser blocks API calls from another device, add your LAN URL to `BACKEND_CORS_ORIGINS` in `.env`, then:

```powershell
docker compose restart backend
```

---

## Services (Compose)

| Service | Port (host) | Notes |
|---------|-------------|--------|
| nginx | 18080, 18443 | Public app entry |
| backend | (internal) | FastAPI — scaled replicas; use Nginx on 18080 |
| postgres | 15432 | Optional external access |
| redis | 16379 | Optional external access |

Stack: `postgres`, `redis`, `backend_migrate`, `backend` (replicas), `celery_worker` (replicas), `celery_beat`, `telegram_bot`, `frontend` (build helper), `nginx`.

---

## Load balancing (multiple users at once)

**Nginx** is the load balancer. It distributes `/api/`, `/docs`, and `/health` across every running `backend` container using `least_conn` (sends each new request to the replica with the fewest active connections).

Set in `.env` (defaults shown in `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKEND_REPLICAS` | 2 | API containers behind Nginx |
| `UVICORN_WORKERS` | 2 | Uvicorn worker processes **per** API container |
| `CELERY_WORKER_REPLICAS` | 2 | Background job workers |
| `CELERY_WORKER_CONCURRENCY` | 4 | Celery processes **per** worker container |

Deploy with scaling (reads `.env` automatically):

```powershell
.\scripts\deploy-docker.ps1
```

Or manually:

```powershell
docker compose up -d --build --scale backend=3 --scale celery_worker=2
```

Auth uses **JWT** (stateless), and uploads live on a **shared volume**, so replicas do not need sticky sessions. Keep **one** `telegram_bot` and **one** `celery_beat` (do not scale those).

---

## Nginx routing

| Path | Target |
|------|--------|
| `/` | Frontend (Nuxt SPA) |
| `/api/` | Backend (`/api/v1/`) |
| `/uploads/` | Backend (media/files) |
| `/_nuxt/` | Frontend static assets |
| `/admin/` | Frontend SPA routes |
| `/docs`, `/health` | Backend |

---

## Common commands

```powershell
docker compose ps
docker compose logs -f backend
docker compose exec backend python scripts/seed_data.py
docker compose exec backend python scripts/reset_database.py
# Or interactive: .\scripts\reset-database.ps1
docker compose down
docker compose up -d --build
```

First login after seed (default): `admin@gmail.com` / `admin12!@$`

---

## Project layout

```
backend/          FastAPI app
Frontend/         Nuxt app (folder name is capital F)
nginx/conf.d/     Nginx config
docker-compose.yml
scripts/
  deploy-docker.ps1
  preflight-docker.ps1
  open-wifi-access.ps1
  SETUP-CHECKLIST.md
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Docker not running | Start Docker Desktop |
| Missing `.env` | `copy .env.example .env` |
| Nginx shows 404 / empty page | `docker compose up -d --build` (re-runs the `frontend` copy step) |
| Port 18080 in use | `docker compose down` or stop the other process |
| Phone cannot connect | `.\scripts\open-wifi-access.ps1` (Admin for firewall) |
| Two Telegram 409 errors | Only one `telegram_bot` container should run |
| Backend DB errors | Check `DATABASE_URL` uses host `postgres` in `.env` for Compose |

---

## Security

- `.env` is gitignored — never commit secrets.
- Keep `secrets/` local only (e.g. Google service account JSON).

See `scripts/SETUP-CHECKLIST.md` for a short step-by-step list.

---

## Google Sheets backup

Exports **every database table** and **every column** into one spreadsheet tab per table (plus `_backup_meta`). The only column excluded is `users.password_hash` (security).

| Table | Typical columns |
|-------|-----------------|
| `users` | id, email, name, role_id, … (not password_hash) |
| `roles`, `students`, `categories`, `courses`, `levels`, `classes` | full row |
| `enrollments`, `commissions`, `finance`, `invoices`, `invoice_lines` | full row |
| `audit_logs`, `refresh_tokens` | full row |
| `alembic_version` | migration version |

Verify coverage (no Google API call):

```powershell
.\scripts\verify-google-sheets-backup.ps1
```

Run backup now:

```powershell
docker compose exec backend python scripts/run_google_sheets_backup.py
```

Requires `GOOGLE_SHEETS_BACKUP_ENABLED=true`, service account JSON in `secrets/`, and spreadsheet shared with the service account email.

Push to GitHub safely: `docs/GITHUB-PUSH.md`.
