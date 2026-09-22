"""Dump of channel and group messages to ``data/raw/`` (gitignored).

Read-only: iterates message history, never sends, reacts or replies.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


async def dump_chat(
    client,
    chat_id: int,
    out_dir: Path,
    since: datetime | None = None,
    limit: int | None = None,
) -> Path:
    """Download the message history of one channel or group.

    Each message is written as one JSON line with: message id, date,
    sender id, sender type (user/channel/anonymous admin), text,
    reply_to, forward info, views, and media type (no media download).

    Args:
        client: Connected ``telethon.TelegramClient``.
        chat_id: Channel or group id.
        out_dir: Destination directory (under ``data/raw/``).
        since: Only fetch messages newer than this date.
        limit: Optional cap on the number of messages.

    Returns:
        Path of the written ``.jsonl`` file.
    """
    raise NotImplementedError


async def fetch_admins(client, chat_id: int) -> list[dict]:
    """List the admins of a group/channel, where visible to a member.

    Args:
        client: Connected ``telethon.TelegramClient``.
        chat_id: Group or channel id.

    Returns:
        Records with user id, admin title, and whether the user is the creator.
        Empty if the admin list is not accessible.
    """
    raise NotImplementedError


async def dump_all(client, chat_ids: list[int], out_dir: Path) -> None:
    """Run :func:`dump_chat` and :func:`fetch_admins` for every chat, resumably.

    Keeps a checkpoint of the last message id per chat so interrupted runs
    can resume without re-downloading.

    Args:
        client: Connected ``telethon.TelegramClient``.
        chat_ids: Chats to dump.
        out_dir: Destination directory (under ``data/raw/``).
    """
    raise NotImplementedError
