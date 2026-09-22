"""Configuration loading.

All secrets come from the environment (populated from a local, gitignored
``.env`` file). Nothing sensitive is hardcoded in the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


@dataclass(frozen=True)
class TelegramConfig:
    """Credentials and settings for the Telethon client.

    Attributes:
        api_id: Numeric API id from my.telegram.org.
        api_hash: API hash from my.telegram.org.
        phone: Phone number of the research account (E.164 format).
        session_name: Base name of the local ``.session`` file (gitignored).
        pseudonym_salt: Secret used to HMAC user IDs before analysis.
    """

    api_id: int
    api_hash: str
    phone: str
    session_name: str
    pseudonym_salt: str


def load_config(env_file: Path | None = None) -> TelegramConfig:
    """Load configuration from ``.env`` / environment variables.

    Args:
        env_file: Optional path to a ``.env`` file. Defaults to
            ``PROJECT_ROOT / ".env"``.

    Returns:
        A populated :class:`TelegramConfig`.

    Raises:
        RuntimeError: If a required variable (``TELEGRAM_API_ID``,
            ``TELEGRAM_API_HASH``, ``TELEGRAM_PHONE``) is missing.
    """
    raise NotImplementedError


def session_path(config: TelegramConfig) -> Path:
    """Return the path of the Telethon session file (outside any tracked dir).

    Args:
        config: Loaded configuration.

    Returns:
        Path to ``<PROJECT_ROOT>/<session_name>.session``; gitignored via
        the ``*.session`` rule.
    """
    raise NotImplementedError
