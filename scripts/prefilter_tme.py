"""Liveness/activity prefilter over Telegram's PUBLIC WEB PREVIEW. Zero API cost.

Why this exists: ``contacts.ResolveUsername`` is the call that got the shared
account a 19 h FloodWait, and the team budget is 100 resolves/day for everyone
(see memory/decisions.md, src/utils/budget.py). The pages at
``https://t.me/<user>`` and ``https://t.me/s/<user>`` are plain HTTPS, not
MTProto: they cost nothing from that budget and are not tied to the research
account at all. So dead and dormant candidates can be thrown away here, and
resolves spent only on chats already known to be alive and busy.

Still read-only and passive (CLAUDE.md rule 3): GET on public pages, no login,
no join, no interaction.

What it can tell per username:
  - exists / not found
  - kind: channel (``/s/`` preview with posts), group (members count only),
    user/bot, unknown
  - subscribers or members
  - for channels: last post date and posts in the last 7 / 30 days
  - description and the t.me links in it (group hints, free)

Limits: supergroups have no ``/s/`` post preview, so a group's activity still
needs the API; the preview is also capped at the last ~20 posts. Telegram may
rate-limit the web endpoint by IP -- keep --delay at 1.5 s or more, and stop if
HTTP 429 appears.

Resumable: usernames already in the output file are skipped. --topic only
picks the folders (no account is used): input defaults to the topic's seed
list, output to data/interim/<topic>/prefilter/tme_prefilter.csv.

Usage:
    python scripts/prefilter_tme.py --topic conspiracy --limit 300
    python scripts/prefilter_tme.py --topic crypto --users MoneroEconomicForum AirdropGroup --dump-html
"""

from __future__ import annotations

import argparse
import csv
import html
import http.client
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import add_topic_arg, paths

SEEDS = {"crypto": "tgdataset_queue.csv", "conspiracy": "seeds_conspiracy_candidates.csv"}
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
COLS = ["username", "status", "kind", "title", "subscribers", "members", "last_post",
         "posts_7d", "posts_30d", "tme_links", "description", "http", "checked_at"]

RE_EXTRA = re.compile(r'class="tgme_page_extra">(.*?)</div>', re.S)
RE_TITLE = re.compile(r'class="tgme_page_title"[^>]*>\s*(?:<span[^>]*>)?(.*?)(?:</span>)?\s*</div>', re.S)
RE_DESC = re.compile(r'class="tgme_page_description"[^>]*>(.*?)</div>', re.S)
RE_MSG = re.compile(r'class="tgme_widget_message[ "]')
RE_TIME = re.compile(r'<time[^>]*datetime="([^"]+)"')
RE_TME = re.compile(r"t\.me/([A-Za-z][\w\d_]{3,31})")
RE_NUM = re.compile(r"([\d][\d\s.,]*)\s*(subscriber|member|subscribers|members)", re.I)
TAGS = re.compile(r"<[^>]+>")
# /s/ (channel preview) pages use a different markup than /<user> pages
RE_S_TITLE = re.compile(r'class="tgme_channel_info_header_title"[^>]*>(.*?)</div>', re.S)
RE_S_DESC = re.compile(r'class="tgme_channel_info_description"[^>]*>(.*?)</div>', re.S)
RE_S_COUNTER = re.compile(r'counter_value">([^<]+)</span>\s*<span class="counter_type">(subscribers?|members?)', re.I)


def human_number(v: str) -> str:
    """'1.04M' -> '1040000', '2.05K' -> '2050', '812' -> '812' (approximate for K/M)."""
    v = v.strip().replace(" ", "").replace(",", "")
    mult = {"K": 1_000, "M": 1_000_000}.get(v[-1:].upper(), 1)
    try:
        return str(int(float(v[:-1] if mult > 1 else v) * mult))
    except ValueError:
        return ""


def text(fragment: str) -> str:
    return html.unescape(TAGS.sub(" ", fragment)).replace("\xa0", " ").strip()


