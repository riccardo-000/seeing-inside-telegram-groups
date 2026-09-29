"""Log unsolicited DMs received by the research account. Never replies.

ONE instance at a time for the whole team (DMs arrive per account): log it
in memory/collection-log.md before starting. First logs DMs already in the
inbox (--backfill), then keeps running and logs new ones until Ctrl+C.
Messages are not marked as read; nothing is ever sent.

Output: data/raw/dms/dms.jsonl (pseudonymized if PSEUDONYM_SALT is set).
Sender <-> admin matching uses the dumps in data/raw/messages/.

Usage:
    python scripts/dm_logger.py --backfill
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon import TelegramClient

from src.collect.dms import backfill_dms, build_indexes, register_dm_logger
from src.utils.config import DATA_RAW, load_config, session_path
from src.utils.privacy import Pseudonymizer

OUT = DATA_RAW / "dms" / "dms.jsonl"


async def main_async(args) -> None:
    config = load_config()
    pseudo = Pseudonymizer(config.pseudonym_salt) if config.pseudonym_salt else None
    admin_index, member_index = build_indexes(DATA_RAW / "messages")
    print(f"pseudonymization: {'ON' if pseudo else 'OFF (no PSEUDONYM_SALT)'} | "
          f"admin lists: {len(admin_index)} chats | member lists: {len(member_index)} chats")
    client = TelegramClient(str(session_path(config).with_suffix("")), config.api_id, config.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not logged in: run scripts/login.py first.")
    try:
        if args.backfill:
            n = await backfill_dms(client, OUT, pseudo, admin_index, member_index)
            print(f"backfill: {n} DMs already in the inbox logged")
        register_dm_logger(client, OUT, pseudo, admin_index, member_index)
        print("Listening for DMs (Ctrl+C to stop)...", flush=True)
        await client.run_until_disconnected()
    finally:
        await client.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backfill", action="store_true", help="first log DMs already in the inbox")
    try:
        asyncio.run(main_async(ap.parse_args()))
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
