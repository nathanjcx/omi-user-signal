"""Renders ThemeResult + recent Signal lists into a Markdown report and a
self-contained HTML report. Both take the same data; Markdown is the
diffable/git-friendly form, HTML is the shareable/readable form.
"""

from __future__ import annotations

import html as html_lib
from datetime import datetime

from .models import Signal, ThemeResult

SOURCE_LABELS = {"github": "GitHub", "appstore": "App Store", "playstore": "Google Play", "discord": "Discord"}


def _evidence_line(signal: Signal) -> str:
    bits = [SOURCE_LABELS.get(signal.source, signal.source)]
    if signal.rating is not None:
        bits.append(f"{signal.rating}★")
    if signal.engagement:
        bits.append(f"{signal.engagement} engagement")
    meta = ", ".join(bits)
    title = signal.title.strip().replace("\n", " ")
    if len(title) > 100:
        title = title[:97] + "..."
    return f"- [{title}]({signal.url}) — {meta}, {signal.created_at.date().isoformat()}"


def render_markdown(top_themes: list[ThemeResult], recent: list[Signal], meta: dict) -> str:
    lines: list[str] = []
    lines.append("# Omi User Signal Report")
    lines.append("")
    generated = meta["generated_at"].strftime("%Y-%m-%d %H:%M UTC")
    lines.append(
        f"Generated {generated} · lookback {meta['lookback_days']}d · repo `{meta['repo']}`"
    )
    counts = ", ".join(f"{SOURCE_LABELS.get(k, k)} {v}" for k, v in meta["source_counts"].items())
    lines.append(f"Source coverage: {counts}")
    github_weight = meta.get("source_weight", {}).get("github", 1.0)
    lines.append(
        f"Source weighting this run: GitHub {github_weight:.2f}x, App Store/Play Store 1.00x "
        "(target split: GitHub 20% / stores 80% of weighted signal — see `score.py`'s `compute_source_weights`)"
    )
    lines.append("")
    lines.append(
        "Priority bands (P0-P3) follow the formula in [`ISSUE_TRIAGE_GUIDE.MD`](../ISSUE_TRIAGE_GUIDE.MD) "
        "section 5, with Failure Severity / Trust Impact / Frequency / Maintenance Leverage / Cost & Risk "
        "estimated automatically from signal statistics — see `score.py` for the exact heuristics. "
        "Treat this as a starting point for triage, not a substitute for it."
    )
    lines.append("")

    lines.append(f"## Top {len(top_themes)} Priority Themes")
    lines.append("")
    for i, theme in enumerate(top_themes, start=1):
        src_counts = ", ".join(f"{SOURCE_LABELS.get(k, k)} {v}" for k, v in theme.source_counts.items())
        lines.append(f"### {i}. [{theme.band}] {theme.name} — score {theme.score:.0f}")
        lines.append("")
        lines.append(
            f"Layer: `{theme.layer}` (weight {theme.layer_weight}) · "
            f"Severity {theme.failure_severity} · Trust {theme.trust_impact} · "
            f"Frequency {theme.frequency} · Leverage {theme.maintenance_leverage} · "
            f"Cost {theme.cost_risk}"
        )
        lines.append("")
        lines.append(f"**{len(theme.signals)} signals** — {src_counts}")
        lines.append("")
        lines.append("Evidence:")
        for signal in theme.signals[:6]:
            lines.append(_evidence_line(signal))
        lines.append("")

    lines.append(f"## Recent Signals (last {meta['lookback_days']}d, newest first)")
    lines.append("")
    if recent:
        lines.append("| Date | Source | Rating/Engagement | Title |")
        lines.append("|---|---|---|---|")
        for s in recent:
            metric = f"{s.rating}★" if s.rating is not None else f"{s.engagement} eng."
            title = s.title.strip().replace("\n", " ").replace("|", "/")
            if len(title) > 90:
                title = title[:87] + "..."
            lines.append(f"| {s.created_at.date().isoformat()} | {SOURCE_LABELS.get(s.source, s.source)} | {metric} | [{title}]({s.url}) |")
    else:
        lines.append("_No signals in the lookback window._")
    lines.append("")

    return "\n".join(lines)


