"""Point 5a of the analysis plan: invitations to register on a platform (pandas only).

An **invitation** is a message (any poster except service messages and channel copies) that
 (a) contains a registration / referral link — a URL with a referral parameter or a sign-up
     path on a platform domain, or a Telegram bot link with ``?start=`` (bot referral), or
 (b) contains registration wording ("sign up", "referral", "deposit", …) and a link to a
     platform domain.
Social, video, news and reference sites are never platforms (``NOT_PLATFORM``), so "claim it
on x.com" is not an invitation. Every target domain gets a class with its source:
``telegram_bot``, ``official`` (also linked by the pair's channel), ``exchange`` and
``trading_tool`` (hand-written lists below, to be reviewed by the team), ``shortener``
(destination unknown), or ``unknown`` (to be labelled by hand, see the domain files).
A **fraud hallmark** is wording such as fixed or guaranteed returns, or "deposit X, earn Y
daily", independent of the domain. Whether an invitation is suspicious is decided later from
the hallmarks, the hand labels of the ``unknown`` domains and (optionally) external lists.
"""

from __future__ import annotations

import re

import pandas as pd

from src.analyze.load import iter_pairs
from src.analyze.structure import base_domain, fragment_map

# --- link and text rules ---------------------------------------------------------------
REF_PARAM = re.compile(
    r"[?&#](ref|referral|refcode|ref_code|refid|ref_id|invite|invite_code|invitecode|inviteCode|"
    r"invitationcode|invitation_code|inviter|aff|affiliate|affiliate_id|code|promo|promocode)=", re.I)
SIGNUP_PATH = re.compile(r"/(register|registration|signup|sign-up|sign_up|invite|referral|ref|join|r)(/|\?|$)",
                         re.I)
TG_BOT_START = re.compile(r"(?:t\.me|telegram\.me)/(\w+bot)\?start(app)?=", re.I)
SIGNUP_TEXT = re.compile(
    r"sign ?up|register|registration|referral|ref link|invite code|invitation code|promo code|"
    r"use my code|my link|deposit|регистр|реферал|депозит|regístrate|registrate|registrati|"
    r"iscriviti|daftar|التسجيل", re.I)
HALLMARK = re.compile(
    r"\d+(?:[.,]\d+)?\s?%\s?(?:daily|per day|a day|each day|every day|weekly|per week|monthly|roi|profit)|"
    r"(?:daily|weekly|monthly) (?:profit|income|return|roi|earnings?|payout)|"
    r"guarantee[ds]? (?:profit|return|income)|risk[- ]free|double your|passive income|"
    r"minimum deposit|min(?:imum)?\.? deposit|deposit \$?\d+.{0,40}(?:earn|get|receive|daily)|"
    r"withdraw(?:al)? (?:daily|instantly|anytime)|доход в день|ежедневн\w* доход", re.I)

