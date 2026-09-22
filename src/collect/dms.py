"""Logging of unsolicited direct messages (DMs) received by the research account.

The account never replies, never clicks links and never opens attachments.
We only record metadata and text for counting and classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class DMRecord:
    """One incoming DM.

    Attributes:
        received_at: Timestamp of the message.
        sender_id: Telegram user id (pseudonymized before analysis).
        sender_username: @username if public, else None.
        text: Message text (URLs kept as-is but never visited).
        shared_chat_ids: Monitored chats in which the sender is also a member.
        sender_is_admin_in: Subset of ``shared_chat_ids`` where the sender is admin.
    """

    received_at: datetime
    sender_id: int
    sender_username: str | None
    text: str
    shared_chat_ids: list[int]
    sender_is_admin_in: list[int]


def register_dm_logger(client, out_path: Path, admin_index: dict[int, set[int]]) -> None:
    """Attach a ``NewMessage(incoming=True, func=is_private)`` handler that logs DMs.

    Args:
        client: Connected ``telethon.TelegramClient``.
        out_path: JSONL file under ``data/raw/`` where records are appended.
        admin_index: Map chat_id -> set of admin user ids, built from
            :func:`src.collect.messages.fetch_admins`.
    """
    raise NotImplementedError


async def backfill_dms(client, out_path: Path, admin_index: dict[int, set[int]]) -> int:
    """Log DMs already present in the inbox (received before the logger started).

    Args:
        client: Connected ``telethon.TelegramClient``.
        out_path: JSONL output file.
        admin_index: Map chat_id -> set of admin user ids.

    Returns:
        Number of DM records written.
    """
    raise NotImplementedError


def is_sender_admin(sender_id: int, admin_index: dict[int, set[int]]) -> list[int]:
    """Return the monitored chats in which ``sender_id`` is an admin.

    Args:
        sender_id: Telegram user id of the DM sender.
        admin_index: Map chat_id -> set of admin user ids.

    Returns:
        Chat ids where the sender is admin (empty list if none).
    """
    raise NotImplementedError
