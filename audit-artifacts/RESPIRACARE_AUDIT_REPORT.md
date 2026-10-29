# RespiraCare audit, repair and validation — 27 October 2026

Completed local repairs across all three repositories. **480 unique tests passed, plus 5 existing subtests; 0 failures or skips in final runs.** Added **208 tests**. All twelve supplied cases were reproduced using the original backend snapshot, retained as regressions, and exercised through the repaired local API with both V1 and V2 selected.

The resulting application is safer software, **not clinically validated**. No model accuracy improvement or clinical probability calibration is claimed.

## Confirmed root causes and implemented fixes

| Confirmed cause | Evidence and repair |
|---|---|
| Production NLP had diverged from the ML implementation. Negation, duration, patient context and several aliases were missing in the backend. | Original backend case observations show both negative-fever cases becoming fever-positive. Synchronized extraction logic/catalogues; added parity tests. `app/nlp/symptom_mapper.py`: polarity/context/duration/severity and `detect_safety_signs`; equivalent ML module. |
| Broad fuzzy suggestions confused different clinical concepts; sneezing lacked its own entry. | Added canonical sneezing, conservative spelling matching, and regression assertions excluding wheezing. Severity/duration are contextual attributes, not recurring unmatched warnings. |
| Confirmation treated all recognized mentions as positive; V2 serving discarded explicit negatives. | `app/services/symptom_confirmation.py::confirm_symptoms` accepts only present patient mentions and preserves absent/uncertain states. `assessment.py::prepare_assessment` keeps unmentioned distinct, and `/predict` forwards supported absence columns. |
| Location-specific symptoms share generic pain evidence. | Headache/chest pain share E_53. Denying a pain location no longer denies all pain or creates conflicting present/absent features. V2 location loss is disclosed. |
| V1's rich simulated training representation is incompatible with sparse conversational input. | Cough+fever reproduces TB at 99.75% for age 21 male. V1 now abstains in this application instead of emitting disease-specific conclusions from incomplete profiles. |
| V2 has untrained absence columns and synthetic extension labels. | Every absent-column tree-split count is zero; absence importance totals 0. COVID/rhinitis additions each use 400 synthetic examples with no independent test labels. Negative answers/duration/severity remain visible without claiming learned benefit. |
| Score magnitude was treated as sufficient evidence; one dominant label/bar obscured alternatives. | Removed arbitrary confidence/margin sufficiency rules. Sparse V2 abstains; at least 3 supported positive features permits only explicitly uncertain research-pattern display, up to 3 candidates. The three-feature guard is an engineering display restriction, not a medically validated threshold. Raw scores and class labels remain intact. |
| No integrated follow-up contract, and warning signs depended on confirmation/model readiness. | Stable bilingual question IDs, controlled answers, sequential replay, maximum 3 questions, actual evidence updates. Bundled warning recognition precedes catalogue/inference and cannot be unchecked. Urgent guidance survives model, schema or history failures. |
| Stale frontend responses and saved history could omit context/uncertainty. | Invalidated stale NLP responses; retained demographics and question history after reload. Stored JSONB context and restored localized warnings in patient/admin history. Real browser testing caught and verified the history repair. |
| Artifact/status checks could disagree with serving. | Exact feature/class order validation; malformed scores/inputs rejected; unavailable artifacts produce readiness errors without fallback activation. `/model/status` reflects the selected model. |

Architecture remains React/Vite → FastAPI → seeded PostgreSQL symptom catalogue → symptom confirmation/profile → independent safety → bounded follow-ups → guarded model inference → stored assessment/history. Authentication, ownership, admin restrictions and feedback remain covered.

## Frozen models, data and evaluation

Original datasets and both model artifacts were preserved. **No retraining, data relabeling, calibration fitting or score rescaling occurred.** Retraining could not supply trustworthy clinical absence labels or independently validated synthetic extension classes from the available evidence.

Evaluation used the original 56,817-record DDXPlus test partition; no fitting or threshold tuning used these runs. Sparse projections use nested deterministic subsets of true positive source symptoms (seed 20261027), with all unreported evidence unknown. These are simulated software/model experiments, not clinical or free-text accuracy estimates. The test partition has been examined historically and is not a pristine holdout.

| Input | Cases | V1 accuracy / macro-F1 | V2 accuracy / macro-F1 |
|---|---:|---:|---:|
| Rich original profiles / all 32 V2 positives |56,817|99.44% / .9933|89.20% / .8698|
| One supported positive |56,816|11.53% / .1090|30.22% / .3521|
| Two supported positives |55,547|21.62% / .2049|60.64% / .5831|
| Three supported positives |49,801|21.13% / .2192|77.11% / .7095|

Macro-F1 uses the fixed 21-class source scope; two/three-symptom cohorts contain 20 represented classes. V2 full-profile top-label ECE=.2265 and three-symptom ECE=.2568, so confidence magnitude is not validated clinical certainty. V1 full-profile ECE=.0091 does not transfer to sparse inputs. The majority-class test baseline is 15.39% accuracy.

