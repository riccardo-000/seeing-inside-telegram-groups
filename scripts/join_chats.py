"""Join the public groups (or channels) of the final pairs, slowly. Never posts.

Joining is the only action: the account never sends, reacts, presses buttons
or answers captchas. Groups whose bot asks new members to verify (button,
captcha) or that restrict/remove us are only *detected* by reading and left as
they are: ``needs_verification`` (we cannot write, or a bot prompt with buttons
mentions us), ``restricted`` (only some rights taken, e.g. no media/links for
newcomers: a normal member otherwise), ``removed``; the reason column says which.
``--recheck STATUS`` re-runs that check later on the chats already joined, without
joining anything. ``--import-manual`` logs the chats joined by hand in the app
(join date as Telegram records it), with the same check, without joining. Groups that need an admin's approval (join request) are
skipped without sending a request.

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
    python scripts/join_chats.py --topic crypto --recheck needs_verification
    python scripts/join_chats.py --topic conspiracy --import-manual
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
FINAL = {"joined", "already_member", "restricted", "needs_verification", "removed",
         "join_request", "not_found", "not_a_channel", "private"}
MEMBER = {"joined", "already_member", "restricted", "needs_verification"}
# ChatBannedRights flags that matter to a member who only reads
RIGHTS = ("send_messages", "send_plain", "send_media", "send_photos", "send_videos", "send_docs",
          "send_audios", "send_voices", "send_roundvideos", "send_stickers", "send_gifs",
          "send_inline", "embed_links", "send_polls")
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


def write_row(path: Path, chat: str, kind: str, status: str, reason: str = "",
              when: datetime | None = None) -> None:
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = when or datetime.now(timezone.utc)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date_utc": now.date().isoformat(), "time_utc": now.strftime("%H:%M:%S"),
                    "chat": chat, "kind": kind, "status": status, "reason": reason})
    print(f"  @{chat}: {status}{' (' + reason + ')' if reason else ''}", flush=True)


def _restrictions(part: ChannelParticipantBanned) -> tuple[bool, str]:
    """(muted, short description) of the rights a group took from us."""
    r = part.banned_rights
    taken = [f for f in RIGHTS if getattr(r, f, False)]
    until = r.until_date
    # until_date 0 (or far in the future) means for ever
    forever = until is None or until.year < 2000 or until.year > datetime.now(timezone.utc).year + 1
    desc = ", ".join(taken) or "none"
    if not forever:
        desc += f" until {until:%Y-%m-%d %H:%M}Z"
    return bool(r.send_messages or getattr(r, "send_plain", False)), desc


async def verification_state(client, ent: Channel, me_id: int, joined_at: datetime) -> tuple[str, str]:
    """Read-only check, some time after joining: did a bot gate, restrict or remove us?

    Returns (status, reason). status is ``removed``; ``needs_verification`` (we
    cannot write, or a bot posted a prompt with buttons that mentions us);
    ``restricted`` (only some rights taken, e.g. media/links for newcomers: still
    a normal member); or ``joined``.
    """
    peer = InputPeerChannel(ent.id, ent.access_hash)
    try:
        now = await client.get_entity(peer)
    except errors.ChannelPrivateError:
        return "removed", "group not accessible any more"
    if isinstance(now, ChannelForbidden) or getattr(now, "left", False):
        return "removed", "not a member any more"
    muted, rights = False, ""
    try:
        part = (await client(GetParticipantRequest(peer, InputPeerSelf()))).participant
        if isinstance(part, ChannelParticipantBanned):
            if part.left or part.banned_rights.view_messages:
                return "removed", "banned"
            muted, rights = _restrictions(part)
    except errors.UserNotParticipantError:
        return "removed", "not a participant"
    except errors.RPCError:
        pass
    # first messages after our join: a prompt with buttons addressed to us = captcha
    prompt = False
    async for m in client.iter_messages(peer, offset_date=joined_at, reverse=True, limit=30):
        if m.reply_markup is not None and (m.mentioned or any(
                isinstance(e, MessageEntityMentionName) and e.user_id == me_id for e in (m.entities or []))):
            prompt = True
            break
    reasons = ([f"cannot write ({rights})"] if muted else
               [f"restricted: {rights}"] if rights else []) + (["bot prompt with buttons"] if prompt else [])
    if muted or prompt:
        return "needs_verification", "; ".join(reasons)
    if rights:
        return "restricted", "; ".join(reasons)
    return "joined", "no restriction"


async def recheck(client, log_path: Path, latest: dict[str, dict], first: dict[str, dict],
                  statuses: set[str], me_id: int, pause: float) -> None:
    """Re-run the read-only check on chats whose latest status is in ``statuses``."""
    for key, row in latest.items():
        if row["status"] not in statuses:
            continue
        try:
            inp = client.session.get_input_entity(row["chat"])
        except (ValueError, KeyError, TypeError):
            print(f"  @{row['chat']}: not in the session cache, skipped (no resolve spent)")
            continue
        await asyncio.sleep(pause)
        try:
            ent = await client.get_entity(inp)
        except errors.ChannelPrivateError:
            write_row(log_path, row["chat"], row["kind"], "removed", "recheck: group not accessible any more")
            continue
        if isinstance(ent, ChannelForbidden):
            write_row(log_path, row["chat"], row["kind"], "removed", "recheck: banned")
            continue
        f = first[key]
        joined_at = datetime.fromisoformat(f"{f['date_utc']}T{f['time_utc']}+00:00")
        await asyncio.sleep(pause)
        state, reason = await verification_state(client, ent, me_id, joined_at)
        write_row(log_path, row["chat"], row["kind"], state, f"recheck: {reason}")


async def import_manual(client, log_path: Path, latest: dict[str, dict], me_id: int, pause: float) -> None:
    """Log the public channels/groups joined by hand in the app and not yet in the log.

    Reads the account's dialogs (no username resolves). The row's date is the join
    date Telegram keeps for a member (``Channel.date``), so DMs can be matched to
    the join; the status comes from the same read-only check as after a script join.
    """
    async for d in client.iter_dialogs():
        ent = d.entity
        if not isinstance(ent, Channel) or not ent.username or ent.username.lower() in latest:
            continue
        kind = "groups" if ent.megagroup else "channels"
        await asyncio.sleep(pause)
        state, reason = await verification_state(client, ent, me_id, ent.date)
        write_row(log_path, ent.username, kind, state, f"manual join (app): {reason}", when=ent.date)


async def main_async(args) -> None:
    p = paths(args.topic)
    pairs = Path(args.pairs) if args.pairs else p.pairs / "final_pairs.csv"
    log_path = p.interim / "joins" / "joins.csv"
    stop = log_path.parent / "STOP"
    queue = queue_from_pairs(pairs, args.kind) if pairs.exists() else []
    log = read_log(log_path)
    latest, first = {}, {}
    for r in log:  # rows are in time order: a recheck row supersedes the join row
        latest[r["chat"].lower()] = r
        first.setdefault(r["chat"].lower(), r)
    done = {k for k, r in latest.items() if r["status"] in FINAL}
    member = {k for k, r in latest.items() if r["status"] in MEMBER}
    todo = [n for n in queue if n.lower() not in done]
    print(f"topic: {args.topic} | {args.kind}: {len(queue)} in {pairs.name}, {len(todo)} to do | "
          f"member of {len(member)} chats so far (log: {log_path})")
    to_recheck = sum(r["status"] in set(args.recheck or ()) for r in latest.values())
    if args.dry_run:
        if args.recheck:
            print(f"  would recheck {to_recheck} chats")
        for n in ([] if args.recheck else todo[: args.max_joins]):
            print(f"  would join @{n}")
        return
    if not (todo or args.recheck or args.import_manual):
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
        if args.import_manual:
            await import_manual(client, log_path, latest, me_id, args.pause)
            todo = []  # an import run never joins
        if args.recheck:
            await recheck(client, log_path, latest, first, set(args.recheck), me_id, args.pause)
            todo = []  # a recheck run never joins
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
            state, reason = await verification_state(client, ent, me_id, joined_at)
            write_row(log_path, n, args.kind, state, f"after {args.check_after:.0f} s: {reason}")
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
    ap.add_argument("--recheck", nargs="+", metavar="STATUS",
                    help="no joins: re-run the read-only check on chats whose latest status is STATUS "
                         "(e.g. needs_verification joined)")
    ap.add_argument("--import-manual", action="store_true",
                    help="no joins: log the public chats joined by hand in the app (join date from "
                         "Telegram) with the read-only check, then exit")
    ap.add_argument("--dry-run", action="store_true", help="only print the queue, no Telegram")
    args = ap.parse_args()
    if args.check_after > args.delay:
        ap.error("--check-after must not exceed --delay")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
