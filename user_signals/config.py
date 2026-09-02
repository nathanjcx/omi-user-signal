"""Runtime configuration for the user-signal pipeline, sourced from env vars
so the same code runs unchanged locally and in the scheduled workflow
(.github/workflows/user-signal-report.yml). See README.md for the full list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass(frozen=True)
class Config:
    github_repo: str = field(default_factory=lambda: os.environ.get("USER_SIGNALS_GITHUB_REPO", "BasedHardware/omi"))
    appstore_app_id: str = field(default_factory=lambda: os.environ.get("USER_SIGNALS_APPSTORE_ID", "6502156163"))
    playstore_package_id: str = field(
        default_factory=lambda: os.environ.get("USER_SIGNALS_PLAYSTORE_ID", "com.friend.ios")
    )
    lookback_days: int = field(default_factory=lambda: _int_env("USER_SIGNALS_LOOKBACK_DAYS", 30))
    github_issue_cap: int = field(default_factory=lambda: _int_env("USER_SIGNALS_GITHUB_ISSUE_CAP", 300))
    review_cap_per_store: int = field(default_factory=lambda: _int_env("USER_SIGNALS_REVIEW_CAP", 200))
    top_n: int = field(default_factory=lambda: _int_env("USER_SIGNALS_TOP_N", 5))
    out_dir: str = field(default_factory=lambda: os.environ.get("USER_SIGNALS_OUT_DIR", "out"))
