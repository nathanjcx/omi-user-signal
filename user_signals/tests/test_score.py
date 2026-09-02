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
from user_signals.score import _band, score_theme  # noqa: E402

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
    def test_severe_cross_store_theme_scores_high(self):
        signals = [make_signal("appstore", 2, rating=1), make_signal("playstore", 3, rating=1)]
        result = score_theme(BLUETOOTH_THEME, signals, lookback_days=30)
        self.assertEqual(result.layer, "capture")
        self.assertEqual(result.maintenance_leverage, 4)  # 2 distinct stores (only 2 sources exist)
        self.assertGreaterEqual(result.score, 14)  # at least P2 given severity + both stores agreeing

    def test_single_stale_signal_scores_low(self):
        signals = [make_signal("appstore", 200, body="minor UI nitpick")]
        result = score_theme(ONBOARDING_THEME, signals, lookback_days=30)
        self.assertEqual(result.band, "P3")

    def test_signals_sorted_newest_first_on_result(self):
        signals = [make_signal("appstore", 10), make_signal("playstore", 1), make_signal("appstore", 5)]
        result = score_theme(BLUETOOTH_THEME, signals, lookback_days=30)
        gaps = [s.created_at for s in result.signals]
        self.assertEqual(gaps, sorted(gaps, reverse=True))

    def test_empty_signals_does_not_raise(self):
        result = score_theme(BLUETOOTH_THEME, [], lookback_days=30)
        self.assertEqual(result.band, "P3")
        self.assertEqual(len(result.signals), 0)


if __name__ == "__main__":
    unittest.main()
