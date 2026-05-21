from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="School Management API", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="sqlite:///./school.db",
        validation_alias="DATABASE_URL",
    )
    secret_key: str = Field(default="change-me-in-production", validation_alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    expose_openapi: bool = Field(default=True, validation_alias="EXPOSE_OPENAPI")
    auto_create_tables: bool = Field(default=True, validation_alias="AUTO_CREATE_TABLES")
    login_rate_limit_enabled: bool = Field(default=True, validation_alias="LOGIN_RATE_LIMIT_ENABLED")
    login_rate_limit_max_attempts: int = Field(default=15, validation_alias="LOGIN_RATE_LIMIT_MAX_ATTEMPTS")
    login_rate_limit_window_seconds: int = Field(default=900, validation_alias="LOGIN_RATE_LIMIT_WINDOW_SECONDS")
    refresh_token_expire_days: int = 30
    # Comma-separated extra origins (optional). LAN IPs are handled by regex when cors_allow_lan=true.
    backend_cors_origins: str = Field(
        default="",
        validation_alias="BACKEND_CORS_ORIGINS",
    )
    cors_allow_lan: bool = Field(default=True, validation_alias="BACKEND_CORS_ALLOW_LAN")
    app_public_port: int = Field(default=18080, validation_alias="APP_PUBLIC_PORT")
    upload_dir: Path = Field(default=Path("uploads"), validation_alias="UPLOAD_DIR")

    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    # API response cache (use Redis DB 2+ so Celery broker/result stay on 0/1)
    redis_cache_enabled: bool = Field(default=True, validation_alias="REDIS_CACHE_ENABLED")
    redis_cache_url: str = Field(
        default="redis://localhost:6379/2",
        validation_alias="REDIS_CACHE_URL",
    )
    redis_cache_ttl_list: int = Field(default=120, validation_alias="REDIS_CACHE_TTL_LIST")
    redis_cache_ttl_dashboard: int = Field(default=60, validation_alias="REDIS_CACHE_TTL_DASHBOARD")
    redis_cache_ttl_auth_me: int = Field(default=300, validation_alias="REDIS_CACHE_TTL_AUTH_ME")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        validation_alias="CELERY_RESULT_BACKEND",
    )
    use_celery_tasks: bool = Field(default=True, validation_alias="USE_CELERY_TASKS")
    celery_beat_handles_schedules: bool = Field(
        default=False,
        validation_alias="CELERY_BEAT_HANDLES_SCHEDULES",
    )

    # Google Sheets full-database backup
    google_sheets_backup_enabled: bool = Field(
        default=False,
        validation_alias="GOOGLE_SHEETS_BACKUP_ENABLED",
    )
    google_sheets_credentials_file: Path = Field(
        default=Path("credentials/google-sheets-service-account.json"),
        validation_alias=AliasChoices(
            "GOOGLE_SHEETS_CREDENTIALS_FILE",
            "GOOGLE_SERVICE_ACCOUNT_FILE",
        ),
    )
    google_sheets_spreadsheet_id: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_SHEETS_SPREADSHEET_ID", "GOOGLE_SPREADSHEET_ID"),
    )
    backup_schedule_hour: int = Field(default=19, validation_alias="BACKUP_SCHEDULE_HOUR")
    backup_schedule_minute: int = Field(default=0, validation_alias="BACKUP_SCHEDULE_MINUTE")
    backup_timezone: str = Field(default="Asia/Phnom_Penh", validation_alias="BACKUP_TIMEZONE")

    # Telegram bot
    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", validation_alias="TELEGRAM_CHAT_ID")
    telegram_webhook_secret: str = Field(default="", validation_alias="TELEGRAM_WEBHOOK_SECRET")
    telegram_use_polling: bool = Field(default=True, validation_alias="TELEGRAM_USE_POLLING")
    telegram_polling_in_api: bool = Field(default=False, validation_alias="TELEGRAM_POLLING_IN_API")
    # dedicated = only school-telegram-bot container | disabled = API/celery | empty = use TELEGRAM_POLLING_IN_API
    telegram_polling_role: str = Field(default="", validation_alias="TELEGRAM_POLLING_ROLE")
    telegram_activity_alerts_enabled: bool = Field(
        default=True,
        validation_alias="TELEGRAM_ACTIVITY_ALERTS_ENABLED",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def should_run_telegram_polling(self) -> bool:
        """True only for the single process that may call getUpdates."""
        if not self.telegram_bot_token.strip() or not self.telegram_use_polling:
            return False
        role = (self.telegram_polling_role or "").strip().lower()
        if role == "dedicated":
            return True
        if role == "disabled":
            return False
        return self.telegram_polling_in_api

    def telegram_polling_enabled_in_api(self) -> bool:
        """Backward-compatible alias."""
        return self.should_run_telegram_polling()

    def cors_origin_list(self) -> list[str]:
        raw = self.backend_cors_origins.strip()
        if not raw:
            return []
        if raw.startswith("["):
            import json

            parsed = json.loads(raw)
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [part.strip() for part in raw.split(",") if part.strip()]

    @field_validator("upload_dir", "google_sheets_credentials_file", mode="before")
    @classmethod
    def parse_path(cls, value: Any) -> Path:
        return Path(value) if not isinstance(value, Path) else value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def should_expose_openapi(self) -> bool:
        if self.is_production and not self.expose_openapi:
            return False
        return self.expose_openapi and (self.app_debug or not self.is_production)

    @property
    def should_auto_create_tables(self) -> bool:
        if self.is_production:
            return self.auto_create_tables and self.app_debug
        return self.auto_create_tables


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    from app.core.startup_validation import validate_settings

    validate_settings(s)
    return s


settings = get_settings()
