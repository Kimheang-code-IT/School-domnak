# Redis API cache (cache-aside)

## Flow

```
Frontend → Backend API → Redis (check)
                ↓ miss
            PostgreSQL → save to Redis → response
```

1. Backend builds a cache key from **resource** + **page/sort/search/filters/date range**.
2. If Redis has JSON → return immediately (fast).
3. If miss → query DB, store result with TTL, return.

## What is cached

| Resource | Endpoint | TTL (default) |
|----------|----------|----------------|
| Students | `GET /students` | 120s |
| Classes | `GET /classes` | 120s |
| Courses, categories, levels | list endpoints | 120s |
| Reports | `GET /reports/sales-lines` | 120s |
| Commissions, finance | list endpoints | 120s |
| Users, roles | list endpoints | 120s |
| Audit logs | `GET /audit-logs` | 120s |
| Student/class enrollments | nested list endpoints | 120s |
| Dashboard cards | `GET /dashboard/summary` | 60s |
| Session profile | `GET /auth/me` | 300s |

**Not cached:** login, writes, exports, invoice preview. Checkout clears caches in a Celery background job (see below).

## Checkout speed

`POST /invoices/checkout` saves order + invoice in one DB commit and returns `invoiceNo` + `jobId` immediately. Celery task `checkout.post_process` warms print preview cache, sends Telegram, and clears list/dashboard Redis caches.

Poll `GET /invoices/checkout-jobs/{jobId}` until `printReady` is true before printing.

## Invalidation

After any database **create / update / delete**, list and dashboard caches are cleared automatically. `/auth/me` cache is cleared too so permissions stay correct.

## Environment (root `.env`)

```env
REDIS_CACHE_ENABLED=true
REDIS_CACHE_URL=redis://redis:6379/2
REDIS_CACHE_TTL_LIST=120
REDIS_CACHE_TTL_DASHBOARD=60
REDIS_CACHE_TTL_AUTH_ME=300
```

Set `REDIS_CACHE_ENABLED=false` to disable (always hits DB).

## Health

`GET /health` includes `redis_cache: ok` when cache is enabled and Redis responds.

## Docker

Uses the same Redis container as Celery; **database index 2** avoids clashing with broker (0) and result backend (1).

After changing `.env`, restart backend replicas:

```powershell
docker compose restart backend
```
