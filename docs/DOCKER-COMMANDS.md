# Docker commands

Quick reference for **School Domnak** (Docker Compose + Nginx).

## Start / stop

```powershell
# Recommended: rebuild images + start (reads BACKEND_REPLICAS from .env)
.\scripts\deploy-docker.ps1

# After pulling or editing frontend/backend code only
.\scripts\docker-update.ps1

# Manual (use project name so DB volume and container names stay consistent)
$env:COMPOSE_PROJECT_NAME = "schooldomnak"
docker compose up -d --build --scale backend=2 --scale celery_worker=2

docker compose -p schooldomnak down
docker compose -p schooldomnak ps
```

## Logs

```powershell
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs -f nginx
```

## Database

```powershell
docker compose exec backend python scripts/db_manage.py migrate
docker compose exec postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB
.\scripts\reset-database.ps1
```

## Health

- App: http://127.0.0.1:18080/health
- Redis cache field in JSON when `REDIS_CACHE_ENABLED=true`

## Scale

Set in `.env`:

```env
BACKEND_REPLICAS=2
CELERY_WORKER_REPLICAS=2
```

Then: `.\scripts\deploy-docker.ps1` or `docker compose up -d --scale backend=2 --scale celery_worker=2`

## See also

- [README.md](../README.md)
- [REDIS-CACHE.md](REDIS-CACHE.md)
- [SECURITY.md](SECURITY.md)
- `scripts/docker-commands.ps1` (shortcuts)
