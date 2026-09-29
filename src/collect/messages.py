"""Dump of channel and group messages to ``data/raw/messages/``.

Read-only: iterates message history, never sends, reacts or replies, never joins.
One gzipped JSONL file per chat (``<username>.jsonl.gz``), messages in
ascending id order. Resumable and deduplicated by (chat_id, message_id): a
rerun only fetches messages newer than the last one on disk and appends them
as a new gzip member (still a valid .gz file).

Records go through ``privacy.sanitize_message``: with ``PSEUDONYM_SALT`` set,
user ids are pseudonymized and text redacted; without it, raw (privacy
deferred, team decision 2026-09-22).
"""

from __future__ import annotations

import asyncio
import gzip
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon import errors
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantsAdmins

from src.utils.links import message_urls, tme_paths
from src.utils.privacy import Pseudonymizer, sanitize_message


def last_id_on_disk(path: Path) -> int:
    """Highest message id already saved (0 if none). Tolerates a truncated tail."""
    if not path.exists():
        return 0
    last, good = 0, []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    last = max(last, json.loads(line)["id"])
                    good.append(line)
                except (json.JSONDecodeError, KeyError):
                    continue
    except (EOFError, OSError):
        # interrupted while writing the last member: rewrite the readable part,
        # otherwise members appended later would be unreadable
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.writelines(line if line.endswith("\n") else line + "\n" for line in good)
    return last


async def dump_chat(
    client,
    chat,
    out_dir: Path,
    since: datetime | None = None,
    limit: int | None = None,
    pseudonymizer: Pseudonymizer | None = None,
    known_chats: set[str] | None = None,
    wait_time: float = 6.0,
) -> tuple[Path, int]:
    """Download (or continue downloading) the history of one channel or group.

    Args:
        client: Connected ``telethon.TelegramClient``.
        chat: Entity or input entity of the channel/group (must have a username).
        out_dir: Destination directory (under ``data/raw/``).
        since: Only fetch messages newer than this date (first run only).
        limit: Optional cap on the number of new messages.
        pseudonymizer: If given, pseudonymize senders and redact text.
        known_chats: Public chat usernames kept in redacted text.
        wait_time: Seconds between history requests (100 messages each).

    Returns:
        (path of the file, number of new messages written).
    """
    name = getattr(chat, "username", None) or str(chat.id)
    path = out_dir / f"{name}.jsonl.gz"
    out_dir.mkdir(parents=True, exist_ok=True)
    min_id = last_id_on_disk(path)
    kwargs = {"reverse": True, "limit": limit, "wait_time": wait_time}
    if min_id:
        kwargs["min_id"] = min_id
    elif since:
        kwargs["offset_date"] = since
    n = 0
    fh = None
    try:
        async for m in client.iter_messages(chat, **kwargs):
            if fh is None:
                fh = gzip.open(path, "at", encoding="utf-8")
            rec = sanitize_message(m, pseudonymizer, known_chats)
            urls = message_urls(m)
            rec["urls"] = urls
            rec["tme"] = tme_paths(urls)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    finally:
        if fh is not None:
            fh.close()
    return path, n


async def fetch_admins(client, chat, pseudonymizer: Pseudonymizer | None = None) -> list[dict]:
    """List the admins of a group/channel, where visible without being admin.

    Returns:
        Records with admin id (pseudonym if a pseudonymizer is given), admin
        title and whether the user is the creator. Empty if not accessible.
    """
    try:
        admins = await client.get_participants(chat, filter=ChannelParticipantsAdmins())
    except (errors.ChatAdminRequiredError, errors.ChannelPrivateError, errors.RPCError):
        return []
    out = []
    for u in admins:
        p = getattr(u, "participant", None)
        out.append({
            "user": pseudonymizer.user(u.id) if pseudonymizer else u.id,
            "is_bot": bool(u.bot),
            "title": getattr(p, "rank", None),
            "is_creator": isinstance(p, ChannelParticipantCreator),
        })
    return out


async def dump_all(client, chats: list, out_dir: Path, days: int = 90,
                   pseudonymizer: Pseudonymizer | None = None, pause: float = 6.0) -> dict:
    """Run :func:`dump_chat` and :func:`fetch_admins` for every chat, resumably.

    Stops at the first FloodWait longer than 60 s (caller must log it).

    Returns:
        ``{chat_name: new_messages}``.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    known = {c.username.lower() for c in chats if getattr(c, "username", None)}
    done = {}
    for chat in chats:
        name = getattr(chat, "username", None) or str(chat.id)
        try:
            path, n = await dump_chat(client, chat, out_dir, since=since,
                                      pseudonymizer=pseudonymizer, known_chats=known, wait_time=pause)
            await asyncio.sleep(pause)
            admins_path = out_dir / f"{name}.admins.json"
            if not admins_path.exists():
                admins = await fetch_admins(client, chat, pseudonymizer)
                admins_path.write_text(json.dumps(admins, indent=1))
                await asyncio.sleep(pause)
        except errors.FloodWaitError as e:
            if e.seconds > 60:
                raise
            await asyncio.sleep(e.seconds + 5)
            continue
        done[name] = n
        print(f"  @{name}: +{n} messages", flush=True)
    return done
