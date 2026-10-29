# TEST REPORT — Muse improvements, 2026-10-29

## Real counts (actually run here)
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
