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

Or (set scale to match `BACKEND_REPLICAS` / `CELERY_WORKER_REPLICAS` in `.env`):

```powershell
docker compose up -d --build --scale backend=2 --scale celery_worker=2
```

(`deploy-docker.ps1` runs preflight, builds the frontend into a Docker volume, and scales API workers from `.env`.)

All Docker commands: **[docs/DOCKER-COMMANDS.md](docs/DOCKER-COMMANDS.md)** — or run `.\scripts\docker-commands.ps1` for a quick list.

### 4. Open the app

| Where | URL |
|-------|-----|
| This PC | http://localhost:18080 |
| Wi‑Fi / LAN | http://\<your-PC-IP\>:18080 |
| Health | http://localhost:18080/health |

For LAN / Wi-Fi (other computers on same network):

```powershell
.\scripts\show-lan-urls.ps1
.\scripts\open-wifi-access.ps1
```

CORS accepts **any private LAN IP** when `BACKEND_CORS_ALLOW_LAN=true` (default) — no manual IP list when you move to another PC.

---

## Clone on another computer

```powershell
git clone https://github.com/Kimheang-code-IT/School-domnak.git
cd School-domnak
copy .env.example .env
# Edit .env (secrets only - see docs/GITHUB-PUSH.md)
.\scripts\deploy-docker.ps1
```

Full steps: **[docs/GITHUB-PUSH.md](docs/GITHUB-PUSH.md)** and **[docs/DEPLOY-ANY-PC.md](docs/DEPLOY-ANY-PC.md)**.

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

## Docker commands (quick reference)

| Task | Command |
|------|---------|
| Deploy / start | `.\scripts\deploy-docker.ps1` |
| Stop | `docker compose down` |
| Status | `docker compose ps` |
| Logs | `docker compose logs -f backend` |
| Reset DB (admin only) | `docker compose exec backend python scripts/reset_database.py` |
| Seed admin | `docker compose exec backend python scripts/seed_data.py` |
| Google Sheets backup | `docker compose exec backend python scripts/run_google_sheets_backup.py` |
| Rebuild & restart | `docker compose up -d --build --scale backend=2 --scale celery_worker=2` |

First login: `admin@gmail.com` / `admin12!@$`

Full list: [docs/DOCKER-COMMANDS.md](docs/DOCKER-COMMANDS.md)

---

## Project layout

```
backend/          FastAPI app
Frontend/         Nuxt app (folder name is capital F)
nginx/conf.d/     Nginx config
docker-compose.yml
scripts/
  deploy-docker.ps1
  reset-database.ps1
  docker-commands.ps1
  preflight-docker.ps1
  open-wifi-access.ps1
  SETUP-CHECKLIST.md
docs/
  DOCKER-COMMANDS.md
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

Before push: `.\scripts\pre-push-check.ps1` — then [docs/GITHUB-PUSH.md](docs/GITHUB-PUSH.md).

---

## Redis cache (faster lists & dashboard)

List pages, filters, search, dashboard summary, and `/auth/me` use **Redis cache-aside** (see [docs/REDIS-CACHE.md](docs/REDIS-CACHE.md)).

Enable in `.env`: `REDIS_CACHE_ENABLED=true`, `REDIS_CACHE_URL=redis://redis:6379/2`.

---

## Security & operations

- Production checklist: [docs/SECURITY.md](docs/SECURITY.md)
- Docker commands: [docs/DOCKER-COMMANDS.md](docs/DOCKER-COMMANDS.md)
- Local checks before deploy: `.\scripts\preflight-docker.ps1` (no GitHub Actions CI/CD in this repo)
- Deploy on another PC / dynamic Wi-Fi IP: [docs/DEPLOY-ANY-PC.md](docs/DEPLOY-ANY-PC.md)