Training has 443,075 records, 22,009 repeated raw inputs, and no conflicting raw signatures found. 3,222 test records exactly overlap training inputs. Removing exact overlaps leaves 53,595 test records: V1 accuracy 99.41% / F1 .9933; V2 accuracy 90.10% / F1 .8753. Near duplicates and simulation-generator leakage remain unresolved. Per-class precision/recall, confusion matrices, ECE bins, Brier scores, log loss, SHA-256 hashes and methodology are in [MODEL_AUDIT.md](../ucs31-madhaparia-ml/reports/autonomous_audit/MODEL_AUDIT.md) and accompanying JSON/CSV files.

Baseline and final **model metrics are identical** because the models were frozen. Improvements are in faithful inputs, safety, abstention, follow-up state, error handling and presentation.

## All twelve supplied cases

Original observations below come from the original backend snapshot at age 21/male. Reported historical percentages were retained separately in the user request; minor percentage differences were not assumed to be ground truth. The final API runs answer missing symptom questions “no” and duration questions “not sure”; follow-up answers are synthetic test inputs, not patient facts.

| Case | Reproduced original backend | Final verified behavior |
|---|---|---|
|1 Fever|Croup 37.25%|Fever extracted; bounded follow-ups, then insufficient evidence. No unsupported age-specific conclusion.|
|2 Nose/headache/throat|Allergic sinusitis 45.50%|All 3 symptoms plus vague duration retained. V1 abstains; V2 shows3 uncertain research patterns with limitations.|
|3 Cough+fever|TB 99.75%|Both present; questions then abstention with either model.|
|4 Cough|TB 62.75%|Cough present; at most 3 questions then abstention.|
|5 Nose/sneezing/mild cough|Allergic sinusitis 68.50%; missing sneezing/severity|Sneezing recognized without wheezing; mild severity retained; insufficient supported model evidence, abstention.|
|6 Cough+fever/two days|TB 99.75%; duration missed|Duration 2 days retained; no redundant duration question; abstention.|
|7 Cough/weeks/weight loss|Only cough recognized; TB 62.75%|Cough+weight loss and vague weeks retained without invented bounds; professional-assessment advice, no duplicate warning loop, abstention.|
|8 Cough/struggling to breathe|Only cough recognized; TB 62.75%|Immediate urgent guidance, 0 routine questions, 0 model candidates. Emergency mapping prioritizes the warning rather than completing routine extraction.|
|9 Feel unwell|No extracted symptoms/prediction|No symptoms invented; clarification/insufficient-evidence outcome.|
|10 English no fever|Fever incorrectly positive; TB 99.75%|Cough present, fever explicitly absent through confirmation/profile/features/history; no forced diagnosis.|
|11 Swahili fever+cough|TB 99.75%|Equivalent English/Swahili evidence, localized questions, abstention.|
|12 Swahili sina homa|Fever incorrectly positive; TB 99.75%|Equivalent English negation; fever absent throughout, localized questions, abstention.|

Actual request/response evidence: [original backend](original-backend-case-observations.json), [final V1](final-v1-case-journeys.json), [final V2](final-v2-case-journeys.json). NLP baseline/final details and API assertions are also retained under the ML audit reports. No disease was set as synthetic clinical ground truth.

## Demographics and score calculations

144 controlled frozen-model comparisons varied only age(5/21/65) and sex across 12 inputs and 2 models. Cough+fever at age 21 gives V1 male 99.75% versus female 96.75%; V2 male 16.18% versus female 16.45%. Selecting male did **not** consistently produce 99.5%. Learned demographic splits explain observed differences; this does not establish fairness. Age/sex are validated and preserved across UI/reloads/requests. V2 AGE/SEX_M impurity importances are .091732/.002283.

Class order and feature order match the saved artifacts exactly. Percent formatting is the raw model score×100; the high TB scores were not caused by frontend percent conversion. Croup is not individually prohibited in adults. The serving evidence policy prevents unsupported symptom-to-disease conclusions for all labels.

## Executed tests and integration

| Layer | Baseline | Final passed | Added |
|---|---:|---:|---:|
| ML/NLP/model/evaluation unit tests |97 +5 subtests|201 +5 subtests|104|
| Backend API/PostgreSQL/auth/history/readiness |108|185|77|
| Frontend component/service |67|87|20|
| Real Edge browser journeys |0|7|7|
| **Total** |**272 +5 subtests**|**480 +5 subtests**|**208**|

Final results: **0 failures, 0 skipped**. Counts represent unique suite tests, not cumulative reruns. Pytest XML includes the 5 ML subtests as extra testcase records. The baseline backend tests ran from a preserved original snapshot against a separate generated PostgreSQL schema. Final backend tests include 69 new integrated safety/assessment cases, all 12 mandatory regressions, malformed/empty input, multilingual negation, uncertain/other-person context, individual durations, shared pain evidence, answered-feature forwarding, repeat/order limits, emergency/storage/model/schema failure, ownership and history.

