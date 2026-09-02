"""Google Play review source.

Uses the `google-play-scraper` PyPI package (see requirements.txt),
which reads the same public review data the Play Store app itself
displays — no auth. Install it into whichever Python you run this with:
    pip install -r requirements.txt
"""

from __future__ import annotations

import logging
from datetime import timezone

from .models import Signal

logger = logging.getLogger(__name__)


def parse_entry(entry: dict, package_id: str) -> Signal | None:
    """Turn one raw google-play-scraper review dict into a Signal."""
    try:
        review_id = entry["reviewId"]
        body = entry.get("content") or ""
        rating = int(entry["score"])
        created_at = entry["at"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        engagement = int(entry.get("thumbsUpCount") or 0)
        author = entry.get("userName")
    except (KeyError, TypeError, ValueError):
        return None
    title = (body[:80] + "…") if len(body) > 80 else body
    return Signal(
        source="playstore",
        id=str(review_id),
        title=title or "(no review text)",
        body=body,
        url=f"https://play.google.com/store/apps/details?id={package_id}",
        created_at=created_at,
        rating=rating,
        engagement=engagement,
        author=author,
    )


def fetch(package_id: str, cap: int) -> list[Signal]:
    try:
        from google_play_scraper import Sort, reviews
    except ImportError:
        logger.warning(
            "google-play-scraper not installed — skipping Play Store. "
            "Run: pip install -r requirements.txt"
        )
        return []

    try:
        raw, _ = reviews(package_id, lang="en", country="us", sort=Sort.NEWEST, count=cap)
    except Exception as exc:  # library raises broadly on network/parse failure
        logger.warning("Play Store fetch failed: %s", exc)
        return []

    signals: list[Signal] = []
    for entry in raw:
        sig = parse_entry(entry, package_id)
        if sig is not None:
            signals.append(sig)
    return signals
