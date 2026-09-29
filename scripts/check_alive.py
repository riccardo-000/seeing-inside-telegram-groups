"""Check which seed channels still exist and whether they have a linked group.

Read-only: resolves each @username and reads the public channel info
(ResolveUsername + GetFullChannel). Never joins, never sends anything.
Slow on purpose (--delay seconds between channels) and stops at the first
FloodWait, which must be logged in memory/collection-log.md.
Resumable: usernames already in the output file are skipped.

Usage:
    python scripts/check_alive.py data/interim/seeds_tgdataset_crypto_a4.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon import TelegramClient, errors
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel

from src.utils.config import load_config, session_path

COLUMNS = [
    "channel_id", "username", "status", "checked_at", "id_matches", "is_broadcast",
    "title_now", "subscribers_now", "scam", "fake", "verified", "restricted",
    "linked_chat_id", "linked_chat_username", "error",
]


async def check_one(client: TelegramClient, row: dict) -> dict:
    out = {"channel_id": row["channel_id"], "username": row["username"],
           "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        entity = await client.get_entity(row["username"])
    except (errors.UsernameNotOccupiedError, errors.UsernameInvalidError, ValueError) as e:
        return out | {"status": "not_found", "error": type(e).__name__}
    except errors.ChannelPrivateError as e:
        return out | {"status": "private", "error": type(e).__name__}

    if not isinstance(entity, Channel):
        # The username now belongs to a user or bot: the channel is gone.
        return out | {"status": "reassigned", "error": type(entity).__name__}

    out |= {
        "status": "alive",
        # Usernames can be reused by another channel after the original is deleted.
        "id_matches": str(entity.id) == str(row["channel_id"]),
        "is_broadcast": bool(entity.broadcast),
        "title_now": entity.title,
        "scam": bool(entity.scam),
        "fake": bool(entity.fake),
        "verified": bool(entity.verified),
        "restricted": bool(entity.restricted),
    }
    full = await client(GetFullChannelRequest(entity))
    out["subscribers_now"] = full.full_chat.participants_count
    linked = full.full_chat.linked_chat_id
    if linked:
        out["linked_chat_id"] = linked
        chat = next((c for c in full.chats if c.id == linked), None)
        out["linked_chat_username"] = getattr(chat, "username", None) or ""
    return out


async def run(in_path: Path, out_path: Path, delay: float, limit: int) -> None:
    with open(in_path, newline="", encoding="utf-8") as fh:
        seeds = [r for r in csv.DictReader(fh) if r.get("username")]
    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {r["username"].lower() for r in csv.DictReader(fh)}
    todo = [r for r in seeds if r["username"].lower() not in done]
    if limit:
        todo = todo[:limit]
    print(f"{len(seeds)} seeds, {len(done)} already checked, {len(todo)} to check")

    config = load_config()
    client = TelegramClient(str(session_path(config).with_suffix("")), config.api_id, config.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not logged in: run scripts/login.py first.")

    new_file = not out_path.exists()
    try:
        with open(out_path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            if new_file:
                writer.writeheader()
            for i, row in enumerate(todo, 1):
                try:
                    res = await check_one(client, row)
                except errors.FloodWaitError as e:
                    print(f"FLOODWAIT {e.seconds}s at {row['username']} — stopping. Log it in memory/collection-log.md.")
                    break
                except errors.RPCError as e:
                    res = {"channel_id": row["channel_id"], "username": row["username"], "status": "error",
                           "error": type(e).__name__,
                           "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                writer.writerow(res)
                fh.flush()
                print(f"[{i}/{len(todo)}] {res['status']}", flush=True)
                await asyncio.sleep(delay)
    finally:
        await client.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("seeds", type=Path, help="CSV with channel_id,username columns")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--delay", type=float, default=10.0, help="seconds between channels (default 10)")
    ap.add_argument("--limit", type=int, default=0, help="check at most N channels (0 = all)")
    args = ap.parse_args()
    out = args.out or args.seeds.with_name(args.seeds.stem + "_alive.csv")
    asyncio.run(run(args.seeds, out, args.delay, args.limit))


if __name__ == "__main__":
    main()
