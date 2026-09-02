"""Hermetic tests for theme classification and severity-keyword detection."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from user_signals.classify import classify, has_severity_signal  # noqa: E402
from user_signals.models import Signal  # noqa: E402


def make_signal(title: str, body: str = "", **kwargs) -> Signal:
    defaults = dict(
        source="github",
        id="1",
        title=title,
        body=body,
        url="https://example.com",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return Signal(**defaults)


class ClassifyTest(unittest.TestCase):
    def test_bluetooth_theme_matches(self):
        signal = make_signal("Omi Loses Connection RIGHT NEXT TO MY IPHONE", "Bluetooth keeps dropping.")
        names = {t.name for t in classify(signal)}
        self.assertIn("Bluetooth / connectivity", names)

    def test_signal_can_match_multiple_themes(self):
        signal = make_signal(
            "Recording failed with no transcript",
            "The recording stopped and my conversation disappeared with no warning.",
        )
        names = {t.name for t in classify(signal)}
        self.assertIn("Recording / capture reliability", names)
        self.assertIn("Sync & data integrity", names)

    def test_unrelated_text_matches_nothing(self):
        signal = make_signal("Great app, love the marketplace", "Just wanted to say thanks!")
        self.assertEqual(classify(signal), [])

    def test_case_insensitive(self):
        signal = make_signal("SUBSCRIPTION is a scam", "")
        names = {t.name for t in classify(signal)}
        self.assertIn("Subscription / billing", names)


class SeverityKeywordTest(unittest.TestCase):
    def test_detects_data_loss_language(self):
        signal = make_signal("Lost my recording", "Two hours of conversation just disappeared, no warning.")
        self.assertTrue(has_severity_signal(signal))

    def test_neutral_text_is_not_severe(self):
        signal = make_signal("Feature request: dark mode", "Would love a dark theme option.")
        self.assertFalse(has_severity_signal(signal))


if __name__ == "__main__":
    unittest.main()
