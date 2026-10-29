# Changelog - 2026-10-29

Starting point: `c04aca7`. Work confined to this repository; no external organisation
repo accessed. Push authorised to `codex-respiracare-improvements-2026-10-29`;
`main` and deployment untouched.

## Fixes following the audit and confirmation screenshot

Application code changed to resolve the audit's software defects (no model
retrained, no disease gate relaxed). Shared negation scope so intrinsic loss
phrases ("no sense of smell", "sina nguvu") cannot deny neighbouring symptoms;
the independent safety detector uses the same context, so missed infant fever
is now caught before routine mapping. Old history projections recheck warning
signs from the original description/age. Discriminator "Yes" answers re-map and
server-confirm the updated description instead of trusting stale local codes.
A replay of the same 10,000 distinct descriptions now passes **10,000 / 10,000**
(was 7,045 / 2,955); the frozen V3 model and its source metrics are unchanged.
[Fixes report](audit-artifacts/AUDIT_FIXES_2026-10-29.md) and
[fixed replay](audit-artifacts/UNIQUE_10000_FIXED_2026-10-29.md).

## Subsequent 10,000-case audit (application left unchanged)

Real API audit: **7,045/10,000** distinct descriptions passed every declared
software check; **2,955** had mapping failures, including **10** missed immediate
infant-fever bypasses. “No sense of smell” leaks negation to other reported
symptoms. An additional **1,000 unfamiliar inputs** produced no forced diagnoses.
A strict **10,000-distinct-effective-input** simulated-source check measured
95.19% specific-name accuracy **at 26.17% coverage**, not clinical accuracy.
These results supersede any implication that passing the smaller suites made
the system patient-ready. No model/threshold/application fixes were made during
the audit. [Full report](audit-artifacts/UNIQUE_10000_2026-10-29.md).

## Earlier implementation and verification