# --- domain lists (hand-written, to be reviewed by the team; decision 2026-11-10) ----------
NOT_PLATFORM = {
    "x.com", "twitter.com", "fixupx.com", "fxtwitter.com", "vxtwitter.com", "t.co",
    "youtube.com", "youtu.be", "facebook.com", "fb.com", "fb.me", "instagram.com", "tiktok.com",
    "discord.gg", "discord.com", "reddit.com", "whatsapp.com", "linkedin.com", "rumble.com",
    "bitchute.com", "odysee.com", "truthsocial.com", "twitch.tv", "substack.com", "medium.com",
    "wikipedia.org", "google.com", "share.google", "github.com", "coinmarketcap.com",
    "coingecko.com", "tradingview.com", "etherscan.io", "bscscan.com", "solscan.io",
    "tronscan.org", "dexscreener.com", "dextools.io", "forms.gle", "gitbook.io", "notion.site",
}
EXCHANGES = {
    "binance.com", "binance.info", "okx.com", "mexc.com", "mexc.co", "bybit.com", "kucoin.com",
    "gate.com", "gate.io", "bitget.com", "htx.com", "huobi.com", "kraken.com", "coinbase.com",
    "bingx.com", "bitmart.com", "lbank.com", "xt.com", "weex.com", "coinex.com", "poloniex.com",
    "crypto.com", "bitfinex.com", "bitstamp.net", "phemex.com", "blofin.com", "wazirx.com",
    "bitkub.com", "indodax.com", "tokocrypto.com", "bitunix.com", "toobit.com",
}
TRADING_TOOLS = {  # memecoin trading terminals / bots, wallets and DEXs
    "gmgn.ai", "axiom.trade", "padre.gg", "bullx.io", "trojan.com", "vyper.trade", "defined.fi",
    "tinyastro.io", "pump.fun", "bonkbot.io", "maestrobots.com",
    "metamask.io", "trustwallet.com", "phantom.app", "uniswap.org", "pancakeswap.finance",
    "raydium.io", "jup.ag", "1inch.io",
}
SHORTENERS = {"bit.ly", "tinyurl.com", "rebrand.ly", "onelink.me", "linktr.ee", "t.ly", "cutt.ly",
              "is.gd", "goo.gl", "shorturl.at", "rb.gy", "s.id"}


def _bot_name(url: str) -> str | None:
    m = TG_BOT_START.search(url)
    return f"t.me/{m.group(1).lower()}" if m else None


def message_invite(urls, text: str) -> tuple[bool, set[str]]:
    """(is_invitation, target domains) of one message, before fragment repair and classes."""
    if not isinstance(urls, list) or not urls:
        return False, set()
    targets, ref_link = set(), False
    for u in urls:
        bot = _bot_name(u)
        if bot:
            targets.add(bot)
            ref_link = True
            continue
        d = base_domain(u)
        if not d or d in {"t.me", "telegram.me", "telegram.dog", "me"} or d in NOT_PLATFORM:
            continue
        targets.add(d)
        if REF_PARAM.search(u) or SIGNUP_PATH.search(u):
            ref_link = True
    is_invite = bool(targets) and (ref_link or bool(SIGNUP_TEXT.search(text or "")))
    return is_invite, targets


def domain_class(d: str, official: set[str]) -> str:
    if d.startswith("t.me/"):
        return "telegram_bot"
    if d in official:
        return "official"
    if d in EXCHANGES:
        return "exchange"
    if d in TRADING_TOOLS:
        return "trading_tool"
    if d in SHORTENERS:
        return "shortener"
    return "unknown"


def poster(role: str, voice) -> str:
    """Who posted: channel / admin / user / bot / other_channel."""
    if isinstance(voice, str):
        return voice
    return role if role in ("bot", "other_channel") else "other"


def pair_invites(pair: pd.Series, df: pd.DataFrame) -> pd.DataFrame:
    """One row per invitation of a pair, with targets, classes and hallmark."""
    w = df[df["in_window"] & ~df["role"].isin(["service", "channel_copy"])]
    found = [message_invite(u, t) for u, t in zip(w["urls"], w["text"])]
    # official = web domains linked by the channel itself (any channel post in the window)
    ch = w["side"] == "channel"
    channel_domains = set()
    for urls in w.loc[ch, "urls"]:
        for u in urls if isinstance(urls, list) else []:
            d = base_domain(u)
            if d:
                channel_domains.add(d)
    fix = fragment_map(channel_domains.union(*[t for _, t in found]))
    official = {fix.get(d, d) for d in channel_domains} - NOT_PLATFORM - EXCHANGES - SHORTENERS
    rows = []
    for pos in [i for i, (is_inv, _) in enumerate(found) if is_inv]:
        m = w.iloc[pos]
        targets = sorted({fix.get(d, d) for d in found[pos][1]})
        classes = [domain_class(d, official) for d in targets]
        rows.append({
            "topic": pair["topic"], "pair_id": pair["pair_id"], "side": m["side"],
            "chat": m["chat"], "msg_id": m["msg_id"], "date": m["date"],
            "poster": poster(m["role"], m["voice"]), "sender": m["sender"],
            "targets": targets, "target_classes": classes, "classes": sorted(set(classes)),
            "hallmark": bool(HALLMARK.search(m["text"] or "")),
            "text": m["text"],
        })
    out = pd.DataFrame(rows)
    out.attrs["n_messages"] = {s: int((w["side"] == s).sum()) for s in ("channel", "group")}
    out.attrs["n_with_link"] = {s: int(((w["side"] == s) & w["urls"].map(
        lambda x: isinstance(x, list) and len(x) > 0)).sum()) for s in ("channel", "group")}
    return out


