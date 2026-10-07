"""One-time interactive login: creates the local .session file.

Read-only check: signs in and prints whether the account is authorized.
Never prints ids, phone numbers or other account details.

Usage:
    python scripts/login.py --topic crypto
    python scripts/login.py --topic conspiracy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import telethon.sync  # noqa: F401  (makes the client usable without asyncio)

from src.utils.config import add_topic_arg, load_config, make_client, session_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    config = load_config(ap.parse_args().topic)
    session = session_path(config)
    # No `with client:` here: its __enter__ calls start() without our phone and prompts for it.
    client = make_client(config)
    try:
        client.start(phone=config.phone)  # prompts for the login code (and 2FA password, if set)
        print("Logged in:", client.is_user_authorized())
        print("Session file:", session.name, "(gitignored, never share it)")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
