# School Management FastAPI Backend

FastAPI backend for the existing school/course management frontend table UI. All table list endpoints return:

```json
{
  "data": [],
  "total": 0
}
```

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The default development database is SQLite:

```env
DATABASE_URL=sqlite:///./school.db
```

To switch to PostgreSQL later, change only `DATABASE_URL`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/school_db
```

## Seed Data

```powershell
cd backend
.venv\Scripts\activate
python scripts\seed_data.py
```

This creates sample categories, courses, classes, students, users, roles, enrollments, invoices, finance rows, commissions, and audit logs.

Default login seed:

- Email: `admin@example.com`
- Password: `password123`
- Staff: `staff@example.com` / `password123`
- Teacher: `teacher@example.com` / `password123`

## Authentication And Permissions

Login with `POST /api/v1/auth/login`. The response includes `accessToken`, `tokenType`, and `user.permissions`.

JWT payloads contain only the user id in `sub`. Protected endpoints load the latest user role from the database and check the role `permissions` JSON before running the action. Missing or invalid tokens return `401`; missing permissions return `403` with `You do not have permission to perform this action`.

Refresh tokens are persisted in `refresh_tokens` as hashes only. Raw refresh tokens are returned once from login, sent to `POST /api/v1/auth/refresh` for a new access token, and sent to `POST /api/v1/auth/logout` to revoke the stored token.

Auth routes:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Role payloads use page/action permissions:

```json
{
  "name": "Staff",
  "permissions": {
    "students": ["view", "create", "update"],
    "classes": ["view"],
    "reports": ["view"]
  }
}
```

## Alembic

Initial Alembic support is configured in `alembic.ini` and `alembic/env.py`.

```powershell
cd backend
.venv\Scripts\activate
alembic revision --autogenerate -m "init"
alembic upgrade head
```

This repository also includes an initial migration at `alembic/versions/0001_init.py` for the current model metadata.

## API Routes

Main table routes:

- `GET|POST /api/v1/categories`
- `GET|POST /api/v1/courses`
- `GET|POST /api/v1/classes`
- `GET|POST /api/v1/students`
- `GET|POST /api/v1/users`
- `GET|POST /api/v1/roles`

Special routes:

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/classes/{class_id}/enrollments`
- `PATCH /api/v1/classes/{class_id}/enrollments/{enrollment_id}`
- `GET /api/v1/students/{student_id}/enrollments`
- `DELETE /api/v1/students/{student_id}/enrollments/{enrollment_id}`
- `GET /api/v1/invoices/{invoice_id}`
- `POST /api/v1/invoices`
- `GET /api/v1/reports/sales-lines`
- `GET /api/v1/reports/sales-lines/export`
- `GET /api/v1/finance`
- `GET /api/v1/finance/export`
- `PUT /api/v1/finance/{id}`
- `GET /api/v1/commissions`
- `GET /api/v1/commissions/export`
- `GET /api/v1/audit-logs`
- `GET /api/v1/audit-logs/export`

Common table query params: `page`, `limit`, `sortBy`, `sortOrder`, `search`, `dateFrom`, `dateTo`.
Extra filters: `categoryId`, `product`, `action`, `role`.

Sorting is always mapped through per-resource `SORT_MAP` dictionaries in repositories/endpoints; raw client field names are never used directly as SQL columns.

## Google Sheets auto backup (all tables)

The backend can export **every table and every column** from the database into a Google Spreadsheet once per day at **19:00** (configurable timezone, default `Asia/Phnom_Penh`). Each database table becomes its own sheet tab; a `_backup_meta` tab records the last run.

### 1. Google Cloud setup

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Enable **Google Sheets API** and **Google Drive API**.
3. Create a **Service account** → Keys → Add key → JSON.
4. Save the JSON file as:
   `backend/credentials/google-sheets-service-account.json`
   (this path is gitignored).

### 2. Spreadsheet access

1. Create a new Google Spreadsheet (or use an existing one).
2. Copy the spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`
3. Click **Share** and add the service account email (from the JSON, field `client_email`) as **Editor**.

### 3. Environment variables

Add to `backend/.env`:

```env
GOOGLE_SHEETS_BACKUP_ENABLED=true
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials/google-sheets-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-here
BACKUP_SCHEDULE_HOUR=19
BACKUP_SCHEDULE_MINUTE=0
BACKUP_TIMEZONE=Asia/Phnom_Penh
```

Install dependencies:

```powershell
cd backend
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run

- **Automatic:** start the API with `uvicorn app.main:app --reload`. While the server is running, the scheduler triggers backup daily at 19:00.
- **Manual (CLI):** `python scripts/run_google_sheets_backup.py`
- **Manual (API):** `POST /api/v1/backup/google-sheets` (requires `role-management` view permission — Admin).

### 5. Optional: Windows Task Scheduler

If the API is not always running, schedule the CLI instead at 19:00:

```powershell
cd backend
.venv\Scripts\python.exe scripts\run_google_sheets_backup.py
```

Use the same `.env` in `backend/` so credentials and spreadsheet ID load correctly.

## Telegram bot reports

Interactive reports via inline keyboards (students, income, category/course/class/teacher breakdowns, today report, Google Sheets backup).

### Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Get your chat id (message [@userinfobot](https://t.me/userinfobot) or inspect `getUpdates`).
3. Add to `backend/.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=your_numeric_chat_id
TELEGRAM_WEBHOOK_SECRET=optional-random-string
TELEGRAM_USE_POLLING=true
```

`TELEGRAM_CHAT_ID` restricts who can use the bot (comma-separated for multiple ids). Leave empty only for local testing.

### Run (polling — easiest for development)

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Polling starts automatically when `TELEGRAM_USE_POLLING=true` and a token is set.

Open your bot in Telegram → send `/start` → tap report buttons or **☁️ Backup to Google Sheets**.

**Auto backup:** daily at **19:00** `Asia/Phnom_Penh` when `GOOGLE_SHEETS_BACKUP_ENABLED=true` and Celery Beat is running (Docker: `celery_beat` service).

**Student alerts** (checkout / new enrollment) include per-class subtotal/discount/line total and invoice subtotal, discount, and grand total.

**Custom range:** choose `Custom Range`, then send: `2026-05-01 to 2026-05-18`

### Commands

| Command | Action |
|---------|--------|
| `/start` | Main menu |
| `/help` | Help text |
| `/report` | Main menu |
| `/summary` | All-time quick summary |
| `/backup` | Google Sheets backup now |
| `/cancel` | Cancel flow |

### Webhook (production)

Set `TELEGRAM_USE_POLLING=false`, expose HTTPS, then:

```http
POST /api/v1/telegram/set-webhook?public_url=https://your-domain.com/api/v1/telegram/webhook
```

Send header `X-Telegram-Bot-Api-Secret-Token` matching `TELEGRAM_WEBHOOK_SECRET` on each webhook call.
