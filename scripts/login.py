"""One-time interactive login: creates the local .session file.

Read-only check: signs in and prints whether the account is authorized.
Never prints ids, phone numbers or other account details.

Usage: python scripts/login.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon.sync import TelegramClient

from src.utils.config import load_config, session_path


def main() -> None:
    config = load_config()
    session = session_path(config)
    # Telethon appends ".session" itself.
    # No `with client:` here: its __enter__ calls start() without our phone and prompts for it.
    client = TelegramClient(str(session.with_suffix("")), config.api_id, config.api_hash)
    try:
        client.start(phone=config.phone)  # prompts for the login code (and 2FA password, if set)
        print("Logged in:", client.is_user_authorized())
        print("Session file:", session.name, "(gitignored, never share it)")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
