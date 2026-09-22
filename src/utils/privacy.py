"""Privacy at ingestion: nothing that identifies a person is ever written to disk.

Every collector passes Telethon objects through :func:`sanitize_message` /
:func:`sanitize_user` BEFORE writing to ``data/raw/``. Downstream code only
ever sees pseudonyms. Design and rationale: ``memory/data-protection.md``.

Rules:
- User ids -> keyed pseudonym (HMAC-SHA256 with ``PSEUDONYM_SALT``). Same id
  always maps to the same pseudonym, so admin <-> DM-sender matching still works.
- Usernames, first/last names, phone numbers, bios, photos: dropped.
- Message text: phone numbers, emails, user @mentions and user profile links
  are replaced with placeholders; URL domains and wallet addresses are kept
  (they are scam indicators, not personal data about the author).
- Channel/group ids and usernames are public entities and are kept.
"""

from __future__ import annotations

from dataclasses import dataclass

# Placeholders written in place of redacted spans.
REDACTED_PHONE = "<PHONE>"
REDACTED_EMAIL = "<EMAIL>"
REDACTED_MENTION = "<USER>"


@dataclass(frozen=True)
class Pseudonymizer:
    """Keyed, deterministic pseudonymization of Telegram user ids.

    Attributes:
        salt: Secret from ``PSEUDONYM_SALT``. Shared out-of-band by the team,
            never committed, destroyed at the end of the project (after which
            pseudonyms can no longer be linked back to ids).
        length: Number of hex characters kept from the HMAC digest.
    """

    salt: str
    length: int = 16

    def user(self, user_id: int) -> str:
        """Return the pseudonym for a user id (e.g. ``"u_3f9a..."``).

        A plain hash is NOT enough: Telegram ids are small integers and a
        plain hash is reversible by brute force; the HMAC key prevents that.
        """
        raise NotImplementedError


def redact_text(text: str, known_chat_usernames: set[str] | None = None) -> str:
    """Remove personal data from message text, keeping scam-relevant signals.

    Replaces phone numbers, email addresses, and @mentions / ``t.me/<name>``
    links that point to users (not to channels/groups in
    ``known_chat_usernames``) with placeholders. Keeps URLs (at least the
    domain), crypto wallet addresses, and invite links to public chats.

    Args:
        text: Raw message text.
        known_chat_usernames: Public channel/group usernames that are safe to keep.

    Returns:
        Redacted text.
    """
    raise NotImplementedError


def sanitize_user(user, pseudonymizer: Pseudonymizer) -> dict:
    """Reduce a Telethon ``User`` to non-identifying fields.

    Returns:
        ``{"user": <pseudonym>, "is_bot": bool, "is_scam": bool,
        "is_fake": bool, "is_premium": bool}`` — no name, username or phone.
    """
    raise NotImplementedError


def sanitize_message(message, pseudonymizer: Pseudonymizer, known_chat_usernames: set[str] | None = None) -> dict:
    """Convert a Telethon ``Message`` into the on-disk record, already pseudonymized.

    Returns:
        Record with message id, chat id, date, sender pseudonym (or channel id
        for channel posts / anonymous admins), redacted text, reply_to,
        forward source (channel id kept, user source pseudonymized), views,
        media type.
    """
    raise NotImplementedError
