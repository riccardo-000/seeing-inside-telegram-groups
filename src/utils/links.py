"""Extract t.me links from Telethon messages (plain text, hidden links, buttons)."""

from __future__ import annotations

import re

from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

TME_RE = re.compile(r"(?:https?://)?(?:t\.me|telegram\.me)/(\+?[\w\-]+(?:/[\w\-]+)?)", re.I)
URL_RE = re.compile(r"https?://[^\s)\]>\"']+", re.I)


def message_urls(msg) -> list[str]:
    """Every URL in a message: plain text, links hidden behind text, URL buttons."""
    text = msg.message or ""
    urls = set(URL_RE.findall(text))
    for ent in msg.entities or []:
        if isinstance(ent, MessageEntityTextUrl):
            urls.add(ent.url)
        elif isinstance(ent, MessageEntityUrl):
            urls.add(text[ent.offset:ent.offset + ent.length])
    for row in getattr(msg.reply_markup, "rows", None) or []:
        for b in row.buttons:
            url = getattr(b, "url", None)
            if isinstance(url, str):
                urls.add(url)
    return sorted(urls)


def tme_paths(urls: list[str]) -> list[str]:
    """``t.me/<path>`` parts of a list of URLs (lower-cased, invite hashes excluded from lowering)."""
    out = set()
    for u in urls:
        for p in TME_RE.findall(u):
            out.add(p if p.startswith("+") else p.lower())
    return sorted(out)
