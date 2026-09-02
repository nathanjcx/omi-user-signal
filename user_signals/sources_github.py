"""GitHub issues source.

Shells out to the `gh` CLI rather than hand-rolling REST auth, so it works
identically in an interactive session (already `gh auth login`'d) and in
the scheduled workflow (Actions injects GH_TOKEN, which `gh` reads
automatically — see .github/workflows/user-signal-report.yml).
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime

from .models import Signal

logger = logging.getLogger(__name__)


def _run_gh(args: list[str]) -> list[dict]:
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("gh command failed to run (%s): %s", args, exc)
        return []
    if result.returncode != 0:
        logger.warning("gh command failed (%s): %s", args, result.stderr.strip())
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def parse_entry(entry: dict) -> Signal | None:
    """Turn one raw `gh api .../issues` entry into a Signal. The issues
    endpoint also returns pull requests (they carry a "pull_request" key) —
    those aren't user signal, so they're filtered here rather than upstream,
    keeping the fetch query itself simple."""
    if "pull_request" in entry:
        return None
    try:
        created_at = datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
        reactions = entry.get("reactions") or {}
        engagement = int(entry.get("comments", 0)) + int(reactions.get("total_count", 0))
        return Signal(
            source="github",
            id=str(entry["number"]),
            title=entry["title"],
            body=(entry.get("body") or "")[:2000],
            url=entry["html_url"],
            created_at=created_at,
            rating=None,
            engagement=engagement,
            author=(entry.get("user") or {}).get("login"),
        )
    except (KeyError, TypeError, ValueError):
        return None


def fetch(repo: str, cap: int) -> list[Signal]:
    raw = _run_gh(
        [
            "api",
            f"repos/{repo}/issues",
            "--paginate",
            "-X",
            "GET",  # gh api defaults to POST once any -f is present; issues POST means "create issue"
            "-f",
            "state=open",
            "-f",
            "per_page=100",
            "-f",
            "sort=created",
            "-f",
            "direction=desc",
        ]
    )
    signals: list[Signal] = []
    for entry in raw[:cap]:
        sig = parse_entry(entry)
        if sig is not None:
            signals.append(sig)
    return signals
