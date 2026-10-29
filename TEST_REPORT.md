# TEST REPORT — Muse improvements, 2026-10-29

## Real counts (actually run here, final pass)
- Backend full suite: **350 passed, 0 failed** (PostgreSQL via pgserver
  bundle, `TEST_DATABASE_URL` to a local test DB, Alembic + seeded
  catalogue). This is 338 + 7 non-specific tests + 5 Codex-take tests.
  No failing test was deleted. One existing assertion was updated for
  an intentional wording change (COVID note, see CHANGELOG); the
  behaviour it checks is unchanged.
- Frontend full suite (vitest): **117 passed, 0 failed** (20 files),
  including the new withheld-screen test (title, explanation,
  discriminator questions, re-check button, no disease name).
- Frontend build: `vite build` succeeds with `VITE_API_BASE_URL` set.
- 21 journeys: **21 passed** in `tests/test_muse_journeys.py` (included
  in the backend full-suite count; re-run in the final pass as part of
  the suite, not separately re-counted here).

## Final pass results (non-specific output fix)
- "Tiredness and headache" — before: `non_specific_input`, primary
  None, and the consultation dead-ended after fever/cough, so the
  patient saw no condition and no next question. After: full withheld
  screen (title, plain explanation, rest/fluids + temperature check,
  warning signs, 24-48 hour review) AND discriminator questions
  (cough, sore throat, runny/blocked nose, fever, breathing difficulty)
  in the consultation sequence and on the withheld screen; never names
  Pulmonary neoplasm (raw V3 1.000 on these 2 features is a model
  artefact, blocked by the anchor gate). After adding cough + sore
  throat + runny nose with transient tiredness: family answer, 78%
  moderate. With persistent tiredness: still withheld at 45% (tested
  honestly, not forced).
- "Tiredness + headache + fever (mild)" — before: same blank outcome;
  mild did not and does not change the model. After: full withheld
  screen + malaria-test step (fever in Kenya) + discriminator
  follow-ups; never names Epiglottitis (raw top 0.216) or neoplasm.
  After adding cough + sore throat: Seasonal flu (influenza), single
  primary, low match (51% present-only; 64% moderate with breathing
  absent).
- Codex takes (tests in `tests/test_muse_codex_takes.py`, 5 passed):
  everyday aliases map as expected; context codes carry no features;
  sudden one-sided weakness / face drooping raise
  `sudden_neurological_change` while general weakness does not; COVID
  note carries the fuller Codex wording.
- What was NOT run in this final pass: browser / Playwright journeys,
  ML training/evaluation suites (no model retrained). Codex's claimed
  45 browser journeys were not re-run here and are reported as Codex's
  claim, not verified by Muse.

## Real counts (actually run here, follow-up run)
- Backend full suite: **338 passed, 0 failed** (PostgreSQL via pgserver bundle,
  `TEST_DATABASE_URL` to a local test DB, Alembic + seeded catalogue).
  This includes the earlier 39 new tests plus 12 dual/family tests and
  5 uncapped-follow-up tests. No failing test was deleted; one existing
  frontend test that asserted the old separate "Medical name:" line was
  updated to assert the new dual title (the behaviour intentionally
  changed, see CHANGELOG), and old 5-question-cap assertions were not
  needed to change — the v3 consultation tests still pass because the
  unknown-answer and gain stops end those flows first.
- Frontend full suite (vitest): **116 passed, 0 failed** (20 files),
  including the new dual-title and TB/family-note tests.
- Frontend build: `vite build` succeeds with `VITE_API_BASE_URL` set
  (baseline requirement; without it the baseline vite config itself errors).

## Follow-up results (dual naming, flu-like fix, uncapped gathering)
- Dual naming: all 21 V3 classes, EN and SW, pass the
  simple (medical) format check.