def get(url: str, timeout: float, retries: int = 3) -> tuple[int, str]:
    """GET with a few retries on network errors (truncated reads, timeouts)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except (http.client.HTTPException, urllib.error.URLError, TimeoutError, OSError):
            if attempt == retries - 1:
                return 0, ""  # recorded as http_0: network problem, not a verdict
            time.sleep(5 * (attempt + 1))
    return 0, ""


def parse_count(fragment: str, word: str) -> str:
    for num, kind in RE_NUM.findall(fragment):
        if kind.lower().startswith(word):
            return re.sub(r"[^\d]", "", num)
    return ""


VALID_USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


def check(user: str, timeout: float, dump: bool) -> dict:
    now = datetime.now(timezone.utc)
    row = {c: "" for c in COLS}
    row["username"], row["checked_at"] = user, now.isoformat(timespec="seconds")
    if not VALID_USERNAME.match(user):
        row["status"] = "not_found"  # cannot be a Telegram username: no request made
        return row

    code, page = get(f"https://t.me/s/{user}", timeout)
    row["http"] = code
    if dump:
        Path(f"tme_{user}.html").write_text(page, encoding="utf-8")
    if code == 429:
        raise SystemExit("HTTP 429 from t.me: rate-limited by IP. Stop and retry later.")
    if code != 200 or not page:
        row["status"] = "not_found" if code in (404, 410) else f"http_{code}"
        return row

    extra = " ".join(text(f) for f in RE_EXTRA.findall(page))
    m = RE_TITLE.search(page)
    row["title"] = text(m.group(1))[:120] if m else ""
    m = RE_DESC.search(page)
    desc = text(m.group(1)) if m else ""
    row["description"] = desc[:300]
    row["subscribers"] = parse_count(extra, "subscriber")
    row["members"] = parse_count(extra, "member")
    if not row["title"] and (m := RE_S_TITLE.search(page)):
        row["title"] = text(m.group(1))[:120]
    if not desc and (m := RE_S_DESC.search(page)):
        desc = text(m.group(1))
        row["description"] = desc[:300]
    for num, kind in RE_S_COUNTER.findall(page):
        key = "subscribers" if kind.lower().startswith("subscriber") else "members"
        row[key] = row[key] or human_number(num)
    desc_html = (RE_DESC.search(page) or RE_S_DESC.search(page))
    row["tme_links"] = " ".join(sorted(set(RE_TME.findall(desc_html.group(1) if desc_html else desc))))

    stamps = sorted(RE_TIME.findall(page))
    posts = len(RE_MSG.findall(page))
    if posts:
        row["kind"] = "channel"
        if stamps:
            row["last_post"] = stamps[-1]
            dates = []
            for s in stamps:
                try:
                    dates.append(datetime.fromisoformat(s))
                except ValueError:
                    pass
            row["posts_7d"] = sum(1 for d in dates if d > now - timedelta(days=7))
            row["posts_30d"] = sum(1 for d in dates if d > now - timedelta(days=30))
        row["status"] = "alive"
    elif row["members"]:
        row["kind"] = "group"
        row["status"] = "alive"
    elif row["subscribers"]:
        row["kind"] = "channel_no_preview"
        row["status"] = "alive"
    elif "tgme_page_photo" in page or row["title"]:
        row["kind"] = "user_or_bot"
        row["status"] = "alive"
    else:
        row["status"] = "empty_page"
    return row


def load_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["username"].lower() for r in csv.DictReader(fh)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    ap.add_argument("--in", dest="infile", type=Path, default=None,
                    help="CSV with a username column (default: the topic's seed list)")
    ap.add_argument("--users", nargs="*", help="check these usernames instead of --in")
    ap.add_argument("--limit", type=int, default=200, help="how many to check this run")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--dump-html", action="store_true",
                    help="save each fetched page as tme_<user>.html to check the parser")
    args = ap.parse_args()
    p = paths(args.topic)
    args.infile = args.infile or p.seeds / SEEDS[args.topic]
    args.out = args.out or p.prefilter / "tme_prefilter.csv"
    print(f"topic: {args.topic} | output: {args.out}")

    done = load_done(args.out)
    if args.users:
        queue = [u.lstrip("@") for u in args.users]
    else:
        with open(args.infile, newline="", encoding="utf-8-sig") as fh:
            queue = [r["username"] for r in csv.DictReader(fh)]
    queue = [u for u in queue if u.lower() not in done][: args.limit]
    print(f"{len(done)} already checked, {len(queue)} to check now")

    new = not args.out.exists()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {}
    with open(args.out, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        if new:
            w.writeheader()
        for i, user in enumerate(queue, 1):
            row = check(user, args.timeout, args.dump_html)
            w.writerow(row)
            fh.flush()
            key = f"{row['status']}/{row['kind'] or '-'}"
            stats[key] = stats.get(key, 0) + 1
            if i % 25 == 0 or args.dump_html:
                print(f"  {i}/{len(queue)} {user}: {key} "
                      f"subs={row['subscribers'] or row['members']} last={row['last_post']}",
                      flush=True)
            time.sleep(args.delay)
    print(f"\nDONE -> {args.out}")
    for k in sorted(stats, key=lambda k: -stats[k]):
        print(f"  {stats[k]:5d}  {k}")


if __name__ == "__main__":
    main()