| Change | Main files | Checks |
|---|---|---|
| V3 whole-percent model-match contract; no legacy probability conversion; honest conditional HomePage wording | backend `primary_assessment.py`; frontend `patientResult.js`, `PossibleExplanations.jsx`, `PredictionPage.jsx`, `HomePage.jsx` | `test_patient_safety_v4.py`, `PatientSafety.test.jsx`; existing single-primary/history tests |
| COVID explicitly outside V3; taste/smell testing advice; bronchitis chest-infection alias; unchanged flu/TB/pneumonia distinctions | `patient_terminology.json`, `consultation_guidance.py`, result page | terminology and required-journey tests |
| Emergency vs exertional breathing; one severity check; negative/subject handling; Kiswahili and bundled safety-only aliases | both `symptom_mapper.py` and NLP dictionaries; `assessment_safety.py`, `assessment.py`, `main.py`, symptom input/result pages | backend safety tests; ML `test_pending_gap.py`; real browser journeys |
| Fail-closed gap gate, dangerous-alternative review; **no invented threshold** | both `primary_selection.py`; vectorized `evaluate_primary_selection.py` | gap/overlap unit tests and serving parity |
| Official DDXPlus v15 restored (CC BY 4.0, checksums verified); V3 reproduced exactly from all 443,075 training rows; 2,000-per-class cap confirmed as V2 only | ML `scripts/restore_ddxplus.py`, ML tests | `TRAINING_PROVENANCE_2026-10-29.md`; source data and processed cohorts stay ignored |
| Predeclared 0.15 gap + 0.60 floor checked on a separate source-validation fold; 24/48 buckets enabled; no test-set tuning | ML `scripts/validate_gap_gate.py`, `docs/GAP_VALIDATION_PROTOCOL.md`, both `primary_selection.py` | `test_gap_validation.py`, `reports/gap_validation/`; reporting/test folds recomputed; sparse buckets remain withheld |
| Everyday-language understanding: weakness/typo/Kiswahili `sina nguvu`; concept-aware negation; Kiswahili durations; generic tiredness not "constant"; weakness clarification (general vs sudden one-sided → emergency) | both `canonical_symptoms.json`, `english_aliases.json`, `swahili_aliases.json`, `symptom_mapper.py`; `consultation.py`, `assessment_safety.py` | `test_everyday_weakness.py`, `test_conversation_flow.py`; browser everyday journeys |
| Scope-aware advice: duration alone no longer names a respiratory cause; generic tiredness/weakness gets neutral rest/hydration/review guidance; unresolved safety screen never names | `consultation_guidance.py`, `primary_assessment.py` | conversation-flow and guidance tests; browser journeys |
| Patient-controlled health-worker summary with copy; whole-percent match preserved in history | frontend `patientResult.js`, `PredictionPage.jsx` | `PatientSafety.test.jsx`; real browser copy/history journey |
| Everyday phrasing: "running nose", "feel cold"/"feeling cold" (chills), "throat pains"; loss of taste recognised and drives COVID-testing advice | both `canonical_symptoms.json`, `english_aliases.json`, `swahili_aliases.json` | `test_everyday_weakness.py`, `test_conversation_flow.py` |
| Withheld viral-cold pattern now gives actionable guidance (viral cold, 5-7 day review, COVID test consideration) instead of a bare "no output" | `consultation_guidance.py`, `primary_assessment.py` | `test_conversation_flow.py`; live API verified |
| Everyday-language expansion: Sheng/Kiswahili phrasings for tiredness (`nimechoka`), chest pain, headache, wheezing, sore throat, runny nose, body aches, night sweats; plus three honest context symptoms (`dizziness`, `common_cold`, `flu_like` - features `[]`, never model evidence) so a stated cold/flu/dizziness is understood and gets plain guidance instead of "nothing" | both `canonical_symptoms.json`, `english_aliases.json`, `swahili_aliases.json`; `consultation_guidance.py`, `primary_assessment.py` | `test_everyday_kenyan_phrases_are_understood`, `test_cold_or_flu_claim_is_context_not_model_evidence`, `test_cold_and_flu_claims_get_actionable_guidance`; ML 412 passed, backend 371 passed; live API verified |
| Symptom-aware withheld guidance: sparse (1-3 feature) cases stay withheld but "what to do next" is now tailored to the reported symptoms (headache+fever red flags, cough, wheezing, sore throat, chest pain, night sweats, body aches, tiredness) instead of near-identical generic advice | `consultation_guidance.py`, `primary_assessment.py` | `test_symptom_aware_guidance_for_withheld_sparse_case`; backend 372 passed; live API verified |
| Never-blank withheld + optional discriminator questions: a withheld result always carries a clear title, a plain explanation, care guidance and tappable "do you also have" questions (cough, sore throat, runny nose, fever, breathing) to re-run; breathing is no longer forced first for a non-respiratory report (severe chest pain stays a safety-screen question, breathing is a later discriminator) | `primary_assessment.py`, `consultation.py`, frontend `PredictionPage.jsx` | `test_withheld_result_is_never_blank_and_offers_discriminators`, `test_non_respiratory_report_does_not_open_with_breathing`; backend 374, frontend 124 passed; live API verified |
| Family-only viral answer for four-present patterns, including negative follow-up answers; never a specific virus or percentage; history preserved | both `primary_selection.py`, `primary_assessment.py`, frontend family label | real API/history regression, family/boundary ML tests, browser history journey |
| Simple + medical names for all 21 classes; original COVID scope message retained | `patient_terminology.json`, `patient_terminology.py` | every-class bilingual terminology test |
| Sparse-serious guard; expanded 24-code question pool; soft guide 5 / hard ceiling 20 in both service and API schema | `consultation.py`, `main.py`, both selection files | beyond-five replay, ceiling, catalogue-feature and night-breathlessness warning tests |
| Additive everyday aliases from Muse mirrored into serving/research dictionaries; corrected Kiswahili flu-like wording (not bird flu) | both NLP dictionaries, guidance service | mapper regressions and bilingual guidance tests |
| Safety first; 0.02-nat, two-unknown and no-change-to-action stops retained | `consultation.py` | consultation and safety tests |
| Explicit non-reassuring abstention; result-page correction; duration/severity visible; stale policy/cache invalidation | `primary_assessment.py`, frontend result/input/history pages and cache service | API/UI correction and abstention tests; 14 original browser scenarios retained |
| Acute vs chronic advice without changing scores; prolonged cough/weight-loss retained | `consultation_guidance.py`, `consultation.py` | duration-band/evidence invariance tests |
| Honest model identity and disclaimer; V2 historical only | root/project READMEs, `/model/status`, app footer, `health_guidance.py` | model-status and frontend communication tests |
| Removed tracked generated dist from index; preserved ignore rules; test discovery excludes executable experiment scripts | `.gitignore`, ML `pytest.ini` | final git hygiene check; no tests deleted or missing-data failures hidden |

## Comparison with the parallel `muse` branch — final decision

Selected features ported with credit from Muse `d11800d` / `9e48792`, not a blanket
branch merge: never-blank withheld output, optional discriminator taps, family
answers, dual names, sparse-serious guard, longer gathering and additive aliases.
Codex retains its provenance work, everyday context symptoms, tests and frozen
**checked 0.15 gap / 0.60 floor** disease gate (24/48 buckets). Muse's general
0.10/0.20 close-gap gate was **not** adopted.

The family-only exception adopts Muse's **0.75 score / 0.20 gap** thresholds.
It is **not independently fold-checked**; disease-gate accuracy/coverage does not
validate it. No bucket was enabled and no model retrained. Cached consultations
and saved patient-policy versions are invalidated for the changed flow.

Final checks: **ML 423 + 5 subtests / backend 381 / frontend 125 / Edge browser 46**.
Lint and production build passed. See the validation addendum for limitations.

Tests whose old expectations contradicted the requested safety-screen order or
new abstention policy were updated explicitly, not deleted. The retained
informative coughing-fit scenario now requires source-gap abstention (its sparse
bucket did not pass the checked bound). The information-gain boundary test uses
isolated hypothetical actionable outcomes so the separate no-change-to-advice
stop cannot mask the 0.02-nat assertion.

Baseline/final counts and remaining failures: [validation record](audit-artifacts/VALIDATION_2026-10-29.md).
Evaluation and historical simulated numbers: [evaluation note](audit-artifacts/SIMULATED_EVALUATION_2026-10-29.md).
Was the model trained on only 2,000 records? [provenance check](audit-artifacts/TRAINING_PROVENANCE_2026-10-29.md).