def compute(topic: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(invitations, per-chat table, per-pair table) for ``topic`` (both arms if None)."""
    invites, chat_rows, pair_rows = [], [], []
    for pair, df in iter_pairs(topic, text=True):
        inv = pair_invites(pair, df)
        invites.append(inv)
        p = {"topic": pair["topic"], "pair_id": pair["pair_id"]}
        for side, chat in (("channel", pair["channel"]), ("group", pair["group"])):
            s = inv[inv["side"] == side] if len(inv) else inv
            n = inv.attrs["n_messages"][side]
            row = {"topic": pair["topic"], "pair_id": pair["pair_id"], "side": side, "chat": chat,
                   "n_messages": n, "n_with_link": inv.attrs["n_with_link"][side],
                   "n_invites": len(s),
                   "invite_share": len(s) / n if n else float("nan"),
                   "n_hallmark": int(s["hallmark"].sum()) if len(s) else 0}
            for who in ("channel", "admin", "user", "bot", "other_channel"):
                row[f"n_invites_by_{who}"] = int((s["poster"] == who).sum()) if len(s) else 0
            for cls in ("telegram_bot", "official", "exchange", "trading_tool", "shortener", "unknown"):
                row[f"n_invites_to_{cls}"] = (int(s["classes"].map(lambda c: cls in c).sum())
                                             if len(s) else 0)
            chat_rows.append(row)
            p[f"{side}_invite_share"] = row["invite_share"]
            p[f"{side}_hallmark_share"] = row["n_hallmark"] / n if n else float("nan")
            p[f"{side}_unknown_share"] = row["n_invites_to_unknown"] / n if n else float("nan")
        p["diff_invite_share"] = p["group_invite_share"] - p["channel_invite_share"]
        pair_rows.append(p)
    return (pd.concat([i for i in invites if len(i)], ignore_index=True),
            pd.DataFrame(chat_rows), pd.DataFrame(pair_rows))


def domain_table(invites: pd.DataFrame) -> pd.DataFrame:
    """One row per (topic, target domain): counts, class, where and by whom it is posted."""
    e = invites.explode(["targets", "target_classes"]).rename(
        columns={"targets": "domain", "target_classes": "class"})
    e = e[e["domain"].notna()]
    g = e.groupby(["topic", "domain"]).agg(
        n_invites=("msg_id", "size"), n_pairs=("pair_id", "nunique"),
        n_pairs_official=("class", lambda x: 0),  # filled below
        group_share=("side", lambda x: round((x == "group").mean(), 3)),
        bot_share=("poster", lambda x: round(x.isin(["bot", "other_channel"]).mean(), 3)),
        hallmark_share=("hallmark", lambda x: round(x.mean(), 3)),
        cls=("class", lambda x: x.mode().iloc[0]),
    ).reset_index().rename(columns={"cls": "class"})
    off = e[e["class"] == "official"].groupby(["topic", "domain"])["pair_id"].nunique()
    g["n_pairs_official"] = [int(off.get((t, d), 0)) for t, d in zip(g["topic"], g["domain"])]
    # a domain that is official in one pair is not "unknown" elsewhere: it is a project's site
    g.loc[(g["class"] == "unknown") & (g["n_pairs_official"] > 0), "class"] = "official"
    return g.sort_values(["topic", "n_invites"], ascending=[True, False])
