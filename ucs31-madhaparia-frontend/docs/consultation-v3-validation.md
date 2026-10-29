# Tentative consultation presentation

The result view now presents ranked possible explanations after the backend's targeted questions. It does not convert a model score into a diagnosis. Supporting symptoms, details that fit less well, explanations and evidence caveats come from the backend response; the frontend does not invent condition-specific reasoning or suppress disease names.

`PossibleExplanations.jsx` is shared by the current result and patient/admin history. Raw scores remain available inside collapsed ranking details, with an explicit probability limitation. Shared evidence caveats appear once. The result also displays the backend assessment summary, practical next steps and professional-review recommendation. An urgent status, red flag or urgent care level overrides all candidate display. Vague or unsupported input keeps its clarification path.

The cache architecture and saved histories are preserved. The cache policy version is now `consultation-v3-2026-10-27`, so older abstentions and question sequences are not reused as current consultations. Existing history records remain accessible with caution text. Landing-page and dashboard wording now describes multiple tentative possibilities.

The request still sends `age`, `sex`, original `text` and `confirmed_codes`, plus the accumulated stable `follow_up_answers`. The client supports the backend's bounded five-question flow, numbered controlled options, reload continuation, English/Swahili text and early emergency guidance.

Validation baseline for this iteration: **90 Vitest tests passed** before these presentation changes. Current component/service validation: **104 tests passed** across 18 files; lint and the production build passed. Fourteen tests were added for candidate ordering, supplied supporting/counterevidence, explanation preservation, collapsed scores, invalid scores, Swahili presentation, no invented support, caveat deduplication, useful post-question results, practical next steps, care-level emergency precedence and service-contract preservation. Existing tests were updated where they previously required a single dominant condition or primary percentage.

Ten real V3 browser journeys are authored in `e2e/consultation-v3.pw.js`; their final executed results will be recorded after the isolated V3 API is ready. They cover natural English/Swahili cough and fever, cough alone, fever alone, English/Swahili negation, early emergency guidance, vague input and rejection of old abstention caches. Browser cases assert data flow and useful tentative output rather than invented clinical ground truth.

Run against an isolated, migrated/seeded V3 database:

```powershell
npm test -- --reporter=dot
npm run lint
$env:VITE_API_BASE_URL='http://127.0.0.1:8000'
npm run build
$env:E2E_MODEL_VERSION='v3'
npm run test:e2e
```

Older V1/V2 browser modes remain selectable with `E2E_MODEL_VERSION`. This iteration does not claim their browser cases passed unless separately executed. No clinical validation is implied by software checks. No commits, pushes, publishing or deployments were performed.


## Final live verification — 28 October 2026

All **10/10 real V3 Edge browser journeys passed** against the current isolated local API/database. Cough alone correctly leaves fever unmentioned unless the patient is actually asked and answers; the initial test's assumption of absence was corrected. The final component/service suite passed **104/104**, lint passed, and the production build passed. Labels for evidence now explicitly describe model-comparison associations rather than clinical support. Current counts and the complete implementation report are in [RESPIRACARE_IMPROVEMENTS.md](../../RESPIRACARE_IMPROVEMENTS.md). Browser JSON and a visually inspected full-page screenshot are retained under ignored `playwright-results/`. No HTTP responses were mocked in the browser tests.