_HTML_TEMPLATE = """<!doctype html>
<html data-theme="light">
<head>
<meta charset="utf-8">
<title>Omi User Signal Report — {generated}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; background:#f5f4ee; color:#201f1a; margin:0; }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 40px 24px 80px; }}
  h1 {{ font-size: 26px; margin-bottom: 4px; }}
  .meta {{ color:#6b6858; font-size: 13px; margin-bottom: 28px; }}
  h2 {{ font-size: 19px; margin-top: 40px; border-bottom: 1px solid #ddd8c4; padding-bottom: 6px; }}
  .theme {{ background:#fff; border:1px solid #ddd8c4; border-left: 5px solid #2f6f5e; border-radius:8px; padding:14px 18px; margin:14px 0; }}
  .theme.p0 {{ border-left-color:#a3392a; }}
  .theme.p1 {{ border-left-color:#a1701a; }}
  .theme-title {{ font-size:16px; font-weight:600; margin:0 0 4px; }}
  .band {{ display:inline-block; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px; background:#dbe6df; color:#193e33; margin-right:6px; }}
  .band.p0 {{ background:#f1ddd6; color:#a3392a; }}
  .band.p1 {{ background:#f0e3c9; color:#a1701a; }}
  .metrics {{ font-size:12.5px; color:#6b6858; font-family: ui-monospace, monospace; margin: 6px 0; }}
  .evidence {{ font-size:13px; margin-top:8px; }}
  .evidence a {{ color:#193e33; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin-top:10px; }}
  th, td {{ text-align:left; padding:7px 10px; border-bottom:1px solid #e5e1d0; }}
  th {{ font-size:11px; text-transform:uppercase; letter-spacing:.04em; color:#8a8571; }}
  code {{ background:#e7e3d4; padding:1px 5px; border-radius:4px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Omi User Signal Report</h1>
  <div class="meta">Generated {generated} &middot; lookback {lookback_days}d &middot; repo <code>{repo}</code> &middot; coverage: {coverage}</div>
  <div class="meta">Source weighting: GitHub {github_weight:.2f}x, App Store/Play Store 1.00x (target split: GitHub 20% / stores 80%)</div>

  <h2>Top {n} Priority Themes</h2>
  {themes_html}

  <h2>Recent Signals (last {lookback_days}d, newest first)</h2>
  {recent_html}
</div>
</body>
</html>
"""


def _theme_html(i: int, theme: ThemeResult) -> str:
    band_class = theme.band.lower()
    src_counts = ", ".join(f"{SOURCE_LABELS.get(k, k)} {v}" for k, v in theme.source_counts.items())
    evidence = "<br>".join(
        f'&bull; <a href="{html_lib.escape(s.url)}">{html_lib.escape(s.title.strip()[:100])}</a> '
        f'&mdash; {SOURCE_LABELS.get(s.source, s.source)}'
        f'{f", {s.rating}★" if s.rating is not None else ""}'
        f", {s.created_at.date().isoformat()}"
        for s in theme.signals[:6]
    )
    return f"""
  <div class="theme {band_class}">
    <p class="theme-title"><span class="band {band_class}">{theme.band}</span>{i}. {html_lib.escape(theme.name)} &mdash; score {theme.score:.0f}</p>
    <div class="metrics">layer {theme.layer} (w{theme.layer_weight}) &middot; severity {theme.failure_severity} &middot; trust {theme.trust_impact} &middot; frequency {theme.frequency} &middot; leverage {theme.maintenance_leverage} &middot; cost {theme.cost_risk}</div>
    <div class="metrics">{len(theme.signals)} signals &mdash; {src_counts}</div>
    <div class="evidence">{evidence}</div>
  </div>
"""


def render_html(top_themes: list[ThemeResult], recent: list[Signal], meta: dict) -> str:
    generated = meta["generated_at"].strftime("%Y-%m-%d %H:%M UTC")
    coverage = ", ".join(f"{SOURCE_LABELS.get(k, k)} {v}" for k, v in meta["source_counts"].items())
    github_weight = meta.get("source_weight", {}).get("github", 1.0)
    themes_html = "".join(_theme_html(i, t) for i, t in enumerate(top_themes, start=1)) or "<p>No themes matched.</p>"

    if recent:
        rows = "".join(
            f"<tr><td>{s.created_at.date().isoformat()}</td>"
            f"<td>{SOURCE_LABELS.get(s.source, s.source)}</td>"
            f'<td>{f"{s.rating}★" if s.rating is not None else f"{s.engagement} eng."}</td>'
            f'<td><a href="{html_lib.escape(s.url)}">{html_lib.escape(s.title.strip()[:90])}</a></td></tr>'
            for s in recent
        )
        recent_html = f"<table><tr><th>Date</th><th>Source</th><th>Rating/Eng.</th><th>Title</th></tr>{rows}</table>"
    else:
        recent_html = "<p>No signals in the lookback window.</p>"

    return _HTML_TEMPLATE.format(
        generated=generated,
        lookback_days=meta["lookback_days"],
        repo=html_lib.escape(meta["repo"]),
        coverage=coverage,
        github_weight=github_weight,
        n=len(top_themes),
        themes_html=themes_html,
        recent_html=recent_html,
    )
