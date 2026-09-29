"""Download the messages of the chosen channels/groups (read-only, no joins).

Chats come from --chats (usernames) or --from-master (channel + group of every
row of data/interim/master.csv with an active community/standalone group).
Resumable: rerunning only fetches new messages. Uses the shared daily
username-resolve budget (src/utils/budget.py). Stops at the first FloodWait
longer than 60 s. Create data/raw/messages/STOP to stop gracefully between chats.

Usage:
    python scripts/dump_messages.py --from-master --days 90
    python scripts/dump_messages.py --chats cancore_io cancore_chat --days 30
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon import TelegramClient, errors
from telethon.tl.types import InputPeerChannel

from src.collect.messages import dump_all
from src.utils.budget import BudgetExceeded, ResolveBudget
from src.utils.config import DATA_INTERIM, DATA_RAW, load_config, session_path
from src.utils.privacy import Pseudonymizer

OUT = DATA_RAW / "messages"


def chats_from_master() -> list[str]:
    path = DATA_INTERIM / "master.csv"
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["channel"] and r["group"] and r["group_active"] == "True"
                and r["group_type"] in ("community", "standalone")]
    names = []
    for r in rows:
        for n in (r["channel"], r["group"]):
            n = n.lstrip("@")
            if n and n.lower() not in {x.lower() for x in names}:
                names.append(n)
    return names


async def main_async(args) -> None:
    names = list(args.chats or []) + (chats_from_master() if args.from_master else [])
    if not names:
        raise SystemExit("No chats: use --chats or --from-master")
    config = load_config()
    pseudo = Pseudonymizer(config.pseudonym_salt) if config.pseudonym_salt else None
    print(f"{len(names)} chats | pseudonymization: {'ON' if pseudo else 'OFF (no PSEUDONYM_SALT)'}")
    budget = ResolveBudget("dump_messages")
    client = TelegramClient(str(session_path(config).with_suffix("")), config.api_id, config.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not logged in: run scripts/login.py first.")
    try:
        entities = []
        for n in names:
            try:
                inp = client.session.get_input_entity(n)
            except (ValueError, KeyError, TypeError):
                budget.take()
                await asyncio.sleep(args.pause)
                try:
                    inp = await client.get_input_entity(n)
                except (ValueError, errors.RPCError):
                    print(f"  @{n}: not found, skipped")
                    continue
            if not isinstance(inp, InputPeerChannel):
                print(f"  @{n}: not a channel/group, skipped")
                continue
            await asyncio.sleep(args.pause)
            entities.append(await client.get_entity(inp))
        print(f"resolve budget left today: {budget.remaining()}")
        for ent in entities:
            if (OUT / "STOP").exists():
                print("STOP file found")
                break
            await dump_all(client, [ent], OUT, days=args.days, pseudonymizer=pseudo, pause=args.pause)
    except BudgetExceeded as e:
        print(f"STOPPED: {e}")
    except errors.FloodWaitError as e:
        print(f"FLOODWAIT {e.seconds}s — stopped. Log it in memory/collection-log.md and tell the others.")
    finally:
        await client.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chats", nargs="*", help="channel/group usernames")
    ap.add_argument("--from-master", action="store_true", help="all active pairs in data/interim/master.csv")
    ap.add_argument("--days", type=int, default=90, help="history window on the first run")
    ap.add_argument("--pause", type=float, default=6.0, help="seconds between requests")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
