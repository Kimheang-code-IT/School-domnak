# Security checklist

## Production `.env` (required)

| Variable | Requirement |
|----------|-------------|
| `APP_ENV` | `production` |
| `SECRET_KEY` | At least 32 random characters (not `change-me-in-production`) |
| `DATABASE_URL` | PostgreSQL (not SQLite) |
| `TELEGRAM_WEBHOOK_SECRET` | Required when using webhooks (not polling only) |
| `EXPOSE_OPENAPI` | `false` (hides `/docs` and `/openapi.json`) |
| `AUTO_CREATE_TABLES` | `false` (use Alembic migrations) |

## Network

- Postgres and Redis host ports bind to `127.0.0.1` in `docker-compose.yml` (not `0.0.0.0`).
- Put TLS in front of Nginx before exposing on the internet.
- Restrict `BACKEND_CORS_ORIGINS` to your real frontend origins.

## API

- Login rate limiting: `LOGIN_RATE_LIMIT_*` (Redis-backed).
- Telegram `set-webhook` and `/status` require `role-management` **update**.
- Permission-denied audits no longer flush the entire Redis cache.
- Upload images: magic-byte validation (JPEG/PNG/GIF/WebP), 10 MB max.

## Tokens (frontend)

Access and refresh tokens are stored in `localStorage` today. For stronger security, migrate to HttpOnly cookies + CSRF (planned improvement).

## Before `git push`

- Never commit `.env`, `uploads/`, or `secrets/`.
- Run `git status` and review untracked files.

See also [GITHUB-PUSH.md](GITHUB-PUSH.md).

## No CI/CD

This project does not use GitHub Actions or other remote CI. Before deploy, run locally:

```powershell
.\scripts\preflight-docker.ps1
docker compose config
docker compose up -d --build
```
