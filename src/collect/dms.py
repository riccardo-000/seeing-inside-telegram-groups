"""Logging of unsolicited direct messages (DMs) received by the research account.

The account never replies, never clicks links, never opens attachments and
never marks messages as read. We only record metadata and text (pseudonymized
and redacted when ``PSEUDONYM_SALT`` is set) for counting and classification.
Only ONE logger instance may run at a time (DMs arrive per account).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from telethon import events
from telethon.tl.types import User

from src.utils.links import message_urls, tme_paths
from src.utils.privacy import Pseudonymizer, redact_text


def _sender_ref(sender_id: int, pseudonymizer: Pseudonymizer | None):
    return pseudonymizer.user(sender_id) if pseudonymizer else sender_id


def dm_record(message, sender, pseudonymizer: Pseudonymizer | None,
              admin_index: dict[str, set], member_index: dict[str, set]) -> dict:
    """On-disk record for one DM (no name, username or phone of the sender)."""
    ref = _sender_ref(message.sender_id, pseudonymizer)
    urls = message_urls(message)
    text = message.message or ""
    return {
        "received_at": message.date.isoformat(),
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sender": ref,
        "sender_is_bot": bool(getattr(sender, "bot", False)),
        "sender_is_scam": bool(getattr(sender, "scam", False)),
        "sender_is_fake": bool(getattr(sender, "fake", False)),
        "sender_is_premium": bool(getattr(sender, "premium", False)),
        "sender_is_contact": bool(getattr(sender, "contact", False)),
        "text": redact_text(text) if pseudonymizer else text,
        "urls": urls,
        "tme": tme_paths(urls),
        "media": type(message.media).__name__ if message.media else None,
        "sender_is_admin_in": sorted(is_sender_admin(str(ref), admin_index)),
        "sender_seen_in": sorted(c for c, members in member_index.items() if str(ref) in members),
    }


def register_dm_logger(client, out_path: Path, pseudonymizer: Pseudonymizer | None,
                       admin_index: dict[str, set], member_index: dict[str, set]) -> None:
    """Attach a handler that appends every incoming private message to ``out_path``.

    Nothing is ever sent back; messages are not marked as read.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def _log(event):
        sender = await event.get_sender()
        # 777000 = Telegram service account (login codes!): never logged
        if not isinstance(sender, User) or sender.is_self or sender.id == 777000:
            return
        rec = dm_record(event.message, sender, pseudonymizer, admin_index, member_index)
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"DM logged at {rec['received_at']} (scam flag: {rec['sender_is_scam']})", flush=True)


async def backfill_dms(client, out_path: Path, pseudonymizer: Pseudonymizer | None,
                       admin_index: dict[str, set], member_index: dict[str, set]) -> int:
    """Log DMs already in the inbox (received before the logger started), deduplicated."""
    seen = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                seen.add((str(r["sender"]), r["received_at"]))
    n = 0
    async for dialog in client.iter_dialogs():
        if not dialog.is_user or not isinstance(dialog.entity, User):
            continue
        user = dialog.entity
        if user.is_self or user.id == 777000:  # 777000 = Telegram service notifications
            continue
        async for m in client.iter_messages(user, limit=200, wait_time=6):
            if m.out:
                continue
            ref = str(_sender_ref(m.sender_id, pseudonymizer))
            if (ref, m.date.isoformat()) in seen:
                continue
            rec = dm_record(m, user, pseudonymizer, admin_index, member_index)
            with open(out_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def is_sender_admin(sender: str, admin_index: dict[str, set]) -> list[str]:
    """Return the monitored chats in which ``sender`` is an admin."""
    return [chat for chat, admins in admin_index.items() if sender in admins]


def build_indexes(raw_dir: Path) -> tuple[dict[str, set], dict[str, set]]:
    """Admin and member indexes from the message dumps in ``raw_dir``.

    admin_index: chat -> admin ids/pseudonyms (from ``<chat>.admins.json``).
    member_index: chat -> ids/pseudonyms seen writing in that chat.
    """
    import gzip

    admins, members = {}, {}
    for f in raw_dir.glob("*.admins.json"):
        chat = f.name[: -len(".admins.json")]
        admins[chat] = {str(a["user"]) for a in json.loads(f.read_text())}
    for f in raw_dir.glob("*.jsonl.gz"):
        chat = f.name[: -len(".jsonl.gz")]
        s = set()
        try:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for line in fh:
                    r = json.loads(line)
                    if r.get("sender_kind") == "user":
                        s.add(str(r["sender"]))
        except (EOFError, OSError, json.JSONDecodeError):
            pass
        members[chat] = s
    return admins, members
