import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.cors_policy import build_cors_allow_origins, build_cors_origin_regex
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.core.redis_cache import cache_enabled, ping as redis_cache_ping
from app.core.database import Base, engine
from app.services.backup_scheduler import start_backup_scheduler, stop_backup_scheduler
from app.services.telegram_polling import start_telegram_polling, stop_telegram_polling
import app.models  # noqa: F401 - register SQLAlchemy models

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not settings.celery_beat_handles_schedules:
        start_backup_scheduler()
    else:
        logging.getLogger(__name__).info(
            "APScheduler backup disabled (CELERY_BEAT_HANDLES_SCHEDULES=true)."
        )
    if settings.should_run_telegram_polling():
        start_telegram_polling()
    else:
        logging.getLogger(__name__).info(
            "Telegram long-polling disabled in API "
            "(production: use school-telegram-bot with TELEGRAM_POLLING_ROLE=dedicated)."
        )
    if cache_enabled():
        ok = redis_cache_ping()
        logging.getLogger(__name__).info(
            "Redis API cache enabled (url=%s, ping=%s, list_ttl=%ss)",
            settings.redis_cache_url,
            ok,
            settings.redis_cache_ttl_list,
        )
    log = logging.getLogger(__name__)
    if settings.cors_allow_lan:
        log.info(
            "CORS: dynamic LAN enabled for private IPs on port %s (BACKEND_CORS_ALLOW_LAN=true)",
            settings.app_public_port,
        )
    else:
        log.info("CORS: explicit origins only — %s", settings.cors_origin_list())
    yield
    await stop_telegram_polling()
    if not settings.celery_beat_handles_schedules:
        stop_backup_scheduler()


_openapi_url = "/openapi.json" if settings.should_expose_openapi else None
_docs_url = "/docs" if settings.should_expose_openapi else None

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=None,
    openapi_url=_openapi_url,
)

app.add_middleware(SecurityHeadersMiddleware)
_cors_regex = build_cors_origin_regex()
app.add_middleware(
    CORSMiddleware,
    allow_origins=build_cors_allow_origins(),
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

if settings.should_auto_create_tables:
    Base.metadata.create_all(bind=engine)
else:
    logging.getLogger(__name__).info("AUTO_CREATE_TABLES disabled — use Alembic migrations.")
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")


@app.get("/health")
def health_check():
    payload: dict = {
        "status": "ok",
        "cors_lan_dynamic": settings.cors_allow_lan,
        "app_public_port": settings.app_public_port,
    }
    if cache_enabled():
        payload["redis_cache"] = "ok" if redis_cache_ping() else "unavailable"
    return payload
