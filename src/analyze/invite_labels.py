"""Point 5a, second half: merge the hand labels and compute the final invitation results.

Inputs (``data/interim/invites/``): ``domains_to_label.csv`` (label_a / label_b / label_final),
``validation_a.csv`` / ``validation_b.csv`` (is_invitation, suspicious), ``validation_key.csv``,
and ``validation_final.csv`` (written here: the items where the two annotators disagree, for a
third person to settle).

Rules
- Domain label: ``label_final`` if filled, else the common label when ``label_a == label_b``,
  else unresolved. Labels: ``suspicious`` / ``legit`` / ``unclear``.
- Suspicious invitation: it has a fraud hallmark, or one of its targets is labelled
  ``suspicious``. **Unresolved** = not suspicious, but it points to an ``unknown`` domain whose
  label is missing, ``unclear`` or disputed. Results are given as a range: ``low`` counts
  unresolved as not suspicious, ``high`` counts them as suspicious.
- Validation reference: the common answer of the two annotators, else the third person's
  (``validation_final.csv``); items still disputed are left out and counted.
- Detector precision / recall are estimated from the three strata of the sample, weighted by
  the size of each part of the pool (detected / link not detected / no link).
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from src.analyze.invites import HALLMARK, message_invite
from src.analyze.structure import fragment_map
from src.utils.config import DATA_INTERIM

LABEL_DIR = DATA_INTERIM / "invites"
DOMAIN_LABELS = ("suspicious", "legit", "unclear")


def _clean(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.lower()


def cohen_kappa(a: pd.Series, b: pd.Series) -> dict:
    """Cohen's kappa on the items both annotators filled."""
    a, b = _clean(a), _clean(b)
    both = (a != "") & (b != "")
    a, b = a[both], b[both]
    n = len(a)
    if n == 0:
        return {"n": 0, "agreement": math.nan, "kappa": math.nan}
    po = float((a == b).mean())
    cats = set(a) | set(b)
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    kappa = (po - pe) / (1 - pe) if pe < 1 else math.nan
    return {"n": n, "agreement": round(po, 3), "kappa": round(kappa, 3) if not math.isnan(kappa) else kappa}


# --- domains -----------------------------------------------------------------------------
def domain_labels(label_dir: Path = LABEL_DIR) -> tuple[pd.DataFrame, dict]:
    """Final label per hand-labelled domain, and the agreement figures."""
    d = pd.read_csv(label_dir / "domains_to_label.csv", dtype=str)
    a, b, f = _clean(d["label_a"]), _clean(d["label_b"]), _clean(d["label_final"])
    bad = sorted((set(a[a != ""]) | set(b[b != ""]) | set(f[f != ""])) - set(DOMAIN_LABELS))
    if bad:
        raise ValueError(f"unknown domain labels {bad}: use {DOMAIN_LABELS}")
    final = f.where(f != "", a.where((a == b) & (a != ""), ""))
    d["final"] = final
    stats = {"domains": len(d), "labelled_a": int((a != "").sum()), "labelled_b": int((b != "").sum()),
             **{f"agree_{k}": v for k, v in cohen_kappa(a, b).items()},
             "disputed_unsettled": int(((a != "") & (b != "") & (a != b) & (f == "")).sum()),
             **{f"final_{lab}": int((final == lab).sum()) for lab in DOMAIN_LABELS},
             "final_missing": int((final == "").sum())}
    return d[["domain", "n_invites", "final"]], stats


def suspicious_status(targets: list[str], classes: list[str], hallmark: bool, labels: dict[str, str]) -> str:
    """``suspicious`` / ``unresolved`` / ``not_suspicious`` for one invitation."""
    if hallmark or any(labels.get(d) == "suspicious" for d in targets):
        return "suspicious"
    if any(c == "unknown" and labels.get(d, "") in ("", "unclear") for d, c in zip(targets, classes)):
        return "unresolved"
    return "not_suspicious"


