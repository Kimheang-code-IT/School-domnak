"""Standalone Telegram polling (if API server is not running)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401
from app.services.telegram_polling import polling_loop


def main() -> None:
    asyncio.run(polling_loop())


if __name__ == "__main__":
    main()
