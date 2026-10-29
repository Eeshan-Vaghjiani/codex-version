# Patient results UI: Kenyan context

## Baseline inspected before implementation (28 October 2026)

The existing V3 flow is symptom text → NLP mapping → patient confirmation → age and sex → bounded backend follow-up questions → prediction response → current result and saved history. `PossibleExplanations` rendered the first three ranked model candidates. Candidate percentages were collapsed, but a patient could open them; the history list also joined three disease names. Routine uncertainty used the same amber family as safety warnings.

Baseline checks: 18 Vitest files / 104 tests passed; oxlint passed. A production build passed with `VITE_API_BASE_URL=http://127.0.0.1:8000` (713 modules); without a configured backend URL it correctly refuses to build. The existing real Edge UI/API suite passed 10/10 journeys in 52.2 seconds. These are software checks, not evidence of clinical accuracy.

An actual baseline patient journey entering **“I have a cough and fever.”** and answering the existing follow-ups with “no” and “less than 3 days” displayed **Voice Box Inflammation (Laryngitis), Viral Sore Throat, and Tuberculosis (TB)** together. This observation describes the output; no clinical reference was available to label those candidates as true or false. Desktop (1280 px) and mobile (390 px) screenshots are saved in `audit-artifacts/kenya-patient-ui/before-desktop.png` and `before-mobile.png`. Mobile had no horizontal overflow.

## Implemented contract and presentation

- Current results and both patient history screens require `primary_prediction`, terminal `prediction_complete`, and a versioned backend decision with `status: possible_explanation`. They never choose from `predictions[0]`.
- Follow-ups, insufficient information, uncertain assessments, old policy records, and urgent responses cannot display candidate names through the primary component. The backend controls eligibility; this UI is not a clinical selection algorithm.
- The primary component accepts one object, retains backend familiar/medical names and descriptions, labels the result a possibility, and provides reported symptom details in an accessible disclosure. It has no score renderer.
- Symptom mapping retains source phrases and confirmation, but removes numeric word-match/suggestion scores and exact/fuzzy jargon.
- Patients receive calm uncertainty summaries, next steps, and a link to reassess an old result. Clinical warnings retain their prominent styling and precede normal assessments. An urgent mapping response immediately focuses and scrolls to its alert; scrolling is instant, with a margin that keeps the message clear of navigation.
- Routine uncertainty and unused/context notes use a neutral blue treatment. The current result heading is shorter. Existing navigation, demographics, feedback, and responsive layout are preserved.
- The session cache version changed to `kenya-single-primary-2026-10-28`; old consultation results and questions are discarded rather than presented under the new policy.
- The original candidate renderer is retained as `AdminModelCandidates.jsx` and imported by the administrator screen only, so research audit functionality remains separate from patient presentation.

## Verification

The updated unit suite currently passes 20 files / 114 tests, including explicit selection, conflicting candidate arrays, absent policies, urgent flags, abstention, old caches, history list/detail, and follow-up behavior. Old tests requiring three patient candidates or expandable percentages were intentionally replaced. Updated oxlint and production build pass (715 modules). New routine information text/background contrast is 9.05:1; the retained urgent amber text/background pair is 7.59:1. This checks these color pairs only, not a full accessibility audit.

The final stable Microsoft Edge run passed **14/14 real UI/API journeys in 1.1 minutes**, including an actual accepted primary, English/Swahili negation, vague symptoms, bounded follow-ups and reload, current/history parity, urgent English/Swahili input, unrecognized wording ('I feel unwell.') and empty input, cache migration, and 390 px mobile layouts. Result pages with screenshots have explicit horizontal-overflow checks. No patient result or saved result contained a numeric model percentage. After the final accessibility change, both affected urgent journeys were rerun and passed (2/2, 9.0 seconds): English at 1280 × 720 and Kiswahili at 390 × 844. They verify that the alert receives keyboard focus and its entire bounding box is inside the viewport, clear of the navigation, without a questionnaire link. The accepted primary and uncertain examples were visually inspected on desktop/mobile; urgent and unrecognized-wording layouts were also inspected. Clinical validity and a complete accessibility audit are outside what these software checks establish.

An earlier run passed 13/14 with the first registration failing during API startup. A subsequent attempt encountered a temporary JSX syntax error while a guidance-deduplication edit was in progress; lint caught it, it was repaired, and the clean final run passed all 14 after the code was fixed. These failed attempts are retained in the audit logs rather than counted as successful runs.

Actual final patient responses, including the precise follow-up answers, are preserved in `audit-artifacts/kenya-patient-ui/actual-browser-responses.json`. Full Playwright results are in `final-browser-results.json`; successful command logs are `browser-after-final.txt`, `frontend-unit-final.txt`, and `frontend-build.txt`. The final affected-browser rerun is `browser-urgent-final.txt`, with JSON in `urgent-focus-browser-results.json`.

## Actual improved UI examples