The 7 real browser journeys use actual Vite, FastAPI, PostgreSQL and saved models without mocked HTTP. Six V1 journeys cover login, English/Swahili inputs, negation, follow-ups, reload, history, emergencies and vague input; one V2 journey verifies 3 candidates, uncertainty, duration/negation and saved-history caution. Final frontend lint/build passed; build used explicit local API URL without editing `.env`. Dependency audit ended with 0 findings after the compatible undici lockfile update. Playwright was added as a development dependency. A Starlette/httpx test-client deprecation warning remains; tests pass.

Evidence: [backend JUnit](backend-final-tests.xml), [backend log](backend-final-tests.txt), [ML JUnit](../ucs31-madhaparia-ml/reports/autonomous_audit/ml_final_tests.xml), [frontend report](../ucs31-madhaparia-frontend/docs/autonomous-audit.md). Browser JSON/screenshots are retained in frontend `playwright-results/` (ignored generated artifacts).

## Files, backups and environment

The [complete change manifest](final-change-manifest.json) lists modified/new files and identifies preexisting work. Main implementation groups are backend NLP/services/main/model loader, JSONB migration/model/history, ML NLP/inference/encoder/audit scripts, frontend input/confirmation/prediction/history/services, and deterministic regression/browser tests. Reproducible model scripts are `scripts/audit_saved_model_reliability.py` and `scripts/audit_sparse_case_outputs.py`; local API cases use backend `scripts/audit_local_case_journeys.py`.

Backups/evidence: `backend-preexisting.patch`, three initial/final Git status files, and `baseline-backend/` (original tracked code/artifacts, with the user's existing condition-information edits copied intact). The user's condition-information file still hashes to `21a5120d15422622bb92a83886f48691328b49d37d00de83aa971ba963e1404c`, identical to the initial backup. Existing untracked ML experimental scripts/schema and frontend images were preserved. Model/backend artifact hashes match; datasets were not destroyed or overwritten.

No PostgreSQL server was initially installed. A portable official EDB/PostgreSQL runtime was used on loopback port 55432. Only `respiracare_test` (temporary pytest schemas) and `respiracare_audit` (synthetic browser users/assessments) were written. No configured `.env` database was contacted or migrated. No local/global service installation was performed. Test servers were stopped after verification; retained runtime/evidence allows reproduction.

## Remaining limitations and next use

- Before running against an intended application database, review that target, apply Alembic migration `d42ea86c5170`, and reseed the symptom catalogue. These steps were validated only on isolated local databases; the configured application environment remains unchanged. See [assessment contract](../ucs31-madhaparia-backend/docs/assessment-contract.md).
- V1 now provides safety, clarification and abstention rather than unsupported disease guesses. V2 remains research-only; the 3-positive-feature guard does not validate a diagnosis.
- Real clinical data with reliable negative observations, independent COVID/rhinitis labels, held-out evaluation and appropriate calibration are needed before clinical reliability claims. No data was fabricated to fill these gaps.
- Rule-based NLP/emergency aliases cannot cover every phrase. Bilingual clinical/fluent-speaker review, broader clinical safety evaluation and demographic fairness evaluation remain necessary.
- Duration/severity/negative statements improve the recorded assessment and guidance; neither saved model was trained to make full use of them. V2 also loses pain-location information.
- Safety wording was checked against [NHS breathing guidance](https://www.nhs.uk/symptoms/shortness-of-breath/) and [WHO TB information](https://www.who.int/news-room/fact-sheets/detail/tuberculosis). No unverified local emergency number was added.

**No commits, pushes, remote branches, publishing or deployments occurred.** Existing repository branches and user work were preserved.

## Follow-up TB display recheck

The unchanged raw models still over-rank TB on sparse inputs. This was not corrected by retraining; the repair prevents unsupported scores from being displayed as a new disease assessment. Fresh targeted API verification passed15/15 tests (all12 supplied V1 cases plus3 sparse V2 cases). Cough alone, cough+fever, two-day cough+fever and the Swahili equivalents return no disease candidate under the limited-information policy. The retained final V1/V2 twelve-case API records contain zero TB candidates.

A remaining browser-cache defect was found and repaired: an unversioned old TB result could reopen for matching text/codes without requesting the repaired API. Fresh responses now use a versioned session cache; older caches are invalidated. Stored historical database records are preserved with uncertainty warnings. Added3 unit/service tests and1 real browser regression. Latest frontend90/90 tests,7/7 V1 browser journeys, lint and build pass. The browser regression specifically loads an old99.75% TB cache and verifies a fresh assessment has no prediction. The earlier V2 browser journey also passed; it was not rerun during this follow-up. All local test servers were stopped again. No commits/pushes/deployments occurred.
