# Frontend audit — 2026-10-27

## Baseline

- Git initially contained only the user's untracked `public/images/`; those files were not edited.
- Original Vitest suite: 16 files, 67 tests passed.
- Original lint: passed.
- Production build without `VITE_API_BASE_URL`: correctly failed configuration validation. Build with an explicit local test API URL passed; `.env` was not changed.
- Confirmed defects: all recognized mentions were preselected regardless of symptom status; only the leading model label was displayed; no follow-up request/UI support; dominant percentage bars suggested certainty; an in-flight NLP response could repopulate stale results after the description changed; missing patient-facing context limitations.

## Repairs

- `SymptomInputPage`: stale/unmounted response protection; explicit present/absent/uncertain labels; duration/severity review; immediate localized safety guidance with a bilingual fallback; urgent input does not offer a routine confirmation questionnaire.
- `SymptomConfirmationPage`: present-only selection for the patient; absent/uncertain and other-person mentions retained separately; no implied single-condition outcome.
- `services/predictions`: optional `follow_up_answers` and language forwarded unchanged; saves request demographics to resume pending questions after reload.
- `PredictionPage`: controlled numbered options, stable IDs, append-only answer history, answer validation, retained question after backend errors, emergency precedence, abstention view, context limitations, uncertainty before candidates, up to three model patterns, numeric scores labeled uncalibrated and displayed without confidence bars. Questions without a stored prediction do not request feedback.
- Patient/admin history: uncalibrated score labels, removed certainty bars, no disease display for abstention/question states, preserved context warnings, and cautious fallbacks for legacy responses without uncertainty metadata. Historical leading patterns remain viewable with caution text.

## Validation

The final Vitest suite contains 17 files and 87 tests, all passed: 20 new tests plus the existing 67 (one former rank-1-only assertion was updated to verify competing candidates). Added tests cover localized numbered questions, missing answers, stable answer IDs/demographics, multi-turn history, backend answer rejection, abstention suppression, emergency precedence and immediate safety, nested context limitations, stale NLP responses, extracted context, present-only confirmation, other-person exclusion, backend-numbered options, legacy history caution/context fallback, and HTTP field preservation. These are deterministic component/service tests with mocked HTTP responses.

Seven additional real browser journeys passed using headless system Microsoft Edge, Playwright, the actual Vite frontend and isolated local PostgreSQL/API. Six with production V1 active verified UI login, English negation, Swahili negation and positive symptoms, controlled follow-ups, reload resume, unchanged demographics, duration answers, persisted history/state/answer equality, English/Swahili emergency guidance before confirmation, and vague-input abstention. One with V2 explicitly activated verified three research pattern candidates, uncalibrated score labels, uncertainty, negative/duration context, and saved-history caution. It deliberately does not assert a clinical disease label. The initial V2 run exposed missing uncertainty metadata on the actual history API; the backend export and frontend legacy fallback were repaired, and the rerun passed. The final V1 six-journey run also passed after those integrated repairs.

No HTTP responses were mocked in these browser journeys. Run them only against an isolated test database: they register synthetic local users and save assessments. Machine-readable final browser reports and a visually inspected full-page research result screenshot are retained locally in ignored `playwright-results/live-v1-results.json`, `playwright-results/live-v2-results.json`, and `playwright-results/v2-research-result.png`.

Lint and the production build passed after all changes. `npm audit` initially reported one high-severity transitive dependency finding. A compatible lockfile update changed `undici` 8.11.2 to 8.12.3; the final audit reported zero vulnerabilities. `@playwright/test` was added as a development dependency for maintainable real end-to-end tests.

Total final frontend validation: **94 unique tests executed, 94 passed, 0 failed** (87 component/service + 7 real browser); 27 were added. Passing software tests do not establish clinical validity.

Run from this repository:

```powershell
npm test -- --reporter=dot
npm run lint
$env:VITE_API_BASE_URL='http://127.0.0.1:8000'
npm run build
# With the isolated migrated/seeded API running on port 8000:
$env:E2E_MODEL_VERSION='v1' # Audit database must have V1 active.
npm run test:e2e
# Separately, with V2 explicitly active in that same isolated database:
$env:E2E_MODEL_VERSION='v2'
npm run test:e2e
```

No commits, pushes, publishing, or deployments were performed. No original data/model artifacts were modified by the frontend work and no destructive backups were required.


## Follow-up: TB display recheck

A further review found that an unversioned browser session cache from before the repair could reopen the old TB output when text/confirmed codes were identical. `services/predictions.js` now stamps fresh cached responses with the current assessment cache version and discards older/unversioned entries. Persisted patient history records are not deleted or rewritten by this cache migration.

Three new component/service regressions cover legacy TB cache removal, policy-version mismatch and current follow-up resume. The full frontend unit suite now passes90/90; lint and build pass. A real browser regression also injects an old99.75% TB cache, reloads the page and verifies it is removed before a fresh cough-and-fever assessment. See the latest live-v1-results.json for the executed browser count. The backend targeted recheck passed15/15 cases: all12 supplied cases with V1 plus3 sparse-input cases with V2. The underlying raw models were not retrained; their original scores remain in audit baseline files and must not be interpreted as fresh application diagnoses.
