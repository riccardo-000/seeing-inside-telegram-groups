"""Daily username-resolve budget shared by every script on this machine.

Telegram rate-limits ``contacts.ResolveUsername`` per account; on 2026-09-29
~250-300 resolves in one day triggered a 19 h FloodWait (see
``memory/decisions.md``). Every script that resolves an uncached @username
must call :meth:`ResolveBudget.take` first. Usage is appended to
``data/interim/resolve_ledger.csv`` (committed with the collection log, so the
other machines can see what was used today).
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.utils.config import DATA_INTERIM

LEDGER = DATA_INTERIM / "resolve_ledger.csv"
DAILY_LIMIT = 100


class BudgetExceeded(Exception):
    pass


class ResolveBudget:
    """Counts username resolves per UTC day across all scripts.

    Args:
        script: Name written in the ledger (e.g. ``"audit_channels"``).
        daily_limit: Max resolves per UTC day for the whole account.
        ledger: CSV file with one row per resolve.
    """

    def __init__(self, script: str, daily_limit: int = DAILY_LIMIT, ledger: Path = LEDGER):
        self.script, self.daily_limit, self.ledger = script, daily_limit, ledger

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def used_today(self) -> int:
        if not self.ledger.exists():
            return 0
        with open(self.ledger, newline="", encoding="utf-8") as fh:
            return sum(1 for r in csv.DictReader(fh) if r["date"] == self._today())

    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used_today())

    def take(self, username: str = "") -> None:
        """Record one resolve, or raise :class:`BudgetExceeded` if the day is used up."""
        if self.used_today() >= self.daily_limit:
            raise BudgetExceeded(f"daily resolve budget ({self.daily_limit}) used up")
        new = not self.ledger.exists()
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["date", "time_utc", "script"])
            now = datetime.now(timezone.utc)
            # the username itself is not logged: it may belong to a person
            w.writerow([now.date().isoformat(), now.strftime("%H:%M:%S"), self.script])
