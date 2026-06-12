import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import settings
from app.services.telegram_bot_service import process_telegram_update, set_webhook

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_webhook_secret(secret_header: str | None) -> None:
    expected = settings.telegram_webhook_secret.strip()
    if not expected:
        return
    if secret_header != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    """Receive Telegram updates (production with HTTPS webhook)."""
    if not settings.telegram_bot_token.strip():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram bot not configured")
    _verify_webhook_secret(x_telegram_bot_api_secret_token)
    update = await request.json()
    try:
        await process_telegram_update(update)
    except Exception:
        logger.exception("Telegram webhook handler error")
    return {"ok": True}


@router.post("/set-webhook")
async def register_webhook(public_url: str) -> dict[str, str]:
    """
    Register webhook URL (admin utility).
    Example public_url: https://your-domain.com/api/v1/telegram/webhook
    """
    if not settings.telegram_bot_token.strip():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram bot not configured")
    await set_webhook(public_url.rstrip("/"))
    return {"ok": "true", "url": public_url}
