"""Print chat ids from recent messages to your bot (stop the API first if polling is on)."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"


def main() -> None:
    raw = ENV.read_text(encoding="utf-8")
    match = re.search(r"^TELEGRAM_BOT_TOKEN=(.+)$", raw, re.M)
    if not match or not match.group(1).strip():
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in backend/.env first")
    token = match.group(1).strip()
    url = f"https://api.telegram.org/bot{token}/getUpdates?limit=20"
    try:
        data = json.load(urllib.request.urlopen(url, timeout=30))
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            raise SystemExit(
                "409 Conflict: bot is already polling (API running). "
                "Stop uvicorn/docker, then run this script again."
            ) from exc
        raise
    updates = data.get("result") or []
    if not updates:
        print("No messages yet. Open your bot in Telegram, send /start, then run again.")
        return
    seen: set[int] = set()
    for item in updates:
        msg = item.get("message") or item.get("edited_message") or {}
        chat = msg.get("chat") or {}
        cid = chat.get("id")
        if cid is None or cid in seen:
            continue
        seen.add(cid)
        label = chat.get("title") or " ".join(
            p for p in (chat.get("first_name"), chat.get("last_name")) if p
        )
        user = chat.get("username")
        print(f"chat_id={cid}  type={chat.get('type')}  name={label!r}  @{user or '-'}")


if __name__ == "__main__":
    main()
