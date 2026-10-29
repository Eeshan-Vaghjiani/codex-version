# Local validation — 29 October 2026

Starting commit: `c04aca7`. Only the local codex-version repository is in scope.
No Drive snapshot or organisation repository was accessed. No .env was opened.

## Final feature-port addendum

User-approved Muse features were adapted into Codex, not merged wholesale:
family-only output, simple + medical naming, sparse-serious guard, and longer
gathering (soft guide 5, hard ceiling 20, 24-code routine pool).

Latest checks in this checkout:

| Check | Result |
|---|---|
| Backend, disposable PostgreSQL schema | **381 passed**, existing Starlette/httpx warning |
| ML | **423 passed, 5 subtests passed** |
| Frontend unit tests | **125 passed**, 21 files |
| Lint | Passed |
| Production build | Passed with process-only `VITE_API_BASE_URL=http://127.0.0.1:8011` |
| Real Edge browser | **46 passed**, 3.5 minutes; actual UI/API/history, no mocked browser responses |

The first browser rerun exposed a real history-projection 500: a family-only
answer was incorrectly looked up as one of the 21 model classes. It now preserves
the saved family snapshot; API/history regression coverage was added. Family
answers have an explicit family label, no patient-facing underlying class and
no percentage, including if stale score fields are present. Old cached flows
and older patient-policy histories require reassessment under the new version.
An intermediate run also started before API readiness (three connection-refused
failures); after a successful health check, the full 46-case rerun passed.

New pool coverage checks every question against actual catalogue/V3 features,
both languages, and the urgent stop for newly disclosed night breathlessness.
The beyond-five API path and 20-question payload ceiling are covered. Backend
and ML NLP dictionaries have identical parsed content. Kiswahili flu-like
guidance no longer incorrectly says bird flu.

**Limits:** the frozen specific-name gap gate is unchanged by these ports.
The adopted family-only **0.75 score / 0.20 gap** heuristic has **not** been
independently evaluated on a held-out fold. The checked disease-gate reports
do not measure family-answer coverage or accuracy. No updated overall accuracy,
clinical safety, Kenyan patient validation or language-comprehension claim is
made. No model was retrained; no COVID class added; no deployment performed.
Push is authorised only to `codex-respiracare-improvements-2026-10-29`.

## Baseline (before application changes)

- Initial frontend unit/browser commands could not start: dependencies absent.
- Initial backend command could not start: `TEST_DATABASE_URL` absent.
- Initial unrestricted ML discovery: 8 collection errors (missing rapidfuzz and
  historical experiment scripts requiring external temporary files). The actual
  unit suite is `python -m pytest tests`, not the executable experiment scripts.
- With the backend's pinned Python environment installed, ML unit suite:
  **365 passed, 4 failed, 5 subtests passed; 369 tests collected**.
  Failures: two V2 builder tests, V2 full-schema test, and source-partition/runtime
  parity test. Required DDXPlus source metadata and processed CSVs are absent.
  These tests remain present; missing datasets are not replaced by invented data.
- Evidence: `baseline-2026-10-29-ml.xml`.
- Backend after installing its pinned requirements and starting a new local-only
  PostgreSQL 16.15 cluster: **282 passed** (`baseline-2026-10-29-backend.xml`).
- Frontend on Node 24.15.0: **114 passed** (`baseline-2026-10-29-frontend.xml`).
  Because dependency installation took 11 minutes, this recovery baseline used
  an isolated `git archive c04aca7` copy, not modified source.
- Real Edge/Playwright baseline on that same frozen copy and V3 API:
  **14 passed**, 50.4 seconds. The first uninstalled attempts were not passes.

## Independent gap validation — source fold checked

