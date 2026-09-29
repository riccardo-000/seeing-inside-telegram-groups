"""Privacy at ingestion: nothing that identifies a person is written to disk.

Collectors pass Telethon objects through :func:`sanitize_message` before
writing. Design and rationale: ``memory/data-protection.md``.

Rules:
- User ids -> keyed pseudonym (HMAC-SHA256 with ``PSEUDONYM_SALT``). Same id
  always maps to the same pseudonym, so admin <-> DM-sender matching still works.
- Usernames, first/last names, phone numbers, bios, photos: dropped.
- Message text: phone numbers and emails are replaced with placeholders;
  @mentions of names that are not known public chats are replaced with
  ``<USER>``. URLs, domains, wallet addresses and links to public chats are
  kept (they are scam indicators, not personal data about the author).
- Channel/group ids and usernames are public entities and are kept.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass

from telethon.tl.types import PeerChannel, PeerChat, PeerUser

# Placeholders written in place of redacted spans.
REDACTED_PHONE = "<PHONE>"
REDACTED_EMAIL = "<EMAIL>"
REDACTED_MENTION = "<USER>"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# 8+ digits, optionally with +, spaces, dashes, dots or parentheses in between
PHONE_RE = re.compile(r"(?<![\w/])\+?\d[\d\s().-]{6,}\d(?![\w/])")
MENTION_RE = re.compile(r"(?<![\w/])@([A-Za-z]\w{3,31})")


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
        if not self.salt:
            raise ValueError("PSEUDONYM_SALT is empty")
        digest = hmac.new(self.salt.encode(), str(int(user_id)).encode(), hashlib.sha256).hexdigest()
        return "u_" + digest[: self.length]


def redact_text(text: str, known_chat_usernames: set[str] | None = None) -> str:
    """Remove personal data from message text, keeping scam-relevant signals.

    Phones and emails become placeholders. @mentions are kept only if they are
    in ``known_chat_usernames`` (public channels/groups), else ``<USER>``.
    ``t.me/...`` links are kept: they point to chats far more often than to
    people, and they are the scam indicators we study.
    """
    if not text:
        return ""
    known = {u.lower() for u in (known_chat_usernames or set())}
    text = EMAIL_RE.sub(REDACTED_EMAIL, text)
    text = PHONE_RE.sub(REDACTED_PHONE, text)
    return MENTION_RE.sub(lambda m: m.group(0) if m.group(1).lower() in known else REDACTED_MENTION, text)


def sanitize_user(user, pseudonymizer: Pseudonymizer) -> dict:
    """Reduce a Telethon ``User`` to non-identifying fields."""
    return {
        "user": pseudonymizer.user(user.id),
        "is_bot": bool(getattr(user, "bot", False)),
        "is_scam": bool(getattr(user, "scam", False)),
        "is_fake": bool(getattr(user, "fake", False)),
        "is_premium": bool(getattr(user, "premium", False)),
    }


def peer_ref(peer, pseudonymizer: Pseudonymizer | None) -> tuple[str, str | int | None]:
    """(kind, id) for a peer: users are pseudonymized, chats/channels kept."""
    if isinstance(peer, PeerUser):
        return "user", pseudonymizer.user(peer.user_id) if pseudonymizer else peer.user_id
    if isinstance(peer, PeerChannel):
        return "channel", peer.channel_id
    if isinstance(peer, PeerChat):
        return "chat", peer.chat_id
    return "none", None


def sanitize_message(message, pseudonymizer: Pseudonymizer | None,
                     known_chat_usernames: set[str] | None = None) -> dict:
    """Convert a Telethon ``Message`` into the on-disk record.

    With a pseudonymizer: sender ids are pseudonymized and text is redacted.
    Without one (team decision 2026-09-22: privacy deferred): raw ids and text.
    """
    kind, sender = peer_ref(message.from_id, pseudonymizer)
    fwd = message.fwd_from
    fwd_kind, fwd_id = peer_ref(getattr(fwd, "from_id", None), pseudonymizer) if fwd else ("none", None)
    reply = message.reply_to
    text = message.message or ""
    return {
        "chat_id": message.chat_id,
        "id": message.id,
        "date": message.date.isoformat(),
        "sender_kind": kind,           # user / channel (channel itself or anonymous admin) / none
        "sender": sender,
        "post_author": message.post_author,  # admin signature on channel posts, if enabled
        "text": redact_text(text, known_chat_usernames) if pseudonymizer else text,
        "reply_to": getattr(reply, "reply_to_msg_id", None),
        "thread_top": getattr(reply, "reply_to_top_id", None),
        "fwd_kind": fwd_kind,
        "fwd_from": fwd_id,
        "views": message.views,
        "forwards": message.forwards,
        "n_replies": message.replies.replies if message.replies else None,
        "media": type(message.media).__name__ if message.media else None,
        "service": type(message.action).__name__ if message.action else None,
    }
