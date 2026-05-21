# Git push and clone on another computer

## Before you push (this PC)

```powershell
cd "D:\project\School Domnak"
.\scripts\pre-push-check.ps1
git status
```

Confirm **`.env` does NOT** appear under "Changes to be committed".

### Never commit

| Path | Why |
|------|-----|
| `.env` | Passwords, Telegram token, SECRET_KEY |
| `backend/.env` | Same |
| `secrets/*.json` | Google service account key |
| `uploads/*` | Student images and files |
| `*.db` | Local database |

### Safe to commit

- All source code, `docker-compose.yml`, `nginx/`, `scripts/`, `docs/`
- `.env.example` (placeholders only)
- `secrets/.gitkeep`, `uploads/.gitkeep` (empty folders)

### Push commands

```powershell
git add -A
git status
# Review the list - no .env, no secrets/*.json

git commit -m "Docker deploy, Redis cache, dynamic LAN CORS, security hardening"

git push origin main
```

Use your branch name if not `main` (e.g. `git push origin master`).

---

## On another computer (clone and run Docker)

### 1. Prerequisites

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)

### 2. Clone

```powershell
git clone https://github.com/Kimheang-code-IT/School-domnak.git
cd School-domnak
```

### 3. Environment (required)

```powershell
copy .env.example .env
notepad .env
```

Set at minimum:

| Variable | What to set |
|----------|-------------|
| `SECRET_KEY` | Random 64-char hex: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_PASSWORD` | Strong password (match in `DATABASE_URL`) |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:YOUR_PASSWORD@postgres:5432/school_db` |
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) (optional) |
| `TELEGRAM_CHAT_ID` | Your numeric chat ID (optional) |

Leave these for LAN deploy on any IP:

```env
BACKEND_CORS_ALLOW_LAN=true
APP_PUBLIC_PORT=18080
BACKEND_CORS_ORIGINS=
```

### 4. Optional folders

```powershell
mkdir secrets, uploads -Force
# Google backup only:
# copy your-key.json secrets\service-account-key.json
```

### 5. Build and start

```powershell
.\scripts\preflight-docker.ps1
.\scripts\deploy-docker.ps1
```

Or:

```powershell
docker compose up -d --build --scale backend=2 --scale celery_worker=2
```

### 6. Open the app

```powershell
.\scripts\show-lan-urls.ps1
.\scripts\open-wifi-access.ps1
```

| Device | URL |
|--------|-----|
| This PC | http://localhost:18080 |
| Other devices (same Wi-Fi) | http://YOUR_LAN_IP:18080 |

### 7. First-time database

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_data.py
```

Default admin (after seed): see `scripts/deploy-docker.ps1` output.

### 8. Verify

```powershell
.\scripts\scan-system.ps1
```

Health: http://localhost:18080/health should show `"status":"ok"`.

---

## More docs

- [DEPLOY-ANY-PC.md](DEPLOY-ANY-PC.md) - dynamic IP / move between PCs
- [DOCKER-COMMANDS.md](DOCKER-COMMANDS.md) - daily Docker commands
- [SECURITY.md](SECURITY.md) - production checklist
- [LAN-ACCESS.md](LAN-ACCESS.md) - Wi-Fi access

## If a secret was ever committed

1. Remove from Git history or rotate the secret immediately.
2. Regenerate Telegram bot token in BotFather if the token was exposed.
3. Change `SECRET_KEY` and `POSTGRES_PASSWORD` on all deployments.