The official DDXPlus v15 files (CC BY 4.0) were restored locally and publisher
checksums verified; see
[TRAINING_PROVENANCE_2026-10-29.md](TRAINING_PROVENANCE_2026-10-29.md). A
predeclared 0.15 relative-score gap and 0.60 match floor were checked on a
separate 6,479-profile source-validation fold per
[the frozen protocol](../docs/GAP_VALIDATION_PROTOCOL.md), with no test-set
threshold tuning. **24 of 48 evidence buckets passed** the declared source error
bound; the rest stay disabled. No threshold was selected from test results. The
gap artifact is frozen and served by the backend; sparse buckets still withhold
rather than invent a threshold.

## Hygiene

Filename-only local .env check found no .env files. No credentials were read or
copied, and there are no local credentials available to rotate. Owners of any
shared snapshot must delete its .env and rotate credentials with their provider;
that external action cannot be verified or performed from this checkout.

## Earlier full-suite run (before feature ports)

| Suite | Baseline | Final |
|---|---:|---:|
| Backend | 282 passed | **360 passed**, one existing Starlette/httpx deprecation warning |
| ML | 365 passed, 4 failed | **395 passed, 5 subtests passed** (missing-data failures resolved) |
| Frontend | 114 passed | **124 passed**, 21 files |
| Real Edge browser | 14 passed | **45 passed** on the final rerun (2.3 minutes): original 14 + required-case variants + everyday-conversation/correction/history journeys |

The four baseline ML missing-data failures are resolved by the restored official
source files; none was deleted, skipped or converted without real data. The
new ML, backend and frontend tests pass. Evidence: `final-2026-10-29-{backend,ml,frontend}.xml`
and `conversation-*.xml`.
Existing order-specific tests were updated to include the requested safety
screen. The informative-primary test now asserts explicit pending-gap abstention.
The 0.02-nat boundary remains tested with isolated actionable model fixtures.

`npm run lint` passed. Production build initially correctly refused an unset
`VITE_API_BASE_URL`; rerunning with a process-only local test URL passed. No .env
was created. Node 24.15.0 was used to satisfy the locked dependency engine range.

`git diff --check` passed. Filename/index hygiene check found **no .env, .venv,
node_modules, dist or raw CSV additions/modifications**. The 158 previously tracked
frontend dist files are staged for removal from the index; generated build output
remains local/ignored. No model artifact or frozen bucket threshold was changed.
The work remains uncommitted and was not pushed or deployed.

Browser command: `node node_modules/@playwright/test/cli.js test` with a process-only
`E2E_API_URL` pointing at the freshly restarted local V3 API. The final run used
real Edge, isolated PostgreSQL synthetic accounts, actual mapping/confirmation/
prediction/history requests, and no mocked browser API responses. Every new case
is recorded PASS with expected naming/score/urgency/advice in
`../RESPIRACARE_MANUAL_TEST_CASES.md`. Full local Playwright JSON/attachments remain
in the ignored frontend `playwright-results` / `test-results` folders. Generated
screenshots are in ignored `validation-2026-10-29-ui`, not mixed into old evidence.

The four model/bucket JSON files have identical parsed contents and LF-normalized
contents to `c04aca7`, with no git diff. Windows checkout CRLF differs from raw git
blob bytes; runtime model-policy hash/parity checks passed. No model was retrained.

## Outstanding validation — do not call this fully complete

- The source fold checked the predeclared gate, but this is **not** newly
  collected or external patient validation. The parent partition had previously
  contributed aggregate reporting metrics. The gate is a research safeguard, not
  a clinical guarantee; the 0.15 gap / 0.60 floor / 2-present minimum were
  declared before the fold, not tuned on it. Passing does not establish patient
  probabilities, real-world triage safety or Kenyan accuracy.
- No Kenyan patient clinical validation, clinician/Kiswahili/Sheng comprehension
  validation, or COVID prediction validation. COVID remains out of scope.
- API/UI follow-up behaviour was tested on synthetic vague Kenyan-language input;
  clinical usefulness and real-world benefit from follow-ups are not established.
- Unresolved dangerous runner-up review is conservative and can over-refer. The
  checked gate only narrows which rich sparse patterns may be named; withholding
  still never rules out illness.
