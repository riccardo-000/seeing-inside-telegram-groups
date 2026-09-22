"""Tone analysis and scam classification of messages and DMs."""

from __future__ import annotations

import pandas as pd

# Label set, to be finalized and logged in memory/decisions.md.
SCAM_LABELS = (
    "investment_scam",   # guaranteed returns, pump & dump, "signals"
    "impersonation",     # fake admin / support
    "carding_fraud",     # stolen cards, fullz, cashout services
    "phishing",          # wallet drainers, fake airdrops, credential links
    "not_scam",
)


def extract_features(texts: pd.Series) -> pd.DataFrame:
    """Compute lightweight lexical features per message.

    E.g. URL/domain count, wallet-address patterns, @mentions, urgency and
    "DM me" cues, emoji density, language.

    Args:
        texts: Message texts.

    Returns:
        Feature dataframe aligned with ``texts``.
    """
    raise NotImplementedError


def classify_scam(texts: pd.Series, method: str = "rules") -> pd.Series:
    """Assign one of :data:`SCAM_LABELS` to each message.

    Args:
        texts: Message texts.
        method: ``"rules"`` (keyword/regex baseline) or a model-based method
            to be decided.

    Returns:
        Series of labels aligned with ``texts``.
    """
    raise NotImplementedError


def tone_scores(texts: pd.Series) -> pd.DataFrame:
    """Score tone per message (e.g. sentiment, aggressiveness, urgency).

    Args:
        texts: Message texts.

    Returns:
        Dataframe with one column per tone dimension.
    """
    raise NotImplementedError


def compare_channel_vs_group(messages: pd.DataFrame) -> pd.DataFrame:
    """Compare tone and scam prevalence between channels and their linked groups.

    Args:
        messages: Labelled messages with ``chat_type`` (channel/group) and ``category``.

    Returns:
        Summary table by category x chat_type.
    """
    raise NotImplementedError
