"""Author roles: admins vs regular users, and who pushes scams.

Input data is already pseudonymized at ingestion (see ``src/utils/privacy.py``):
``sender`` columns hold pseudonyms, never Telegram ids or usernames.
"""

from __future__ import annotations

import pandas as pd


def label_roles(messages: pd.DataFrame, admins: pd.DataFrame) -> pd.DataFrame:
    """Label each message author as ``admin``, ``creator``, ``channel`` or ``user``.

    Args:
        messages: Messages with ``chat_id`` and ``sender`` (pseudonym).
        admins: Admin records with ``chat_id``, ``user`` (pseudonym), ``is_creator``.

    Returns:
        ``messages`` with an added ``role`` column.
    """
    raise NotImplementedError


def author_stats(messages: pd.DataFrame) -> pd.DataFrame:
    """Per-author activity statistics per chat.

    Args:
        messages: Role-labelled messages.

    Returns:
        One row per (chat, author): message count, active days, number of
        chats the author appears in, share of scam-labelled messages.
    """
    raise NotImplementedError


def dm_senders_vs_roles(dms: pd.DataFrame, messages: pd.DataFrame) -> pd.DataFrame:
    """Cross DM senders with their roles in the monitored chats.

    Answers: do scam DMs come from admins or from regular members?

    Args:
        dms: Logged DMs (pseudonymized).
        messages: Role-labelled messages.

    Returns:
        Contingency table sender role x DM label (scam / not scam), per category.
    """
    raise NotImplementedError
