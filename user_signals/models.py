"""Shared data model for the user-signal pipeline.

A Signal is one normalized piece of user feedback (a GitHub issue, an App
Store review, a Play Store review, ...). Everything downstream — theme
classification, scoring, reporting — operates on Signal, never on a
source's raw payload, so a new source only has to implement one function:
fetch(...) -> list[Signal] (see sources_github.py for the shape to match).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Signal:
    source: str  # "github" | "appstore" | "playstore" | "discord" (future)
    id: str
    title: str
    body: str
    url: str
    created_at: datetime
    rating: int | None = None  # 1-5 stars; review sources only
    engagement: int = 0  # comments + reactions, or thumbs-up count
    author: str | None = None


@dataclass
class ThemeResult:
    name: str
    layer: str
    layer_weight: int
    signals: list[Signal]
    failure_severity: int
    trust_impact: int
    frequency: int
    maintenance_leverage: int
    cost_risk: int
    score: float
    band: str  # "P0".."P3", per ISSUE_TRIAGE_GUIDE.MD section 6

    @property
    def source_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.signals:
            counts[s.source] = counts.get(s.source, 0) + 1
        return counts
