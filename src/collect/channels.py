"""Seed selection from TGDataset and joining of channels / linked groups.

Scope: ~100 crypto channels and ~100 conspiracy/malicious channels taken
from TGDataset. Only PUBLIC channels and their PUBLIC linked discussion
groups are joined. Joining is the only "action" taken; no messages are sent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

Category = Literal["crypto", "conspiracy"]


@dataclass
class SeedChannel:
    """A channel selected from TGDataset.

    Attributes:
        channel_id: Telegram channel id as reported in TGDataset.
        username: Public @username, if any (required to join passively).
        category: Seed category ("crypto" or "conspiracy").
        linked_group_id: Id of the linked discussion group, filled after resolution.
    """

    channel_id: int
    username: str | None
    category: Category
    linked_group_id: int | None = None


def load_seed_list(tgdataset_path: Path, per_category: int = 100) -> list[SeedChannel]:
    """Select seed channels from a local TGDataset export.

    Args:
        tgdataset_path: Path to the TGDataset files (not committed).
        per_category: Number of channels to sample per category.

    Returns:
        The seed list, balanced across categories. The selection criteria
        (topic labels, min. subscribers, still-active) must be logged in
        ``memory/decisions.md``.
    """
    raise NotImplementedError


async def resolve_linked_group(client, seed: SeedChannel) -> SeedChannel:
    """Resolve the public discussion group linked to a channel, if any.

    Args:
        client: Connected ``telethon.TelegramClient``.
        seed: Channel to inspect (via ``GetFullChannelRequest``).

    Returns:
        The same seed with ``linked_group_id`` set, or unchanged if the
        channel has no public linked group.
    """
    raise NotImplementedError


async def join_channels(client, seeds: Iterable[SeedChannel], delay_s: float = 30.0) -> list[dict]:
    """Join channels and their public linked groups, with rate limiting.

    Must respect ``FloodWaitError`` and never join private/invite-only chats.

    Args:
        client: Connected ``telethon.TelegramClient``.
        seeds: Channels to join.
        delay_s: Minimum pause between join requests.

    Returns:
        One status record per chat (id, type, joined/failed, reason, timestamp).
    """
    raise NotImplementedError
