"""CORS rules for Docker/LAN deploy — any host IP on APP_PUBLIC_PORT without editing .env."""

from __future__ import annotations

from app.core.config import settings


def build_cors_origin_regex() -> str | None:
    """
    Allow browser requests from localhost and private LAN IPs on the public app port.
    Safe for school Wi-Fi deploy; disable with BACKEND_CORS_ALLOW_LAN=false.
    """
    if not settings.cors_allow_lan:
        return None

    port = settings.app_public_port
    # RFC1918 + localhost, HTTP/HTTPS, fixed nginx port
    return (
        rf"^https?://localhost:{port}$|"
        rf"^https?://127\.0\.0\.1:{port}$|"
        rf"^https?://192\.168\.\d{{1,3}}\.\d{{1,3}}:{port}$|"
        rf"^https?://10\.\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}}:{port}$|"
        rf"^https?://172\.(1[6-9]|2\d|3[0-1])\.\d{{1,3}}\.\d{{1,3}}:{port}$"
    )


def build_cors_allow_origins() -> list[str]:
    """Explicit origins from BACKEND_CORS_ORIGINS (optional extras)."""
    explicit = settings.cors_origin_list()
    if explicit:
        return explicit

    port = settings.app_public_port
    return [
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
    ]
