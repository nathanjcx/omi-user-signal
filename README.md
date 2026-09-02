# omi-user-signal

Fetches recent user feedback for [Omi](https://www.omi.me) (GitHub issues,
App Store reviews, Google Play reviews), groups it into themes, scores each
theme with the Priority Score formula from Omi's own
[`ISSUE_TRIAGE_GUIDE.MD`](./ISSUE_TRIAGE_GUIDE.MD) (copied in — see
`NOTICE.md`), and writes a ranked report of what's worth fixing, every run.

## Run it

```bash
python3 -m pip install -r requirements.txt
gh auth login          # once, if not already authenticated — GitHub source shells out to `gh`
bin/user-signal-report # writes out/user-signal-report-<date>.{md,html}, prints the top 5
```

Options: `--top N` (default 5), `--lookback-days N` (default 30), `--out-dir DIR`
(default `out/`, gitignored). Config beyond the flags is env vars, all
optional: `USER_SIGNALS_GITHUB_REPO` (default `BasedHardware/omi`),
`USER_SIGNALS_APPSTORE_ID` (default `6502156163`), `USER_SIGNALS_PLAYSTORE_ID`
(default `com.friend.ios`), `USER_SIGNALS_LOOKBACK_DAYS`,
`USER_SIGNALS_GITHUB_ISSUE_CAP`, `USER_SIGNALS_REVIEW_CAP`,
`USER_SIGNALS_TOP_N`, `USER_SIGNALS_OUT_DIR` — see `user_signals/config.py`.
Point it at a different repo/app by overriding those three IDs.

## How it works

```
sources_github.py   ─┐
sources_appstore.py  ─┼─► Signal (models.py) ─► classify.py ─► score.py ─► report.py
sources_playstore.py ┘        one normalized      groups into    ranks per       renders
                               record per item      named themes   ISSUE_TRIAGE_   .md + .html
                                                                    GUIDE.MD formula
```

- **Sources** (`user_signals/sources_*.py`) each expose `fetch(...) -> list[Signal]`
  plus a pure `parse_entry(raw) -> Signal | None` the fetch function calls —
  parsing is unit-tested against fixture payloads, no network involved. No
  auth needed for App Store (public RSS feed) or Play Store
  (`google-play-scraper`, reads the same public data the Play Store app
  shows); GitHub shells out to the `gh` CLI.
- **classify.py** matches each signal's title+body against a small keyword
  taxonomy (`THEMES`) and tags it with a Core Layer — the same
  capture/understand/memory/intelligence/retrieval-action/ux-polish/docs-tooling
  layers `ISSUE_TRIAGE_GUIDE.MD` uses. A signal can match more than one theme.
- **score.py** implements `ISSUE_TRIAGE_GUIDE.MD` section 5's formula —
  `(Layer Weight × Failure Severity) + Trust Impact + Frequency + Maintenance Leverage − Cost & Risk`
  — per theme, banded into P0–P3 at the guide's exact thresholds. The
  guide's five inputs are meant to be a maintainer's judgment call per
  issue; here they're *estimated automatically* from signal statistics
  (rating, keyword hits, volume, source diversity). **This is an
  approximation of the manual rubric, not a replacement for it** — read
  each `_*` function's docstring in `score.py` for exactly which heuristic
  backs which input, and treat a P0/P1 theme as "look at this," not a verdict.
  Signals are also **source-weighted** (`SOURCE_WEIGHT` in `score.py`):
  App Store and Play Store reviews count 1.5×, GitHub issues count 0.5×,
  since GitHub's open-issues list mixes real user bugs with internal
  engineering/CI/process tickets that never reach an end user, while every
  store review is direct end-user signal. Tune the dict if that mix should shift.
- **report.py** renders the same data as Markdown (diffable, git-friendly)
  and a self-contained HTML file (shareable/readable).

## Known limitations

- Keyword matching is substring-based and will occasionally mis-tag a
  signal. It's deliberately simple so it's auditable, fast, and testable
  without an LLM call — extend `THEMES` in `user_signals/classify.py` as
  new recurring complaints show up.
- Apple's review RSS feed caps at ~500 reviews per storefront; Play Store
  and GitHub pulls are capped by `USER_SIGNALS_REVIEW_CAP` /
  `USER_SIGNALS_GITHUB_ISSUE_CAP` — this is a snapshot of recent signal,
  not a full census.

## Adding a source

Implement `fetch(...) -> list[Signal]` in a new `user_signals/sources_<name>.py`
(with a pure `parse_entry()` for testability), then register it in
`user_signals/cli.py`'s `fetch_all()`. That's the entire integration surface.

**Discord is a planned 4th source, not yet built** — needs a bot token with
read-only message-history access to the relevant channels. Tracked in
[BasedHardware/omi#12627](https://github.com/BasedHardware/omi/issues/12627).

## Testing

```bash
bin/test
```

Hermetic unit tests only (no network) — pure `parse_entry()`/`classify()`/`score_theme()`
functions against fixture data. Fetching against live sources is exercised
manually (`bin/user-signal-report`) rather than in CI.

## Scheduled runs

`.github/workflows/user-signal-report.yml` runs this daily, uploads both
report files as a workflow artifact, and writes the Markdown into the run's
step summary. It doesn't auto-publish anywhere further — wire that into the
workflow's last step if you want the report posted somewhere.
