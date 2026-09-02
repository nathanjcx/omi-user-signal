"""Hermetic tests for score_theme() — verifies the ISSUE_TRIAGE_GUIDE.MD
formula and P0-P3 band thresholds are applied exactly as specified."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from user_signals.classify import THEMES  # noqa: E402
from user_signals.models import Signal  # noqa: E402
from user_signals.score import _band, _frequency, score_theme  # noqa: E402

BLUETOOTH_THEME = next(t for t in THEMES if t.name == "Bluetooth / connectivity")
ONBOARDING_THEME = next(t for t in THEMES if t.name == "Onboarding & setup")


def make_signal(source: str, days_ago: int, rating=None, body="disconnects constantly, no warning") -> Signal:
    return Signal(
        source=source,
        id=f"{source}-{days_ago}",
        title="Bluetooth disconnects",
        body=body,
        url="https://example.com",
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )


class BandThresholdTest(unittest.TestCase):
    def test_band_boundaries_match_guide(self):
        self.assertEqual(_band(30), "P0")
        self.assertEqual(_band(29.9), "P1")
        self.assertEqual(_band(22), "P1")
        self.assertEqual(_band(21.9), "P2")
        self.assertEqual(_band(14), "P2")
        self.assertEqual(_band(13.9), "P3")
        self.assertEqual(_band(0), "P3")


class ScoreThemeTest(unittest.TestCase):
    def test_severe_cross_source_theme_scores_high(self):
        signals = [make_signal("github", 1), make_signal("appstore", 2, rating=1), make_signal("playstore", 3, rating=1)]
        result = score_theme(BLUETOOTH_THEME, signals, lookback_days=30)
        self.assertEqual(result.layer, "capture")
        self.assertEqual(result.maintenance_leverage, 5)  # 3 distinct sources
        self.assertGreaterEqual(result.score, 14)  # at least P2 given severity + cross-source

    def test_single_stale_signal_scores_low(self):
        signals = [make_signal("github", 200, body="minor UI nitpick")]
        result = score_theme(ONBOARDING_THEME, signals, lookback_days=30)
        self.assertEqual(result.band, "P3")

    def test_signals_sorted_newest_first_on_result(self):
        signals = [make_signal("github", 10), make_signal("github", 1), make_signal("github", 5)]
        result = score_theme(BLUETOOTH_THEME, signals, lookback_days=30)
        gaps = [s.created_at for s in result.signals]
        self.assertEqual(gaps, sorted(gaps, reverse=True))

    def test_empty_signals_does_not_raise(self):
        result = score_theme(BLUETOOTH_THEME, [], lookback_days=30)
        self.assertEqual(result.band, "P3")
        self.assertEqual(len(result.signals), 0)


class SourceWeightingTest(unittest.TestCase):
    """App Store and Play Store reviews count for more than GitHub issues —
    per user direction, GitHub's issue list mixes real user bugs with
    internal engineering/CI tickets that never reach an end user."""

    def test_appstore_outweighs_equal_count_of_github(self):
        github_signals = [make_signal("github", d, body="") for d in range(10)]
        appstore_signals = [make_signal("appstore", d, body="") for d in range(10)]
        github_freq = _frequency(github_signals, lookback_days=30)
        appstore_freq = _frequency(appstore_signals, lookback_days=30)
        self.assertLess(github_freq, appstore_freq)

    def test_appstore_and_playstore_theme_outscores_same_size_github_only_theme(self):
        github_only = [make_signal("github", d, body="") for d in range(10)]
        stores_only = [make_signal("appstore", d, body="") for d in range(5)] + [
            make_signal("playstore", d, body="") for d in range(5)
        ]
        github_result = score_theme(BLUETOOTH_THEME, github_only, lookback_days=30)
        stores_result = score_theme(BLUETOOTH_THEME, stores_only, lookback_days=30)
        self.assertGreater(stores_result.score, github_result.score)


if __name__ == "__main__":
    unittest.main()
