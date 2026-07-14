"""CORS rules for Docker/LAN deploy — any host IP on APP_PUBLIC_PORT without editing .env."""

from __future__ import annotations

from app.core.config import settings


def build_cors_origin_regex() -> str | None:
    """
    Allow browser requests from localhost and private LAN IPs on the public app port.
    Safe for school Wi-Fi deploy; disable with BACKEND_CORS_ALLOW_LAN=false.
    Port 80/443 omit the explicit port in browser Origin headers.
    """
    if not settings.cors_allow_lan:
        return None

    port = settings.app_public_port
    if port in (80, 443):
        # Browsers send http://localhost (no :80) for default ports
        return (
            r"^https?://localhost/?$|"
            r"^https?://127\.0\.0\.1/?$|"
            r"^https?://192\.168\.\d{1,3}\.\d{1,3}/?$|"
            r"^https?://10\.\d{1,3}\.\d{1,3}\.\d{1,3}/?$|"
            r"^https?://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}/?$"
        )

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
    if port in (80, 443):
        return [
            "http://localhost",
            "http://127.0.0.1",
        ]
    return [
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
    ]
