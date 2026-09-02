"""Entry point: fetch -> classify -> score -> report.

Run via `bin/user-signal-report` from the repo root, or directly:
    python3 -m user_signals.cli --top 5 --lookback-days 30
(with the repo root on PYTHONPATH — the wrapper script handles that for you.)
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import sources_appstore, sources_github, sources_playstore
from .classify import THEMES, classify
from .config import Config
from .models import Signal, ThemeResult
from .report import render_html, render_markdown
from .score import score_theme

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def fetch_all(config: Config) -> dict[str, list[Signal]]:
    results: dict[str, list[Signal]] = {
        "github": sources_github.fetch(config.github_repo, config.github_issue_cap),
        "appstore": sources_appstore.fetch(config.appstore_app_id, config.review_cap_per_store),
        "playstore": sources_playstore.fetch(config.playstore_package_id, config.review_cap_per_store),
    }
    for name, signals in results.items():
        logger.info("%s: %d signals", name, len(signals))
    return results


def build_themes(signals: list[Signal], lookback_days: int) -> list[ThemeResult]:
    grouped: dict[str, list[Signal]] = defaultdict(list)
    for signal in signals:
        for theme_def in classify(signal):
            grouped[theme_def.name].append(signal)
    by_name = {t.name: t for t in THEMES}
    results = [score_theme(by_name[name], sigs, lookback_days) for name, sigs in grouped.items() if sigs]
    results.sort(key=lambda t: t.score, reverse=True)
    return results


def recent_signals(signals: list[Signal], lookback_days: int, limit: int = 15) -> list[Signal]:
    now = datetime.now(timezone.utc)
    recent = [s for s in signals if (now - s.created_at).days <= lookback_days]
    recent.sort(key=lambda s: s.created_at, reverse=True)
    return recent[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=None, help="Number of priority themes to report")
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--out-dir", type=str, default=None)
    args = parser.parse_args(argv)

    config = Config()
    top_n = args.top or config.top_n
    lookback_days = args.lookback_days or config.lookback_days
    out_dir = Path(args.out_dir or config.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    by_source = fetch_all(config)
    all_signals = [s for sigs in by_source.values() for s in sigs]

    if not all_signals:
        logger.error("No signals fetched from any source — check network/auth (gh auth status) and try again.")
        return 1

    themes = build_themes(all_signals, lookback_days)
    top_themes = themes[:top_n]
    recent = recent_signals(all_signals, lookback_days)

    meta = {
        "generated_at": datetime.now(timezone.utc),
        "lookback_days": lookback_days,
        "source_counts": {k: len(v) for k, v in by_source.items()},
        "repo": config.github_repo,
    }

    stamp = meta["generated_at"].strftime("%Y-%m-%d")
    md_path = out_dir / f"user-signal-report-{stamp}.md"
    html_path = out_dir / f"user-signal-report-{stamp}.html"
    md_path.write_text(render_markdown(top_themes, recent, meta), encoding="utf-8")
    html_path.write_text(render_html(top_themes, recent, meta), encoding="utf-8")

    print(f"\nWrote {md_path}")
    print(f"Wrote {html_path}\n")
    print(f"Top {len(top_themes)} priority themes:")
    for i, theme in enumerate(top_themes, start=1):
        print(
            f"  {i}. [{theme.band}] {theme.name} — score {theme.score:.0f}, "
            f"{len(theme.signals)} signals across {len(theme.source_counts)} source(s)"
        )
    if not top_themes:
        print("  (no themes matched any fetched signal — see per-source counts above)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
