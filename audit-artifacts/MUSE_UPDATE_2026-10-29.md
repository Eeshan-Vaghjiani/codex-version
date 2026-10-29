# Muse update — fetched 29 October 2026

Scope: read-only comparison of branches in this repository. Muse's tests were
not rerun by Codex. No outside organisation repository was accessed.

## Current branch

`origin/muse/respiracare-improvements-2026-10-29`: **`24612e9`**, previously
`d11800d`. Four new commits:

- `6e3dd09`: prompt-first backend/consultation changes, aliases and tests.
- `9d5c686`: ML copy, frontend/dependency lockfile and documentation.
- `ded81cc`: first 10,000-case sweep, runner/analyser and results.
- `24612e9`: second sweep and corrected regression rerun.

## Confirmed code changes

- Initially clear prompts stop after breathing safety, rather than continuing
  duration/severity/model-refinement questions. Non-specific cases ask respiratory
  discriminators rather than advice-only duration/severity questions.
- Stated cold/flu can yield a context-family answer without a percentage.
- Four-present family answers now tolerate answered negative features rather
  than only bucket `4:0`. Current Codex already supports this.
- For an initially clear result, Muse records a safety "no" in displayed symptom
  states but **freezes the initial model evidence**, deliberately preventing that
  new negative from changing the name. This is a substantive evidence-policy
  difference, not just fewer questions; it is not independently validated.
- The Muse flow still lacks Codex's proactive severe-chest-pain and general vs
  sudden-one-sided weakness clarification questions. Free-text warning detection
  remains. Its general gap thresholds remain `0.10/0.20`, not Codex's separately
  fold-checked `0.15/0.60` disease gate.

None of these newer policy changes was silently adopted into Codex during the
audit. Faster questioning is potentially useful; freezing negative evidence needs
explicit review rather than assuming an initially named result must be preserved.

## What Muse reports having run

Its current `TEST_REPORT.md` reports **365 backend tests**, **117 frontend
tests**, a successful build and two 10,000-row function-level sweeps. It reports
**no browser/Playwright rerun**, no new ML evaluation suite, and no fresh
independent threshold validation. These are Muse's recorded results, not tests
independently executed here. Its comparison document still compares older Codex
commits and is not an up-to-date assessment of Codex `aa7d422`.

## Independently counted uniqueness of the committed CSVs

Read with Python's `csv.DictReader` directly from the fetched Git objects:

| Batch | Rows | Distinct descriptions | Distinct `(text, language, pattern, age, duration)` tuples | Repeated tuple rows |
|---|---:|---:|---:|---:|
| 1 | 10,000 | **6,094** | **7,329** | **2,671** |
| 2 | 10,000 | **7,657** | **8,748** | **1,252** |

Different answer patterns can be useful tests, but these files do **not** contain
10,000 unique descriptions or even 10,000 unique full scenarios each. Batch 2
also includes eight original harness age-string errors; Muse records a corrected
eight-case rerun rather than claiming those were product crashes.

Muse's sweeps exercise mapping/consultation functions using an in-memory
catalogue adapter, not HTTP/authentication/PostgreSQL/history or the browser.
Neither their zero-blank count nor their naming counts establish disease
accuracy or Kenyan clinical safety. Its stated 267/384 strong matches on at most
two model features remain an acknowledged policy concern, not a validated gain.
