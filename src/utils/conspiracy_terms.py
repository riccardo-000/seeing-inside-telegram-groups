"""Keywords that mark a channel as conspiracy-themed (title + description).

Used to rank the conspiracy audit queue (scripts/audit_channels.py) and to help
the manual check of pairs (scripts/select_pairs.py). A hit is a hint, not a
label: the final call on the topic is made by hand. Decision 2026-10-20 in
memory/decisions.md.
"""

from __future__ import annotations

import re

TERMS = {
    # QAnon / "awakening" movement
    "qanon": r"\bq\s?anon|\bwwg1wga|\bwwg1|\bq\s?drops?\b|\bq\s?posts?\b|\bq\s?army|\bthe\s?storm\b",
    "awakening": r"great\s?awakening|\bawake(ning)?\b|wake\s?up|red\s?pill|\bsheeple\b|\bpatriots?\b|\bdigital soldiers?",
    "deep_state": r"deep\s?state|\bcabal\b|\bglobalists?\b|\bnwo\b|new\s?world\s?order|great\s?reset|agenda\s?20(30|21)|"
                  r"illuminati|freemason|khazar|\bzionist|jew(ish)?\s?world\s?order|\bkalergi\b|great\s?replacement",
    "truth": r"\btruth(ers?)?\b|\bdisclosure\b|\bexposed?\b|\bcensored\b|\buncensored\b|they\s?don.?t\s?want|"
             r"mainstream\s?media|\bmsm\b|\bpsyops?\b|false\s?flag",
    "covid_health": r"plandemic|scamdemic|\bvaxx?\b|vaccin|\bjab\b|died\s?suddenly|mrna|\bcovid|\bpfizer|"
                    r"\b5g\b|chemtrails?|fluorid|\bgeoengineering|depopulation|bill\s?gates",
    "esoteric_ufo": r"\bufos?\b|\buap\b|aliens?\b|galactic|ascension|starseed|\bpleiad|anunnaki|tartari|mud\s?flood|"
                    r"flat\s?earth|hollow\s?earth|adrenochrome|reptilian|\bqfs\b|quantum\s?financial|\bnesara|gesara|med\s?beds?",
    "sovereign": r"sovereign\s?citizen|freedom\s?fighters?|\bconvoy\b|\bplandemie|lockdown",
    # other languages (DE, IT, ES, FR, RU)
    "other_lang": r"wahrheit|aufwachen|impf|plandemie|querdenk|reichsbürger|verschwörung|"
                  r"verità|svegli|complott|vaccin|"
                  r"verdad|despierta|conspira|plandemia|"
                  r"vérité|réveil|complot|"
                  r"правд|заговор|пробужд",
}
_RE = {k: re.compile(v, re.I) for k, v in TERMS.items()}


def conspiracy_hits(*texts: str) -> list[str]:
    """Names of the keyword families found in the given texts (empty list if none)."""
    text = " ".join(t for t in texts if t)
    return [k for k, r in _RE.items() if r.search(text)]
