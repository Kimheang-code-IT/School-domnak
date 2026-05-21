# Push to GitHub — checklist

Use this before `git push` so secrets and local-only files stay off GitHub.

## Never commit

- `.env` (root) — Telegram token, DB passwords, spreadsheet IDs
- `backend/.env` — same
- `secrets/` — Google service account JSON
- `uploads/` — user files
- `*.db` — local SQLite

These are listed in `.gitignore`. Confirm with:

```powershell
git status
git check-ignore -v .env backend/.env
```

## Safe to commit (this migration)

- `docker-compose.yml`, `nginx/`, `scripts/`
- `README.md`, `.env.example` (placeholders only)
- Removal of `deploy/kubernetes/`, old GitHub Actions workflows, `docker-compose.prod.yml`
- `docs/GITHUB-PUSH.md`, backup verify scripts

## Suggested commit & push

```powershell
cd "D:\project\School Domnak"

git add -A
git status
# Review: .env must NOT appear under "Changes to be committed"

git commit -m "$(cat <<'EOF'
Deploy with Docker Compose only and Nginx load balancing.

Remove Kubernetes and GHCR workflows; add scaled backend replicas,
Google Sheets backup verification, and LAN deploy scripts.
EOF
)"

git push origin main
```

## After push (on the server / your PC)

1. Copy `.env.example` → `.env` and set real secrets (do not commit `.env`).
2. Put Google key at `secrets/service-account-key.json`.
3. Set `TELEGRAM_CHAT_ID=8551167485` (and your bot token) in `.env`.
4. Run `.\scripts\deploy-docker.ps1`.
5. Verify backup: `.\scripts\verify-google-sheets-backup.ps1`.
6. Restart Telegram bot after chat ID change: `docker compose up -d --force-recreate telegram_bot`.

## Rotate secrets if exposed

If a bot token or password was ever pasted in chat or committed, regenerate it in [@BotFather](https://t.me/BotFather) and update `.env` only.
