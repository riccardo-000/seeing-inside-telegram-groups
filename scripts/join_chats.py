"""Join the public groups (or channels) of the final pairs, slowly. Never posts.

Joining is the only action: the account never sends, reacts, presses buttons
or answers captchas. Groups whose bot asks new members to verify (button,
captcha) or that restrict/remove us are only *detected* by reading, logged as
``needs_verification`` / ``removed`` and left as they are. Groups that need an
admin's approval (join request) are skipped without sending a request.

Input: data/interim/<topic>/pairs/final_pairs.csv (columns ``channel``, ``group``).
Output: data/interim/<topic>/joins/joins.csv, one row per attempt. Resumable:
chats with a final outcome are skipped on the next run; ``failed`` is retried.

Telegram does not publish join limits; the defaults (20 joins per run, ~90-120 s
apart) are a cautious guess. Stops at the first FloodWait of any length.
ONE person per account at a time: log the run in memory/collection-log.md.
Create data/interim/<topic>/joins/STOP to stop gracefully between joins.

Usage:
    python scripts/join_chats.py --topic crypto --dry-run
    python scripts/join_chats.py --topic crypto --kind groups --max-joins 20
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon import errors
from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest
from telethon.tl.types import (Channel, ChannelForbidden, ChannelParticipantBanned,
                               InputPeerChannel, InputPeerSelf, MessageEntityMentionName)

from src.utils.budget import DAILY_LIMIT, BudgetExceeded, ResolveBudget
from src.utils.config import add_topic_arg, load_config, make_client, paths

FIELDS = ["date_utc", "time_utc", "chat", "kind", "status", "reason"]
# outcomes that are not retried
FINAL = {"joined", "already_member", "needs_verification", "removed",
         "join_request", "not_found", "not_a_channel", "private"}
MAX_CHATS = 480  # Telegram caps an account at 500 channels + supergroups


def queue_from_pairs(path: Path, kind: str) -> list[str]:
    col = "group" if kind == "groups" else "channel"
    with open(path, newline="", encoding="utf-8-sig") as fh:
        names = [r[col].strip().lstrip("@") for r in csv.DictReader(fh) if r.get(col, "").strip()]
    seen, out = set(), []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


def read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_row(path: Path, chat: str, kind: str, status: str, reason: str = "") -> None:
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date_utc": now.date().isoformat(), "time_utc": now.strftime("%H:%M:%S"),
                    "chat": chat, "kind": kind, "status": status, "reason": reason})
    print(f"  @{chat}: {status}{' (' + reason + ')' if reason else ''}", flush=True)


async def verification_state(client, ent: Channel, me_id: int, joined_at: datetime) -> str | None:
    """Read-only check, some time after joining: did a bot gate or remove us?"""
    peer = InputPeerChannel(ent.id, ent.access_hash)
    try:
        now = await client.get_entity(peer)
    except errors.ChannelPrivateError:
        return "removed"
    if isinstance(now, ChannelForbidden) or getattr(now, "left", False):
        return "removed"
    try:
        part = (await client(GetParticipantRequest(peer, InputPeerSelf()))).participant
        if isinstance(part, ChannelParticipantBanned):
            return "needs_verification"  # restricted right after joining: captcha bots do this
    except errors.UserNotParticipantError:
        return "removed"
    except errors.RPCError:
        pass
    # a message after our join, with buttons, that mentions us (typical captcha prompt)
    async for m in client.iter_messages(peer, limit=20):
        if m.date < joined_at:
            break
        if m.reply_markup is not None and any(
                isinstance(e, MessageEntityMentionName) and e.user_id == me_id for e in (m.entities or [])):
            return "needs_verification"
    return None


async def main_async(args) -> None:
    p = paths(args.topic)
    pairs = Path(args.pairs) if args.pairs else p.pairs / "final_pairs.csv"
    log_path = p.interim / "joins" / "joins.csv"
    stop = log_path.parent / "STOP"
    queue = queue_from_pairs(pairs, args.kind)
    log = read_log(log_path)
    done = {r["chat"].lower() for r in log if r["status"] in FINAL}
    member = {r["chat"].lower() for r in log if r["status"] in ("joined", "already_member", "needs_verification")}
    todo = [n for n in queue if n.lower() not in done]
    print(f"topic: {args.topic} | {args.kind}: {len(queue)} in {pairs.name}, {len(todo)} to do | "
          f"member of {len(member)} chats so far (log: {log_path})")
    if args.dry_run:
        for n in todo[: args.max_joins]:
            print(f"  would join @{n}")
        return
    if not todo:
        return
    config = load_config(args.topic)
    budget = ResolveBudget("join_chats", config.account, daily_limit=args.daily_limit)
    client = make_client(config)
    client.flood_sleep_threshold = 0  # never sleep through a FloodWait: stop instead
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not logged in: run scripts/login.py first.")
    joins = 0
    try:
        me_id = (await client.get_me(input_peer=True)).user_id
        for n in todo:
            if joins >= args.max_joins:
                print(f"max joins for this run reached ({args.max_joins})")
                break
            if len(member) >= MAX_CHATS:
                print(f"STOPPED: member of {len(member)} chats, close to Telegram's 500 cap")
                break
            if stop.exists():
                print("STOP file found")
                break
            try:
                inp = client.session.get_input_entity(n)
            except (ValueError, KeyError, TypeError):
                budget.take()
                await asyncio.sleep(args.pause)
                try:
                    inp = await client.get_input_entity(n)
                except (ValueError, errors.UsernameInvalidError, errors.UsernameNotOccupiedError):
                    write_row(log_path, n, args.kind, "not_found")
                    continue
            if not isinstance(inp, InputPeerChannel):
                write_row(log_path, n, args.kind, "not_a_channel")
                continue
            await asyncio.sleep(args.pause)
            try:
                ent = await client.get_entity(inp)
            except errors.ChannelPrivateError:
                write_row(log_path, n, args.kind, "private")
                continue
            if isinstance(ent, ChannelForbidden):
                write_row(log_path, n, args.kind, "private", "banned or private")
                continue
            if not ent.left:
                write_row(log_path, n, args.kind, "already_member")
                member.add(n.lower())
                continue
            if getattr(ent, "join_request", False):
                write_row(log_path, n, args.kind, "join_request", "admin approval needed, not requested")
                continue
            await asyncio.sleep(args.pause)
            joined_at = datetime.now(timezone.utc)
            try:
                await client(JoinChannelRequest(inp))
            except errors.InviteRequestSentError:
                write_row(log_path, n, args.kind, "join_request", "Telegram sent a join request")
                continue
            except errors.ChannelsTooMuchError:
                print("STOPPED: Telegram says the account is in too many channels")
                break
            except errors.ChannelPrivateError:
                write_row(log_path, n, args.kind, "private")
                continue
            except errors.UserAlreadyParticipantError:
                write_row(log_path, n, args.kind, "already_member")
                member.add(n.lower())
                continue
            joins += 1
            member.add(n.lower())
            # wait, then look (read-only) for a captcha bot, and space out the joins
            gap = args.delay + random.uniform(0, args.jitter)
            await asyncio.sleep(min(args.check_after, gap))
            state = await verification_state(client, ent, me_id, joined_at)
            write_row(log_path, n, args.kind, state or "joined", f"checked after {args.check_after:.0f} s")
            if state == "removed":
                member.discard(n.lower())
            await asyncio.sleep(max(0.0, gap - args.check_after))
    except BudgetExceeded as e:
        print(f"STOPPED: {e}")
    except errors.FloodWaitError as e:
        req = type(e.request).__name__ if getattr(e, "request", None) else "?"
        print(f"FLOODWAIT {e.seconds}s on {req} — stopped. Log it in memory/collection-log.md and tell the others.")
    except errors.RPCError as e:
        print(f"STOPPED on Telegram error {type(e).__name__}: {e}")
    finally:
        await client.disconnect()
        print(f"joins this run: {joins} | member of {len(member)} chats (update 'Joined so far' "
              f"in memory/collection-log.md) | resolve budget left today: {budget.remaining()}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    ap.add_argument("--kind", choices=("groups", "channels"), default="groups",
                    help="which side of the pairs to join (decision 2026-10-18: groups first)")
    ap.add_argument("--pairs", help="pairs CSV (default: data/interim/<topic>/pairs/final_pairs.csv)")
    ap.add_argument("--max-joins", type=int, default=20, help="max successful joins in this run")
    ap.add_argument("--delay", type=float, default=90.0, help="seconds between joins")
    ap.add_argument("--jitter", type=float, default=30.0, help="random extra seconds between joins")
    ap.add_argument("--check-after", type=float, default=60.0,
                    help="seconds after a join before looking for a captcha bot")
    ap.add_argument("--pause", type=float, default=6.0, help="seconds between other requests")
    ap.add_argument("--daily-limit", type=int, default=DAILY_LIMIT, help="account's daily resolve budget")
    ap.add_argument("--dry-run", action="store_true", help="only print the queue, no Telegram")
    args = ap.parse_args()
    if args.check_after > args.delay:
        ap.error("--check-after must not exceed --delay")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
