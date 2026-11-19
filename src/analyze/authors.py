"""Point 6 of docs/analysis-plan.md: the three voices (channel, admins in the group, users).

Roles and voices come from ``load.py`` (README "Roles"). For every pair and every voice this
module computes per-message rates that need no model: share of messages with a link /
forwarded / with media, and the invitation measures of point 5a (detector of ``invites.py``):
invitations, invitations with a fraud hallmark, invitations to an ``unknown`` domain.
Bots and "other channel" senders are not a voice; their counts are kept for context.

Paired comparison (plan point 6): a group enters only if its admin list is visible, admins
wrote >= ``min_admin`` messages in the window (30; 10 and 50 as sensitivity) and users >= 1.
Per pair: user − admin and admin − channel.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.analyze.invites import pair_invites
from src.analyze.load import iter_pairs, read_admins

VOICES = ("channel", "admin", "user")
EXTRA = ("bot", "other_channel")
MEASURES = ("link_share", "forward_share", "media_share",
            "invite_share", "hallmark_invite_share", "unknown_invite_share")


def _has_list(x) -> bool:
    return isinstance(x, list) and len(x) > 0


def pair_voices(pair: pd.Series, df: pd.DataFrame) -> list[dict]:
    """One row per voice (plus bot / other_channel) of one pair."""
    w = df[df["in_window"] & ~df["role"].isin(["service", "channel_copy"])].copy()
    inv = pair_invites(pair, df)
    key = (["side", "msg_id"])
    if len(inv):
        flags = inv.assign(
            unknown=inv["classes"].map(lambda c: "unknown" in c))[key + ["hallmark", "unknown"]]
        flags["invite"] = True
        w = w.merge(flags, on=key, how="left")
    else:
        w["invite"] = w["hallmark"] = w["unknown"] = np.nan
    w["invite"] = w["invite"].fillna(False).astype(bool)
    w["hallmark"] = w["hallmark"].fillna(False).astype(bool) & w["invite"]
    w["unknown"] = w["unknown"].fillna(False).astype(bool) & w["invite"]
    w["who"] = w["voice"].where(w["voice"].notna(), w["role"])
    admins_listed = len(read_admins(pair["group_file"]))
    rows = []
    for who in VOICES + EXTRA:
        s = w[w["who"] == who]
        n = len(s)
        r = {"topic": pair["topic"], "pair_id": pair["pair_id"], "voice": who,
             "side": "channel" if who == "channel" else "group", "n_messages": n,
             "n_invites": int(s["invite"].sum()), "admins_listed": admins_listed}
        if n:
            r.update({
                "link_share": s["urls"].map(_has_list).mean(),
                "forward_share": s["is_forward"].astype(bool).mean(),
                "media_share": s["media"].notna().mean(),
                "invite_share": s["invite"].mean(),
                "hallmark_invite_share": s["hallmark"].mean(),
                "unknown_invite_share": s["unknown"].mean(),
            })
        else:
            r.update({m: float("nan") for m in MEASURES})
        rows.append(r)
    return rows


def compute(topic: str | None = None) -> pd.DataFrame:
    """Voice table (one row per pair × voice) for ``topic`` (both arms if None)."""
    rows = []
    for pair, df in iter_pairs(topic, text=True):
        rows += pair_voices(pair, df)
    return pd.DataFrame(rows)


def pair_table(voices: pd.DataFrame) -> pd.DataFrame:
    """One row per pair: measures per voice side by side, eligibility, differences."""
    v = voices[voices["voice"].isin(VOICES)]
    wide = v.pivot(index=["topic", "pair_id"], columns="voice",
                   values=["n_messages", *MEASURES])
    wide.columns = [f"{voice}_{m}" for m, voice in wide.columns]
    wide = wide.reset_index()
    listed = voices.groupby("pair_id")["admins_listed"].first()
    wide["admins_listed"] = wide["pair_id"].map(listed)
    for k in (10, 30, 50):
        wide[f"eligible_{k}"] = ((wide["admins_listed"] > 0) & (wide["admin_n_messages"] >= k)
                                 & (wide["user_n_messages"] >= 1))
    for m in MEASURES:
        wide[f"diff_user_admin_{m}"] = wide[f"user_{m}"] - wide[f"admin_{m}"]
        wide[f"diff_admin_channel_{m}"] = wide[f"admin_{m}"] - wide[f"channel_{m}"]
    return wide


def sign_test(d: pd.Series) -> tuple[int, int, int, float]:
    """(positive, negative, zero, two-sided exact sign-test p) of paired differences."""
    d = d.dropna()
    pos, neg = int((d > 0).sum()), int((d < 0).sum())
    n, k = pos + neg, min(pos, neg)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else float("nan")
    return pos, neg, int((d == 0).sum()), p


def boot_median_ci(d: pd.Series, reps: int = 20000, seed: int = 42) -> tuple[float, float]:
    """95% percentile bootstrap interval of the median (pairs resampled)."""
    x = d.dropna().to_numpy()
    if len(x) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    meds = np.median(rng.choice(x, size=(reps, len(x)), replace=True), axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def summary(pairs: pd.DataFrame) -> pd.DataFrame:
    """Per topic, threshold, measure and contrast: n, medians, sign test, bootstrap CI."""
    rows = []
    for topic, t in pairs.groupby("topic"):
        for k in (10, 30, 50):
            e = t[t[f"eligible_{k}"]]
            for m in MEASURES:
                for contrast in ("user_admin", "admin_channel"):
                    d = e[f"diff_{contrast}_{m}"]
                    pos, neg, zero, p = sign_test(d)
                    lo, hi = boot_median_ci(d)
                    rows.append({
                        "topic": topic, "min_admin": k, "measure": m, "contrast": contrast,
                        "n_pairs": int(d.notna().sum()),
                        "median_channel": e[f"channel_{m}"].median(),
                        "median_admin": e[f"admin_{m}"].median(),
                        "median_user": e[f"user_{m}"].median(),
                        "median_diff": d.median(), "ci_low": lo, "ci_high": hi,
                        "n_pos": pos, "n_neg": neg, "n_zero": zero, "sign_p": p,
                    })
    return pd.DataFrame(rows)
