"""Implements the Priority Score formula from ISSUE_TRIAGE_GUIDE.MD section
5, applied to an aggregated theme instead of a single hand-triaged issue:

    Priority Score = (Core Layer Weight * Failure Severity)
                      + Trust Impact + Frequency + Maintenance Leverage
                      - Cost & Risk

The five inputs there are meant to be a maintainer's judgment call per
issue. Here they're estimated from signal statistics instead — this is an
automated *approximation* of the manual rubric, not a replacement for it.
Treat P0/P1 output as "a maintainer should look at this," not a verdict.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .classify import LAYER_WEIGHTS, ThemeDef, has_severity_signal
from .models import Signal, ThemeResult

# App Store and Play Store reviews are direct, unfiltered end-user signal —
# every entry is a real person hitting a real problem. GitHub's open-issues
# list mixes that same kind of report with internal engineering/CI/process
# tickets that never reach an end user (release guards, formatting checks,
# refactors), so it's weighted down relative to the stores rather than
# counted 1:1. Tune here if the mix should shift; "discord" is a placeholder
# for when that source lands (see README.md).
SOURCE_WEIGHT: dict[str, float] = {
    "appstore": 1.5,
    "playstore": 1.5,
    "github": 0.5,
    "discord": 1.0,
}


def _weight(signal: Signal) -> float:
    return SOURCE_WEIGHT.get(signal.source, 1.0)


def _failure_severity(signals: list[Signal]) -> int:
    """5 if most (source-weighted) signal carries a severity keyword or a
    <=2-star rating, scaling down from there. A low store rating is the
    strongest unambiguous severity signal available without a human
    reading every review, so it's weighted equally with the keyword
    match — source weighting is applied on top of that, not instead."""
    if not signals:
        return 1
    total = sum(_weight(s) for s in signals)
    bad = sum(
        _weight(s) for s in signals if has_severity_signal(s) or (s.rating is not None and s.rating <= 2)
    )
    ratio = bad / total if total else 0
    if ratio >= 0.6:
        return 5
    if ratio >= 0.4:
        return 4
    if ratio >= 0.2:
        return 3
    if ratio > 0:
        return 2
    return 1


def _trust_impact(signals: list[Signal]) -> int:
    """5 if any signal reads as data loss / privacy; otherwise tracks
    severity one band down, since most complaints that aren't explicit
    data-loss language still erode trust roughly proportionally."""
    if any(has_severity_signal(s) for s in signals):
        return 5
    return max(1, _failure_severity(signals) - 1)


def _frequency(signals: list[Signal], lookback_days: int) -> int:
    """Source-weighted volume within the lookback window, bucketed rather
    than linear so one viral thread doesn't read as "happens daily" on its
    own. This is the input SOURCE_WEIGHT affects most visibly: ten GitHub
    issues and ten App Store reviews land in different buckets."""
    now = datetime.now(timezone.utc)
    recent = [s for s in signals if (now - s.created_at).days <= lookback_days]
    n = sum(_weight(s) for s in recent)
    if n >= 15:
        return 5
    if n >= 8:
        return 4
    if n >= 4:
        return 3
    if n > 0:
        return 2
    return 1


def _maintenance_leverage(signals: list[Signal]) -> int:
    """Cross-source corroboration is the leverage signal available
    automatically: a theme independent sources agree on is more likely a
    systemic fix (eliminates a class of bugs) than a one-off complaint."""
    sources = {s.source for s in signals}
    if len(sources) >= 3:
        return 5
    if len(sources) == 2:
        return 4
    return 3


def _cost_risk(layer: str) -> int:
    """No automated signal for engineering cost/rollout risk exists, so
    this uses the Core Layer as a coarse proxy: capture/memory bugs tend to
    span firmware, BLE, and backend, while ux-polish/docs fixes are usually
    single-surface."""
    return {
        "capture": 4,
        "memory": 4,
        "understand": 3,
        "intelligence": 2,
        "retrieval-action": 2,
        "ux-polish": 2,
        "docs-tooling": 1,
    }.get(layer, 3)


def _band(score: float) -> str:
    """Thresholds verbatim from ISSUE_TRIAGE_GUIDE.MD section 6."""
    if score >= 30:
        return "P0"
    if score >= 22:
        return "P1"
    if score >= 14:
        return "P2"
    return "P3"


def score_theme(theme_def: ThemeDef, signals: list[Signal], lookback_days: int) -> ThemeResult:
    severity = _failure_severity(signals)
    trust = _trust_impact(signals)
    frequency = _frequency(signals, lookback_days)
    leverage = _maintenance_leverage(signals)
    cost = _cost_risk(theme_def.layer)
    weight = LAYER_WEIGHTS[theme_def.layer]
    score = (weight * severity) + trust + frequency + leverage - cost
    return ThemeResult(
        name=theme_def.name,
        layer=theme_def.layer,
        layer_weight=weight,
        signals=sorted(signals, key=lambda s: s.created_at, reverse=True),
        failure_severity=severity,
        trust_impact=trust,
        frequency=frequency,
        maintenance_leverage=leverage,
        cost_risk=cost,
        score=score,
        band=_band(score),
    )
