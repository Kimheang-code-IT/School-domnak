import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
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
    yield
    await stop_telegram_polling()
    if not settings.celery_beat_handles_schedules:
        stop_backup_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok"}
