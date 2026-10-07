"""Configuration loading and data layout.

All secrets come from the environment (populated from a local, gitignored
``.env`` file). Nothing sensitive is hardcoded in the repository.

The study has two arms (topics), each collected by its own Telegram account:
``crypto`` and ``conspiracy``. One ``.env`` holds both accounts, with the
suffixes ``_CRYPTO`` / ``_CONSPIRACY`` (e.g. ``TELEGRAM_API_ID_CONSPIRACY``).
Unsuffixed variables (``TELEGRAM_API_ID``...) are still read as the crypto
account, so older ``.env`` files keep working.

Every script takes ``--topic``; the topic picks both the data folders
(:func:`paths`) and the account (:func:`load_config`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

TOPICS = ("crypto", "conspiracy")
DEFAULT_SESSION = {"crypto": "research", "conspiracy": "research_conspiracy"}


@dataclass(frozen=True)
class TelegramConfig:
    """Credentials and settings for the Telethon client of one account.

    Attributes:
        account: Account name (``crypto`` or ``conspiracy``).
        api_id: Numeric API id from my.telegram.org.
        api_hash: API hash from my.telegram.org.
        phone: Phone number of the research account (E.164 format).
        session_name: Base name of the local ``.session`` file (gitignored).
        pseudonym_salt: Secret used to HMAC user IDs before analysis (shared by both accounts).
    """

    account: str
    api_id: int
    api_hash: str
    phone: str
    session_name: str
    pseudonym_salt: str


@dataclass(frozen=True)
class Paths:
    """Data folders of one topic. Nothing here is created on import."""

    topic: str

    @property
    def interim(self) -> Path:
        return DATA_INTERIM / self.topic

    @property
    def seeds(self) -> Path:
        return self.interim / "seeds"

    @property
    def prefilter(self) -> Path:
        return self.interim / "prefilter"

    @property
    def pairs(self) -> Path:
        return self.interim / "pairs"

    @property
    def audit(self) -> Path:
        return self.interim / "audit"

    @property
    def peek(self) -> Path:
        return self.interim / "peek"

    @property
    def master(self) -> Path:
        return self.interim / "master.csv"

    @property
    def messages(self) -> Path:
        return DATA_RAW / self.topic / "messages"

    @property
    def dms(self) -> Path:
        """DMs received by this topic's account."""
        return DATA_RAW / "dms" / self.topic


def paths(topic: str) -> Paths:
    """Data folders of ``topic`` (``crypto`` or ``conspiracy``)."""
    if topic not in TOPICS:
        raise ValueError(f"unknown topic {topic!r}, expected one of {TOPICS}")
    return Paths(topic)


def ledger_path(account: str) -> Path:
    """Daily resolve ledger of one account (Telegram's limits are per account)."""
    return DATA_INTERIM / "accounts" / f"resolve_ledger_{account}.csv"


def add_topic_arg(parser) -> None:
    """Add the required ``--topic`` option to an argparse parser."""
    parser.add_argument("--topic", required=True, choices=TOPICS,
                        help="study arm: picks the data folders and the Telegram account")


def _env(name: str, account: str) -> str:
    value = os.environ.get(f"{name}_{account.upper()}", "").strip()
    if not value and account == "crypto":  # pre-2026-10-07 .env files: no suffix
        value = os.environ.get(name, "").strip()
    return value


def load_config(account: str, env_file: Path | None = None) -> TelegramConfig:
    """Load the credentials of one account from ``.env`` / environment variables.

    Args:
        account: ``crypto`` or ``conspiracy``.
        env_file: Optional path to a ``.env`` file. Defaults to
            ``PROJECT_ROOT / ".env"``.

    Returns:
        A populated :class:`TelegramConfig`.

    Raises:
        RuntimeError: If ``TELEGRAM_API_ID_<ACCOUNT>``, ``TELEGRAM_API_HASH_<ACCOUNT>``
            or ``TELEGRAM_PHONE_<ACCOUNT>`` is missing.
    """
    from dotenv import load_dotenv

    if account not in TOPICS:
        raise ValueError(f"unknown account {account!r}, expected one of {TOPICS}")
    load_dotenv(env_file or PROJECT_ROOT / ".env")
    required = ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_PHONE")
    missing = [f"{n}_{account.upper()}" for n in required if not _env(n, account)]
    if missing:
        raise RuntimeError(f"Missing in .env: {', '.join(missing)}")
    return TelegramConfig(
        account=account,
        api_id=int(_env("TELEGRAM_API_ID", account)),
        api_hash=_env("TELEGRAM_API_HASH", account),
        phone=_env("TELEGRAM_PHONE", account),
        session_name=_env("TELEGRAM_SESSION_NAME", account) or DEFAULT_SESSION[account],
        pseudonym_salt=os.environ.get("PSEUDONYM_SALT", "").strip(),
    )


def session_path(config: TelegramConfig) -> Path:
    """Return the path of the Telethon session file (outside any tracked dir).

    Args:
        config: Loaded configuration.

    Returns:
        Path to ``<PROJECT_ROOT>/<session_name>.session``; gitignored via
        the ``*.session`` rule.
    """
    return PROJECT_ROOT / f"{config.session_name}.session"


def make_client(config: TelegramConfig):
    """Telethon client for ``config``'s account (not connected yet).

    Prints which account and session are used, so two arms running in
    parallel are never confused. Never prints ids or phone numbers.
    """
    from telethon import TelegramClient

    print(f"account: {config.account} | session: {config.session_name}.session", flush=True)
    # Telethon appends ".session" itself.
    return TelegramClient(str(session_path(config).with_suffix("")), config.api_id, config.api_hash)
