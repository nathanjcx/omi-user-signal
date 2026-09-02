"""Groups Signals into named themes and maps each theme to a Core Layer,
using the same layer taxonomy as ../ISSUE_TRIAGE_GUIDE.MD (repo root) so
this pipeline's output speaks the same language as manual issue triage.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Signal

# Layer weights, verbatim from ISSUE_TRIAGE_GUIDE.MD section 3.
LAYER_WEIGHTS: dict[str, int] = {
    "capture": 5,
    "understand": 4,
    "memory": 4,
    "intelligence": 3,
    "retrieval-action": 3,
    "ux-polish": 1,
    "docs-tooling": 1,
}


@dataclass(frozen=True)
class ThemeDef:
    name: str
    layer: str
    keywords: tuple[str, ...]


# Keyword matching is intentionally simple (substring, case-insensitive):
# it's auditable and fast, and every theme here is a real recurring
# complaint identified in a prior cross-source review (see README.md for
# the source audit this taxonomy is built from). Extend it as new
# recurring themes emerge — don't build a generic keyword-learning system
# for a report that runs a few times a week.
THEMES: tuple[ThemeDef, ...] = (
    ThemeDef(
        "Bluetooth / connectivity",
        "capture",
        ("bluetooth", " ble ", "disconnect", "pairing", "won't connect", "can't connect", "connection drop"),
    ),
    ThemeDef(
        "Battery & power",
        "capture",
        ("battery", "charging", "charge", "power drain", "won't turn on", "won't power off", "drains"),
    ),
    ThemeDef(
        "Recording / capture reliability",
        "capture",
        ("recording failed", "didn't record", "no offline backup", "recording stopped", "capture failed",
         "nothing was captured", "wasn't recorded"),
    ),
    ThemeDef(
        "Transcription accuracy",
        "understand",
        ("transcription", "transcript", "mishear", "inaccurate", "mistranscri"),
    ),
    ThemeDef(
        "Speaker ID / diarization",
        "understand",
        ("speaker", "diariz", "voice profile", "misidentif"),
    ),
    ThemeDef(
        "Sync & data integrity",
        "memory",
        ("sync", "data loss", "lost my", "disappeared", "won't save", "not saving", "deleted my", "missing conversation"),
    ),
    ThemeDef(
        "Account / privacy / deletion",
        "memory",
        ("account deletion", "delete my account", "gdpr", "my data", "privacy"),
    ),
    ThemeDef(
        "Search & retrieval (Ask Omi)",
        "retrieval-action",
        ("ask omi", "can't find", "search doesn't", "not searchable", "chat can't", "chat hallucinat"),
    ),
    ThemeDef(
        "Integrations (Notion, Calendar, etc.)",
        "retrieval-action",
        ("notion", "calendar integration", "oauth", "integration", "spotify", "zapier"),
    ),
    ThemeDef(
        "Notifications",
        "retrieval-action",
        ("notification", "push alert", "too many notifications"),
    ),
    ThemeDef(
        "Subscription / billing",
        "intelligence",
        ("subscription", "billing", "charged", "refund", "paywall", "pricing"),
    ),
    ThemeDef(
        "Onboarding & setup",
        "ux-polish",
        ("onboarding", "setup", "set up", "getting started", "instructions"),
    ),
    ThemeDef(
        "App stability / crashes",
        "ux-polish",
        ("crash", "freeze", "frozen", "won't open", "force close"),
    ),
)

# Presence of any of these near-verbatim phrases marks a signal as a strong
# severity/trust signal regardless of source (see score.py).
SEVERITY_KEYWORDS: tuple[str, ...] = (
    "data loss", "lost my", "disappeared", "no recovery", "never deleted",
    "no warning", "silently", "gone", "wiped", "no transcript", "nothing was captured",
)


def classify(signal: Signal) -> list[ThemeDef]:
    """A signal may match more than one theme (e.g. a post about a lost
    recording legitimately belongs to both "Recording / capture reliability"
    and "Sync & data integrity") — that's intentional, not deduplicated."""
    text = f"{signal.title} {signal.body}".lower()
    return [t for t in THEMES if any(kw in text for kw in t.keywords)]


def has_severity_signal(signal: Signal) -> bool:
    text = f"{signal.title} {signal.body}".lower()
    return any(kw in text for kw in SEVERITY_KEYWORDS)
