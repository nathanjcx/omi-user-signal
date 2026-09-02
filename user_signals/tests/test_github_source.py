"""Regression test: `gh api` defaults to POST once any -f/-F flag is
present (its normal behavior is GET only with zero field flags), which
turned the issues *list* query into an attempted issue-*creation* POST
("title" wasn't supplied, HTTP 422) the first time this pipeline ran
against the live repo. fetch() must always pass -X GET explicitly whenever
it passes -f flags."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from user_signals import sources_github  # noqa: E402


class GithubFetchMethodTest(unittest.TestCase):
    def test_fetch_forces_get_before_any_field_flags(self):
        with patch.object(sources_github, "_run_gh", return_value=[]) as mock_run:
            sources_github.fetch("BasedHardware/omi", cap=10)

        args = mock_run.call_args[0][0]
        self.assertIn("-X", args)
        x_index = args.index("-X")
        self.assertEqual(args[x_index + 1], "GET")

        f_indices = [i for i, a in enumerate(args) if a == "-f"]
        self.assertTrue(f_indices, "expected at least one -f flag in the fixture")
        self.assertTrue(all(i > x_index for i in f_indices), "-X GET must precede every -f flag")


if __name__ == "__main__":
    unittest.main()
