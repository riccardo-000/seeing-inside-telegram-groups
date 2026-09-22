"""Seed selection and joining of channels / public groups.

Scope: ~100 crypto channels and ~100 conspiracy/malicious channels. Sources
(see ``memory/decisions.md``): TGDataset as the labelled starting point, plus
newer sources (still-active channels' recent messages, TeraGram, keyword
search). Groups are found as linked discussion groups AND as public invite
links / t.me links posted in recent channel messages. Only PUBLIC chats are
joined. Joining is the only "action" taken; no messages are sent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

Category = Literal["crypto", "conspiracy"]


@dataclass
class SeedChannel:
    """A seed channel.

    Attributes:
        channel_id: Telegram channel id.
        username: Public @username, if any (required to join passively).
        category: Seed category ("crypto" or "conspiracy").
        source: Where the seed came from ("tgdataset", "teragram", "search", "forward").
        linked_group_id: Id of the linked discussion group, filled after resolution.
    """

    channel_id: int
    username: str | None
    category: Category
    source: str = "tgdataset"
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


async def discover_groups_from_messages(client, seed: SeedChannel, since_days: int = 180) -> list[str]:
    """Extract public group links (``t.me/<name>``, public invite links) from recent posts.

    Only links that resolve to PUBLIC groups are returned; private invite
    links (``t.me/+...`` / ``joinchat``) are recorded as counts only, never joined.

    Args:
        client: Connected ``telethon.TelegramClient``.
        seed: Channel whose recent messages are scanned.
        since_days: How far back to scan.

    Returns:
        Public group usernames/links found in the channel.
    """
    raise NotImplementedError


def search_public_chats(client, keywords: list[str]) -> list[dict]:
    """Find newer public channels/groups by keyword via Telegram's public search.

    Complements TGDataset (collected up to July 2022) with currently active chats.

    Args:
        client: Connected ``telethon.TelegramClient``.
        keywords: Search terms (e.g. "airdrop", "signals", "cvv"), logged in decisions.md.

    Returns:
        Candidate chats with id, username, type, member count, and matching keyword.
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
