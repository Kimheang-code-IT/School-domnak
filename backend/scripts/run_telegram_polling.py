"""Production Telegram worker: poll getUpdates + process queue (school-telegram-bot)."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401
from app.core.config import settings
from app.services.telegram_polling import polling_loop
from app.services.telegram_update_worker import queue_consumer_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


async def _run_both() -> None:
    await asyncio.gather(
        polling_loop(),
        queue_consumer_loop(),
    )


def main() -> None:
    if not settings.telegram_bot_token.strip():
        logging.error("TELEGRAM_BOT_TOKEN is not set — exiting.")
        sys.exit(1)
    if not settings.telegram_use_polling:
        logging.error("TELEGRAM_USE_POLLING=false — this container should not run.")
        sys.exit(1)
    role = (settings.telegram_polling_role or "").strip().lower()
    if role != "dedicated":
        logging.error(
            "TELEGRAM_POLLING_ROLE must be 'dedicated' on this container (got %r).",
            settings.telegram_polling_role,
        )
        sys.exit(1)
    logging.info(
        "Telegram worker: getUpdates → Redis queue → consumer (API + frontend run in parallel)"
    )
    asyncio.run(_run_both())


if __name__ == "__main__":
    main()