- Common cluster, before → after:
  - "headache, sore throat, dry cough and a running nose" — before:
    "running nose" unmapped (3 symptoms, URTI 69% moderate by luck).
    After: runny_blocked_nose mapped, 4 symptoms, family answer
    "Flu-like illness / common cold (viral upper respiratory
    infection)", 78% moderate, with care steps and COVID test note.
  - "headache, sore throat, cough and runny nose for 2 days" — before:
    withheld (bucket 4:0 disabled). After: family answer, 78% moderate.
  - "fever, cough, tiredness and sore throat" (4:0 close case) — still
    withheld: top 51%, below the 75% family threshold.
  - "headache, tiredness and cough for 2 days" — before: Pulmonary
    neoplasm 100% strong. After: no neoplasm name, status uncertain,
    reason sparse_serious_guard, professional-review guidance.
  - "fever + cough" — before: withheld. After extra discriminator
    (sore throat "yes"): URTI, 70% moderate.
- 21 journeys: **21 passed** in `tests/test_muse_journeys.py` (re-run).
- New tests: `tests/test_muse_dual_and_family.py` (12 tests) and
  `tests/test_muse_uncapped_followup.py` (5 tests) — all pass.
- What was NOT run in this follow-up: browser / Playwright journeys,
  ML training/evaluation suites (no model retrained).

## Earlier counts (first build, for reference)
- Backend full suite: **321 passed, 0 failed** (PostgreSQL via pgserver bundle,
  `TEST_DATABASE_URL` to a local `respiratory_test` DB, Alembic + seeded catalogue).
  This includes the 39 new tests below and all pre-existing tests.
  Earlier run before fixes: 287 passed / 34 failed — all 34 were (a) V1/V2 joblibs
  removed from the first copy and (b) duration advice displacing `health_guidance`.
  Both were fixed in code (joblibs restored; duration advice inserted after the
  primary care step), not by deleting tests. No failing test was deleted.
- Frontend full suite (vitest): **115 passed, 0 failed** (20 files), including
  the new match-band test. Earlier run: 114/115 — the 1 failure was a duplicate
  duration line from the new "What we understood" section; fixed by removing
  the duplicate line (the existing duration line below the result stays).
- Frontend build: `vite build` succeeds with `VITE_API_BASE_URL` set (baseline
  requirement; without it the baseline vite config itself errors).
- Backend smoke: uvicorn starts, `/openapi.json` and `/health` respond.
  Live `/nlp/map` verified: "I can't breathe" → `breathing_tier: emergency` +
  emergency guidance; "napumua kwa shida" → `urgent` + same-day guidance;
  "I can breathe fine but I have a cough" → no red flag (DB-dependent mapping
  path returns the baseline "schema not ready" error on sqlite, as in baseline).

## 20 journeys + 1 extra (function-level, not browser)
All 21 pass in `tests/test_muse_journeys.py`, using the same functions the API
uses (mapping → safety → V3 selection). A browser journey did NOT run here and
is NOT claimed: no browser automation was available in this worker.
- Withheld (no confident name): headache+fatigue, cough only, fever+cough 2 days,
  fever+cough+tiredness, generic fever+pain+fatigue, close-call cough+smell+wheeze.
- Named, moderate only: chronic cough + weight loss → Tuberculosis, 75% moderate
  (never strong on 2 symptoms).
- Urgent (no prediction): can't breathe (emergency), difficulty walking + can
  speak (urgent after severity check), severe chest pain, fainting, blue lips,
  coughing a lot of blood, confusion, baby fever age 0, headache+fever+stiff neck.
- Not triggered: "I can breathe fine" + cough.
- COVID: loss of smell only / +cough+fever / loss of taste + fever → recognised
  (taste = note, no model feature), never a COVID label, COVID note shown.
- Severe flu-like illness, no test → nothing named, never COVID.

## What was NOT run
- Browser / Playwright journeys (14 in the baseline report): not run here.
- ML training/evaluation suites (369 in the baseline report): not re-run; no
  model was retrained and no model artifact changed except hash fields in the
  policy/scope JSONs.

## Known limitations (see LIMITATIONS.md)
Gap thresholds unvalidated on a fresh fold; real V3 gap gate fires rarely
(distribution is extremely peaked); Kiswahili copy draft unreviewed.
