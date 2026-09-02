"""Apple App Store review source.

Uses Apple's public, unauthenticated customer-reviews RSS-as-JSON feed —
no API key needed. Apple caps this feed at 10 pages (~500 reviews) per
storefront, newest first, which is why fetch() stops there regardless of
`cap`.
"""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from .models import Signal

logger = logging.getLogger(__name__)

FEED_URL = "https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/json"
MAX_PAGES = 10


def parse_entry(entry: dict, app_id: str) -> Signal | None:
    """Turn one raw RSS feed entry into a Signal. Returns None for the
    page-1 app-summary object (which has no im:rating) or any malformed
    entry, rather than raising — a handful of bad rows shouldn't fail the
    whole fetch."""
    try:
        rating = int(entry["im:rating"]["label"])
        title = entry["title"]["label"]
        body = entry["content"]["label"]
        entry_id = entry["id"]["label"]
        author = entry.get("author", {}).get("name", {}).get("label")
        updated = entry["updated"]["label"]  # ISO 8601, e.g. 2026-08-30T12:00:00-07:00
        created_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None
    return Signal(
        source="appstore",
        id=str(entry_id),
        title=title,
        body=body,
        url=f"https://apps.apple.com/us/app/id{app_id}",
        created_at=created_at,
        rating=rating,
        engagement=0,
        author=author,
    )


def fetch(app_id: str, cap: int) -> list[Signal]:
    signals: list[Signal] = []
    for page in range(1, MAX_PAGES + 1):
        if len(signals) >= cap:
            break
        url = FEED_URL.format(page=page, app_id=app_id)
        try:
            resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("App Store fetch failed on page %s: %s", page, exc)
            break
        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break
        for raw in entries:
            sig = parse_entry(raw, app_id)
            if sig is not None:
                signals.append(sig)
    return signals[:cap]
