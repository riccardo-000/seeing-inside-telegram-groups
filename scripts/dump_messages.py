"""Download the messages of the chosen channels/groups (read-only, no joins).

Chats come from --chats (usernames), --from-pairs (channel + group of every row
of data/interim/<topic>/pairs/final_pairs.csv, joined or not) or --from-master
(channel + group of every row of data/interim/<topic>/master.csv with an active
community/standalone group). The window starts at --since (a fixed date, the
same for every chat and run) or else --days before now; it only matters on a
chat's first run. Output: data/raw/<topic>/messages/. Resumable: rerunning
only fetches new messages, so --max-messages splits a long dump over several
runs. Uses the account's daily username-resolve budget (src/utils/budget.py).
Stops at the first FloodWait longer than 60 s. Create
data/raw/<topic>/messages/STOP to stop gracefully between chats.

Usage:
    python scripts/dump_messages.py --topic crypto --from-pairs --since 2026-07-30 --dry-run
    python scripts/dump_messages.py --topic crypto --from-pairs --since 2026-07-30 --max-messages 50000
    python scripts/dump_messages.py --topic crypto --chats cancore_io cancore_chat --days 30
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon import errors
from telethon.tl.types import ChannelForbidden, InputPeerChannel

from src.collect.messages import dump_all
from src.utils.budget import BudgetExceeded, ResolveBudget
from src.utils.config import add_topic_arg, load_config, make_client, paths
from src.utils.privacy import Pseudonymizer


def chats_from_master(path: Path) -> list[str]:
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


def chats_from_pairs(path: Path) -> list[str]:
    """Channel then group of every pair, in file order, without duplicates."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    names, seen = [], set()
    for r in rows:
        for n in (r.get("channel", ""), r.get("group", "")):
            n = n.strip().lstrip("@")
            if n and n.lower() not in seen:
                seen.add(n.lower())
                names.append(n)
    return names


async def main_async(args) -> None:
    p = paths(args.topic)
    out = p.messages
    names = (list(args.chats or []) + (chats_from_master(p.master) if args.from_master else [])
             + (chats_from_pairs(p.pairs / "final_pairs.csv") if args.from_pairs else []))
    if not names:
        raise SystemExit("No chats: use --chats, --from-pairs or --from-master")
    since = (datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
             if args.since else None)
    config = load_config(args.topic)
    pseudo = Pseudonymizer(config.pseudonym_salt) if config.pseudonym_salt else None
    print(f"{len(names)} chats | pseudonymization: {'ON' if pseudo else 'OFF (no PSEUDONYM_SALT)'}")
    print(f"topic: {args.topic} | output: {out} | window from "
          f"{since.date() if since else f'{args.days} days ago'} | max messages per chat: {args.max_messages}")
    client = make_client(config)
    if args.dry_run:
        uncached = []
        for n in names:
            try:
                client.session.get_input_entity(n)
            except (ValueError, KeyError, TypeError):
                uncached.append(n)
        print(f"dry run, no Telegram: {len(names) - len(uncached)} chats in the session cache, "
              f"{len(uncached)} would cost a username resolve: {' '.join(uncached)}")
        return
    budget = ResolveBudget("dump_messages", config.account)
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
            try:
                ent = await client.get_entity(inp)
            except errors.ChannelPrivateError:
                print(f"  @{n}: private or banned, skipped")
                continue
            if isinstance(ent, ChannelForbidden):
                print(f"  @{n}: private or banned, skipped")
                continue
            entities.append(ent)
        print(f"resolve budget left today: {budget.remaining()}")
        for ent in entities:
            if (out / "STOP").exists():
                print("STOP file found")
                break
            await dump_all(client, [ent], out, days=args.days, since=since, pseudonymizer=pseudo,
                           pause=args.pause, limit=args.max_messages)
    except BudgetExceeded as e:
        print(f"STOPPED: {e}")
    except errors.FloodWaitError as e:
        print(f"FLOODWAIT {e.seconds}s — stopped. Log it in memory/collection-log.md and tell the others.")
    finally:
        await client.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    ap.add_argument("--chats", nargs="*", help="channel/group usernames")
    ap.add_argument("--from-master", action="store_true", help="all active pairs in data/interim/<topic>/master.csv")
    ap.add_argument("--from-pairs", action="store_true",
                    help="channel + group of every pair in data/interim/<topic>/pairs/final_pairs.csv")
    ap.add_argument("--since", help="window start YYYY-MM-DD (UTC), same for all chats; overrides --days")
    ap.add_argument("--days", type=int, default=90, help="history window on the first run")
    ap.add_argument("--dry-run", action="store_true",
                    help="only count the chats that would cost a username resolve, no Telegram")
    ap.add_argument("--pause", type=float, default=6.0, help="seconds between requests")
    ap.add_argument("--max-messages", type=int, default=None,
                    help="max new messages per chat in this run, oldest first (default: no cap)")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
