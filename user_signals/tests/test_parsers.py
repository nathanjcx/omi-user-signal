"""Hermetic tests for the pure parse_entry() functions — no network, fixed
fixture dicts shaped like the real API/feed/scraper payloads."""

from __future__ import annotations

import sys
import unittest
from datetime import timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from user_signals import sources_appstore, sources_playstore  # noqa: E402


class AppStoreParserTest(unittest.TestCase):
    def test_parses_well_formed_review(self):
        entry = {
            "im:rating": {"label": "2"},
            "title": {"label": "Constant disconnects"},
            "content": {"label": "Loses BLE connection every few minutes."},
            "id": {"label": "1234567890"},
            "author": {"name": {"label": "frustrated_user"}},
            "updated": {"label": "2026-08-01T12:00:00-07:00"},
        }
        signal = sources_appstore.parse_entry(entry, app_id="6502156163")
        self.assertIsNotNone(signal)
        self.assertEqual(signal.source, "appstore")
        self.assertEqual(signal.rating, 2)
        self.assertEqual(signal.author, "frustrated_user")
        self.assertEqual(signal.created_at.tzinfo is not None, True)

    def test_skips_app_summary_object(self):
        # Page 1 entry[0] is the app's own metadata, not a review — no im:rating.
        entry = {"im:name": {"label": "Omi"}, "title": {"label": "Omi"}}
        self.assertIsNone(sources_appstore.parse_entry(entry, app_id="6502156163"))

    def test_skips_malformed_entry(self):
        self.assertIsNone(sources_appstore.parse_entry({"title": {"label": "x"}}, app_id="1"))


class PlayStoreParserTest(unittest.TestCase):
    def test_parses_well_formed_review(self):
        import datetime as dt

        entry = {
            "reviewId": "abc123",
            "content": "Battery drains so fast, unusable by afternoon.",
            "score": 1,
            "at": dt.datetime(2026, 8, 1, 9, 0, 0),
            "thumbsUpCount": 12,
            "userName": "AndroidUser42",
        }
        signal = sources_playstore.parse_entry(entry, package_id="com.friend.ios")
        self.assertIsNotNone(signal)
        self.assertEqual(signal.rating, 1)
        self.assertEqual(signal.engagement, 12)
        self.assertEqual(signal.created_at.tzinfo, timezone.utc)

    def test_skips_malformed_entry(self):
        self.assertIsNone(sources_playstore.parse_entry({"content": "x"}, package_id="p"))


if __name__ == "__main__":
    unittest.main()
