"""Read-only peek at public channels: recent posts, t.me links, comments.

Does NOT join: reads a public channel's history and, if it has a linked
discussion group, the comment threads of its most-commented posts.
Never sends, reacts or clicks anything. Prints only aggregate numbers;
full data goes to data/interim/<topic>/peek/<username>_{posts,comments}.jsonl.gz.

Usage:
    python scripts/peek_channel.py --topic crypto MoneroEconomicForum MoneroOrangePills --posts 200
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telethon import errors
from telethon.tl.types import (
    MessageEntityTextUrl,
    MessageEntityUrl,
    PeerChannel,
    PeerUser,
)

from src.utils.config import add_topic_arg, load_config, make_client, paths

TME_RE = re.compile(r"(?:https?://)?(?:t\.me|telegram\.me)/(\+?[\w\-]+(?:/[\w\-]+)?)", re.I)


def extract_links(msg) -> dict[str, list[str]]:
    """t.me links found in plain text, hidden behind text (entities) and in buttons."""
    text = msg.message or ""
    plain = set(TME_RE.findall(text))
    hidden, buttons = set(), set()
    for ent in msg.entities or []:
        if isinstance(ent, MessageEntityTextUrl):
            hidden.update(TME_RE.findall(ent.url))
        elif isinstance(ent, MessageEntityUrl):
            plain.update(TME_RE.findall(text[ent.offset:ent.offset + ent.length]))
    for row in getattr(msg.reply_markup, "rows", None) or []:
        for b in row.buttons:
            url = getattr(b, "url", None)  # URL buttons (class name varies across layers)
            if isinstance(url, str):
                buttons.update(TME_RE.findall(url))
    lower = lambda s: sorted({x.lower() for x in s})
    return {"plain": lower(plain), "hidden": lower(hidden), "buttons": lower(buttons)}


def sender_kind(msg) -> str:
    if isinstance(msg.from_id, PeerUser):
        return "user"
    if isinstance(msg.from_id, PeerChannel):
        return "channel"  # posted "as" a channel (often the channel itself / admins)
    return "none"


def post_record(msg) -> dict:
    fwd = msg.fwd_from
    return {
        "id": msg.id,
        "date": msg.date.isoformat(),
        "text": msg.message or "",
        "views": msg.views,
        "forwards": msg.forwards,
        "n_comments": msg.replies.replies if msg.replies else None,
        "is_forward": fwd is not None,
        "fwd_from_channel": getattr(getattr(fwd, "from_id", None), "channel_id", None),
        "media": type(msg.media).__name__ if msg.media else None,
        "links": extract_links(msg),
    }


def comment_record(msg, post_id: int) -> dict:
    return {
        "post_id": post_id,
        "id": msg.id,
        "date": msg.date.isoformat(),
        "sender_kind": sender_kind(msg),
        "sender_id": getattr(msg.from_id, "user_id", None) or getattr(msg.from_id, "channel_id", None),
        "text": msg.message or "",
        "links": extract_links(msg),
    }


async def peek(client, username: str, n_posts: int, n_threads: int, per_thread: int, out_dir: Path) -> None:
    channel = await client.get_entity(username)
    posts = [m async for m in client.iter_messages(channel, limit=n_posts, wait_time=2)]
    recs = [post_record(m) for m in posts]
    with gzip.open(out_dir / f"{username}_posts.jsonl.gz", "wt", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    all_links = Counter()
    for r in recs:
        for kind, links in r["links"].items():
            for l in links:
                all_links[(kind, l)] += 1
    invite = {l for (_, l) in all_links if l.startswith("+") or l.startswith("joinchat")}
    with_comments = [r for r in recs if r["n_comments"]]
    print(f"\n== {username}")
    if recs:
        print(f"posts read: {len(recs)}  ({recs[-1]['date'][:10]} -> {recs[0]['date'][:10]})")
    print(f"posts with t.me links: {sum(1 for r in recs if any(r['links'].values()))}")
    print(f"distinct t.me targets: {len({l for (_, l) in all_links})} "
          f"(plain {sum(1 for k,_ in all_links if k=='plain')}, hidden {sum(1 for k,_ in all_links if k=='hidden')}, "
          f"buttons {sum(1 for k,_ in all_links if k=='buttons')}); private invite links: {len(invite)}")
    print(f"posts with comments enabled/non-zero: {len(with_comments)}, total comments: {sum(r['n_comments'] for r in with_comments)}")

    if not with_comments:
        return
    top = sorted(with_comments, key=lambda r: r["n_comments"], reverse=True)[:n_threads]
    comments = []
    for r in top:
        try:
            async for c in client.iter_messages(channel, reply_to=r["id"], limit=per_thread):
                comments.append(comment_record(c, r["id"]))
        except errors.RPCError as e:
            print(f"  comments of a post not readable: {type(e).__name__}")
            break
        await asyncio.sleep(3)
    with gzip.open(out_dir / f"{username}_comments.jsonl.gz", "wt", encoding="utf-8") as fh:
        for c in comments:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    kinds = Counter(c["sender_kind"] for c in comments)
    senders = Counter(c["sender_id"] for c in comments if c["sender_kind"] == "user")
    print(f"comments read: {len(comments)} from {len(top)} threads; sender kinds {dict(kinds)}; "
          f"distinct users: {len(senders)}; comments with t.me links: {sum(1 for c in comments if any(c['links'].values()))}")


async def main_async(args) -> None:
    out_dir = paths(args.topic).peek
    out_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.topic)
    print(f"topic: {args.topic} | output: {out_dir}")
    client = make_client(config)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not logged in: run scripts/login.py first.")
    try:
        for u in args.usernames:
            try:
                await peek(client, u, args.posts, args.threads, args.per_thread, out_dir)
            except errors.FloodWaitError as e:
                print(f"FLOODWAIT {e.seconds}s — stopping. Log it in memory/collection-log.md.")
                break
            await asyncio.sleep(5)
    finally:
        await client.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    ap.add_argument("usernames", nargs="+")
    ap.add_argument("--posts", type=int, default=200)
    ap.add_argument("--threads", type=int, default=10, help="most-commented posts whose comments are read")
    ap.add_argument("--per-thread", type=int, default=50)
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