def suspicious_tables(invites: pd.DataFrame, chats: pd.DataFrame, labels: dict[str, str]
                      ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-chat and per-pair suspicious counts and shares (low / high range)."""
    inv = invites.copy()
    inv["status"] = [suspicious_status(t, c, h, labels) for t, c, h in
                     zip(inv["targets"], inv["target_classes"], inv["hallmark"])]
    rows = []
    for _, c in chats.iterrows():
        s = inv[(inv["pair_id"] == c["pair_id"]) & (inv["side"] == c["side"])]
        n = c["n_messages"]
        low = int((s["status"] == "suspicious").sum())
        high = low + int((s["status"] == "unresolved").sum())
        row = {"topic": c["topic"], "pair_id": c["pair_id"], "side": c["side"], "chat": c["chat"],
               "n_messages": n, "n_invites": len(s), "n_suspicious_low": low, "n_suspicious_high": high,
               "suspicious_share_low": low / n if n else math.nan,
               "suspicious_share_high": high / n if n else math.nan}
        for who in ("channel", "admin", "user", "bot", "other_channel"):
            row[f"n_suspicious_low_by_{who}"] = int(((s["status"] == "suspicious") & (s["poster"] == who)).sum())
        rows.append(row)
    per_chat = pd.DataFrame(rows)
    per_pair = per_chat.pivot(index=["topic", "pair_id"], columns="side",
                              values=["suspicious_share_low", "suspicious_share_high"])
    per_pair.columns = [f"{side}_{m}" for m, side in per_pair.columns]
    per_pair = per_pair.reset_index()
    for m in ("suspicious_share_low", "suspicious_share_high"):
        per_pair[f"diff_{m}"] = per_pair[f"group_{m}"] - per_pair[f"channel_{m}"]
    return per_chat, per_pair


# --- validation --------------------------------------------------------------------------
def validation_reference(label_dir: Path = LABEL_DIR) -> tuple[pd.DataFrame, dict]:
    """Reference answers for the 150 items, agreement figures, and the disputes file."""
    key = pd.read_csv(label_dir / "validation_key.csv", dtype={"item": str})
    va = pd.read_csv(label_dir / "validation_a.csv", dtype=str)
    vb = pd.read_csv(label_dir / "validation_b.csv", dtype=str)
    v = key.merge(va[["item", "text", "is_invitation", "suspicious"]], on="item") \
           .merge(vb[["item", "is_invitation", "suspicious"]], on="item", suffixes=("_a", "_b"))
    final_path = label_dir / "validation_final.csv"
    old = (pd.read_csv(final_path, dtype=str).set_index("item")
           if final_path.exists() else pd.DataFrame(columns=["is_invitation_final", "suspicious_final"]))
    stats = {}
    disputes = pd.DataFrame({"item": v["item"], "text": v["text"]})
    for q in ("is_invitation", "suspicious"):
        a, b = _clean(v[f"{q}_a"]), _clean(v[f"{q}_b"])
        stats.update({f"{q}_{k}": val for k, val in cohen_kappa(a, b).items()})
        third = _clean(v["item"].map(old[f"{q}_final"]) if len(old) else pd.Series("", index=v.index))
        v[f"{q}_ref"] = a.where((a == b) & (a != ""), third)
        disputes[f"{q}_a"], disputes[f"{q}_b"] = a, b
        disputes[f"{q}_final"] = third
    is_dispute = ((disputes["is_invitation_a"] != disputes["is_invitation_b"]) |
                  (disputes["suspicious_a"] != disputes["suspicious_b"])) & \
                 (disputes["is_invitation_a"] != "") & (disputes["is_invitation_b"] != "")
    disputes[is_dispute].to_csv(final_path, index=False)  # keeps the third person's answers
    stats["disputed_items"] = int(is_dispute.sum())
    stats["items_with_reference"] = int((v["is_invitation_ref"] != "").sum())
    return v, stats


def detector_quality(v: pd.DataFrame, pool: pd.DataFrame) -> dict:
    """Precision and recall of the invitation detector, weighted by the pool strata.

    ``v`` must carry ``has_link`` (merged from the pool). Random items can fall in any part.
    """
    ref = v[v["is_invitation_ref"].isin(["yes", "no"])]
    if ref.empty:
        return {"note": "no reference answers yet"}
    sizes = {"D": int(pool["detected"].sum()),
             "L": int((pool["has_link"] & ~pool["detected"]).sum()),
             "N": int((~pool["has_link"]).sum())}
    part = ref.apply(lambda r: "D" if r["detected"] else ("L" if r["has_link"] else "N"), axis=1)
    yes = ref["is_invitation_ref"] == "yes"
    p = {k: (float(yes[part == k].mean()) if (part == k).any() else math.nan) for k in sizes}
    n = {k: int((part == k).sum()) for k in sizes}
    true_d = sizes["D"] * (p["D"] if not math.isnan(p["D"]) else 0)
    missed_l = sizes["L"] * (p["L"] if not math.isnan(p["L"]) else 0)
    missed_n = sizes["N"] * (p["N"] if not math.isnan(p["N"]) else 0)
    return {"pool_sizes": sizes, "items_per_part": n,
            "invite_rate_per_part": {k: (round(x, 3) if not math.isnan(x) else None) for k, x in p.items()},
            "precision": round(p["D"], 3) if not math.isnan(p["D"]) else None,
            "recall_link_messages": round(true_d / (true_d + missed_l), 3) if true_d + missed_l else None,
            "recall_all_messages": (round(true_d / (true_d + missed_l + missed_n), 3)
                                    if true_d + missed_l + missed_n else None),
            "note": "recall_all_messages rests on the few random items without a link: wide uncertainty"}


def suspicious_quality(v: pd.DataFrame, labels: dict[str, str], domain_class: dict[str, str]) -> dict:
    """Automatic suspicious status vs the reference, on items the reference calls invitations.

    ``v`` must carry ``urls`` (merged from the pool: hidden links and buttons included).
    """
    ref = v[(v["is_invitation_ref"] == "yes") & v["suspicious_ref"].isin(["yes", "no"])]
    if ref.empty:
        return {"note": "no reference answers yet"}
    auto = []
    for urls, text in zip(ref["urls"], ref["text"]):
        _, targets = message_invite(urls, text)
        fix = fragment_map(targets)
        targets = sorted({fix.get(d, d) for d in targets})
        classes = [domain_class.get(d, "unknown") for d in targets]
        auto.append(suspicious_status(targets, classes, bool(HALLMARK.search(text or "")), labels))
    auto = pd.Series(auto, index=ref.index)
    gold = ref["suspicious_ref"] == "yes"
    out = {"n": len(ref), "reference_suspicious": int(gold.sum())}
    for mode, flag in (("low", auto == "suspicious"), ("high", auto.isin(["suspicious", "unresolved"]))):
        tp = int((flag & gold).sum())
        out[f"precision_{mode}"] = round(tp / flag.sum(), 3) if flag.sum() else None
        out[f"recall_{mode}"] = round(tp / gold.sum(), 3) if gold.sum() else None
    return out