These are synthetic patient inputs sent through the real local application, not clinically reviewed patient cases. Most respiratory tests answered no to the listed additional symptoms and less than 3 days for duration; the accepted coughing-fits example supplied 5 days in the text and answered only the breathing question no. The backend stopped questioning once its selection rule was met. No answers were added to force a chosen diagnosis.

| Input | Actual result and interaction | Screenshots |
|---|---|---|
| “I have intense coughing fits and vomiting after coughing for 5 days.” | `prediction_complete`; one **Whooping cough (pertussis)** possible explanation; professional review recommended; no confidence percentage. One follow-up: breathing difficulty = no. The result explicitly states it is not a diagnosis and is not clinically validated in Kenya. | [Desktop](../../audit-artifacts/kenya-patient-ui/after-informative-coughing-fits-desktop.png), [mobile](../../audit-artifacts/kenya-patient-ui/after-informative-coughing-fits-mobile.png) |
| “I have a cough and fever.” | `assessment_uncertain`; no disease name after five follow-ups; “The information does not support naming one illness at this point.” This replaces the baseline three named candidates described above. | [Desktop](../../audit-artifacts/kenya-patient-ui/after-english-cough-and-fever-desktop.png), [mobile](../../audit-artifacts/kenya-patient-ui/after-english-cough-and-fever-mobile.png) |
| “I have a headache and feel tired.” | `assessment_uncertain`; no disease name; four follow-ups about duration, severity, fever and cough; explains the app's respiratory scope and gives next steps. | [Desktop](../../audit-artifacts/kenya-patient-ui/after-headache-and-tiredness-desktop.png), [mobile](../../audit-artifacts/kenya-patient-ui/after-headache-and-tiredness-mobile.png) |
| “I have fever, a cough, a sore throat and body aches.” | `assessment_uncertain`; no disease name after four follow-ups. The app does not label this influenza merely because someone might call it flu. | [Desktop](../../audit-artifacts/kenya-patient-ui/after-fever-cough-sore-throat-body-aches-desktop.png), [mobile](../../audit-artifacts/kenya-patient-ui/after-fever-cough-sore-throat-body-aches-mobile.png) |
| “I feel unwell.” | No supported symptom recognized; asks for clearer wording; no confirmation link, questionnaire or disease name. An empty description separately receives an inline correction. | [Desktop](../../audit-artifacts/kenya-patient-ui/after-insufficient-desktop.png), [mobile](../../audit-artifacts/kenya-patient-ui/after-insufficient-mobile.png) |
| “I am struggling to breathe.” | Immediate mapping warning recommends urgent assessment, emergency care for severe breathing difficulty, and says not to wait for the questionnaire. No continue-to-confirmation link. Kiswahili equivalent also passed. | [Focused desktop viewport](../../audit-artifacts/kenya-patient-ui/after-urgent-focused-desktop.png), [focused mobile viewport](../../audit-artifacts/kenya-patient-ui/after-urgent-focused-mobile.png) |

## Files changed for this UI work

- `src/services/patientResult.js`: explicit backend-primary contract guard; no ranked-array fallback.
- `src/components/PossibleExplanations.jsx`: one backend-selected explanation, familiar/medical name, plain description and optional reported symptoms; no percentage renderer.
- `src/components/AdminModelCandidates.jsx` and administrator import: preserve the original protected audit renderer separately.
- `src/pages/PredictionPage.jsx`, `PatientHistoryPage.jsx`, `PatientHistoryDetailPage.jsx`: primary/uncertain/legacy/urgent presentation, history parity and no duplicate next-step paragraph when it repeats the first bullet.
- `src/pages/SymptomInputPage.jsx`: remove numeric text-match and suggestion scores; retain source wording and confirmation; immediately focus/scroll urgent guidance into view.
- `src/services/predictions.js`: reject cached results from the old policy.
- `src/styles/global.css`: calm uncertainty/context styles, responsive primary typography and visible disclosure focus.
- Updated/new component, page, service and `e2e/consultation-v3.pw.js` tests; this report.

The unrecognized-wording browser case does not establish handling of unsupported medical complaints such as abdominal pain; backend scenario tests cover those separately.

Existing public images and prior uncommitted project repairs were preserved. No commit, push or deployment was performed.

## Reproduce

```powershell
cd ucs31-madhaparia-frontend
npm test
npm run lint
$env:VITE_API_BASE_URL='http://127.0.0.1:8000'
npm run build
npm run test:e2e
```

Browser tests require the isolated migrated/seeded audit API on port 8000 and frontend on port 5173; they create synthetic test accounts. Do not point these tests at a patient production database. API results are attached to the Playwright report; screenshots are stored under `audit-artifacts/kenya-patient-ui`. The saved baseline browser report and original browser spec are in the same directory for comparison.

No interface change establishes improved model accuracy or Kenyan clinical validity. See the ML evaluation and research reports for model metrics, provenance, selection coverage, and remaining validation needs.
