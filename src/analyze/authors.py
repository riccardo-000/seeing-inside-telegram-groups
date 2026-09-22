"""Author roles: admins vs regular users, and who pushes scams.

Operates on pseudonymized data (see :func:`pseudonymize`).
"""

from __future__ import annotations

import pandas as pd


def pseudonymize(df: pd.DataFrame, salt: str, cols: tuple[str, ...] = ("sender_id",)) -> pd.DataFrame:
    """Replace user identifiers with keyed hashes (HMAC-SHA256, truncated).

    Usernames and display names are dropped. The salt is read from
    ``PSEUDONYM_SALT`` and never stored alongside the data.

    Args:
        df: Messages or DMs dataframe.
        salt: Secret key for the HMAC.
        cols: Identifier columns to replace.

    Returns:
        A copy of ``df`` with pseudonymized ids and no direct identifiers.
    """
    raise NotImplementedError


def label_roles(messages: pd.DataFrame, admins: pd.DataFrame) -> pd.DataFrame:
    """Label each message author as ``admin``, ``creator``, ``channel`` or ``user``.

    Args:
        messages: Messages with ``chat_id`` and ``sender_id``.
        admins: Admin records with ``chat_id``, ``user_id``, ``is_creator``.

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
