# Backend scripts

All commands below assume you are in the **`backend`** folder unless noted.

## Database: send data, update schema, remove rows

| Goal | Command | What it does |
|------|---------|----------------|
| **Insert/update** default admin user & Admin role | `python scripts/db_manage.py seed` | Upserts `admin@gmail.com` (see `seed_data.py`). Safe to run many times. |
| **Remove all app data** from tables, then recreate admin | `python scripts/db_manage.py reset` | Deletes rows in all business tables (order respects foreign keys), then runs `seed`. **Irreversible.** |
| **Update database schema** (tables/columns) | `python scripts/db_manage.py migrate` | Runs `alembic upgrade head`. Also runs automatically when the API container starts (`RUN_DB_MIGRATIONS=true`). |

### Docker Compose

```powershell
docker compose exec backend python scripts/db_manage.py seed
docker compose exec backend python scripts/db_manage.py reset
docker compose exec backend python scripts/db_manage.py migrate
```

### Change admin email/password

Edit constants at the top of `seed_data.py`, then run **seed** (or **reset** if you also want empty tables).

---

## Other scripts

| Script | Purpose |
|--------|---------|
| `get_telegram_chat_id.py` | Help discover `TELEGRAM_CHAT_ID` using bot token from `backend/.env` |
| `migrate_sqlite_to_postgres.py` | One-off migration from SQLite to PostgreSQL |
| `run_telegram_polling.py` | Standalone Telegram long-polling (if API is not running) |
| `run_google_sheets_backup.py` | Manual Google Sheets backup run |

---

## Direct usage (without `db_manage.py`)

- `python scripts/seed_data.py` — same as `db_manage.py seed`
- `python scripts/reset_database.py` — same as `db_manage.py reset`

`reset_database.py` truncates, in dependency order:

`refresh_tokens` → invoice lines/invoices → enrollments → commissions → finance → audit_logs → students → classes → levels → courses → categories → users → roles  

Alembic’s `alembic_version` table is **not** cleared.
