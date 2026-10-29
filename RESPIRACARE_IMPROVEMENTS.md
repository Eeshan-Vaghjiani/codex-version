# RespiraCare — Improvements and Validation

> Historical V3 implementation report. The later [Kenya patient experience report](KENYA_PATIENT_EXPERIENCE_REPORT.md) supersedes the ranked-three patient presentation described here. Current patient results use a selective single-primary policy, with uncertainty when a name cannot be supported.

**Completed: 28 October 2026**

## Outcome

RespiraCare now supports a useful consultation flow for everyday English, Swahili and mixed-language symptom descriptions. A user can start with **“I have a cough and fever”**, answer a few targeted questions, and receive ranked **possible explanations**, reasons from the supplied information, and practical next steps. Common supported symptom reports no longer end in blanket “insufficient evidence.” Vague input still requests clarification, and emergency signs still take priority.

This work includes a **new fitted partial-evidence model**, not just a change to the displayed disease name. TB was not selectively removed or prohibited. The results remain tentative: the application is not clinically validated and cannot reproduce a clinician's examination or diagnostic tests.

## 1. What changed in the model

The previous models mishandled incomplete conversational information. V1 treated unmentioned symptoms like absent symptoms, while V2's absence columns were never learned. V2 also used class-balanced training that distorted the source-condition mixture. That contributed to very high TB scores for simple reports.

A separate **V3 partial-evidence likelihood model** was trained on all **443,075 original DDXPlus respiratory training records**, covering the original **21 labelled conditions**. These are simulated patients, not real clinical records. Original V1/V2 artifacts and datasets were preserved.

V3:

- Learns the source class frequencies and symptom likelihoods rather than treating every condition as equally frequent.
- Uses only information actually reported: unmentioned evidence remains unknown and contributes no positive or negative observation.
- Learns explicit yes/no evidence from the complete simulated source profiles. A patient's “no fever” now genuinely changes the assessment.
- Uses 32 native binary evidence features plus two explicitly reported pain-location features. Generic headache is no longer assumed to mean forehead pain; generic chest pain is no longer assumed to mean upper-chest pain.
- Uses validation-selected age groups. Sex was excluded from the selected predictor, so changing male/female alone does not change V3 scores.
- Returns dataset-relative ranking scores, not clinically validated probabilities or measures of illness severity.

Selection compared demographic modes, shrinkage and temperature using a separate tuning partition. The selected settings are age groups, shrinkage 1000 and temperature 0.75. They were selected by validation log loss, not to force an attractive result for a supplied phrase.

The dataset authors describe complete simulated evidence and negative answers to additional questions; this supports negative observations **within the simulated source**. It does not justify treating an unmentioned user symptom as absent. Sources: [DDXPlus paper, sections 3.2–3.3](https://papers.nips.cc/paper/2022/file/cae73a974390c0edd95ae7aeae09139c-Paper-Datasets_and_Benchmarks.pdf), [official dataset documentation](https://github.com/mila-iqia/ddxplus/blob/main/README.md).

## 2. Follow-up questions now improve the assessment

The sequence follows a history-taking structure:

1. Extract the patient's actual report and its present, absent, uncertain and unmentioned states.
2. Check urgent warning signs independently of the model.
3. Clarify relevant context such as cough duration and whether reported weight loss was intentional.
4. Select a useful missing symptom question using the model's expected information gain.
5. Record the controlled answer and use it in the next assessment.
6. Stop after at most five questions, when no relevant questions remain, or when another model question has little expected benefit.

Questions have stable IDs, English/Swahili wording, numbered options and an explicit “not sure” choice. Answer replay validates ordering and prevents duplicates or skipped questions. Unknown weight-loss intention no longer produces a duplicate weight-loss question. Reloading resumes a current consultation; old prediction/abstention caches are invalidated.

The 0.02-nat question-utility stop policy is an engineering policy, **not a medical certainty threshold**. In a 2,000-profile validation experiment, it reduced average model questions from 3.00 to 2.59 while observed top-three recall stayed 87.7%. That experiment measures model-question utility, not clinical interviewing quality.

Duration, onset and severity guide questions and advice. The available source does **not** support learning duration/severity as disease-prediction features; those values were not fabricated for training.

## 3. An actual tested example

This is an illustrative **synthetic software journey**, not a real doctor's transcript or clinical ground truth.

**Initial report:** “I have a cough and fever.” Age 21.

| App question | Test answer |
|---|---|
| Are you having difficulty breathing now? | No |
| How long have you had the cough? | Less than 3 days |
| Is your throat sore? | Yes |
| Do you hear a whistling sound when breathing out? | No |
| Are you coughing up coloured phlegm, or more phlegm than usual? | No |

**Actual returned possibilities:** Upper Respiratory Infection (URTI), Influenza, Bronchitis. The interface shows them as tentative possibilities, with shared uncertainty and next steps. Percentages are not presented as a headline diagnosis/confidence bar.

Before follow-ups, the actual V3 ranking for cough and fever at age 21 is URTI, Viral pharyngitis, Influenza. Answers can change the ranking. Serious conditions can still appear when the supplied evidence supports comparing them; TB cannot safely be declared impossible from a short text description.

Recorded example: [example-consultation.json](audit-artifacts/consultation-v3/example-consultation.json).

## 4. NLP and patient-language improvements

A curated patient-language corpus now has **80 deterministic software cases**, in addition to the existing regression tests. It exercises plausible everyday descriptions; it is not a measured distribution of actual user messages and is not a new clinically labelled dataset.

Improvements include:

- English, Swahili and mixed-language negation, uncertainty and patient/other-person context.
- Common cough, fever, body-ache, nasal, throat and sweating expressions, conservative spelling matching and conjugated Swahili phrases.
- Separate dry/productive cough context, onset text, explicit duration and preserved vague durations without invented numeric bounds.
- Sneezing preserved as sneezing rather than wheezing.
- Tight chest preserved as its own context rather than being converted to an exhaled wheeze.
- Generic phlegm retained without falsely claiming the source's more specific “coloured or increased sputum” feature.
- Generic temperature wording no longer automatically establishes fever.
- Weight-loss intention clarified before using the involuntary-weight-loss model feature.
- Exact forehead/upper-chest locations distinguished from generic headache/chest pain.

Updated catalogues now contain 41 canonical entries; some are deliberately context/safety-only rather than trained model features. Seeder reconciliation retires only an explicit reviewed list of formerly managed unsafe aliases. Unknown custom database aliases are preserved.

## 5. Results, explanations, history and safety

The frontend now displays equally styled, ranked **Possible explanations** cards rather than one dominant diagnosis and confidence bar. It includes the assessment summary, reported details used in the model comparison, details that reduced that ranking, limitations and practical next steps. Association labels explicitly refer to the **model comparison**, not clinical confirmation. Raw scores are available only inside collapsed details.

Current results and patient/admin history share this presentation. Stored context includes original symptoms, explicit negatives, accepted follow-up answers, duration, severity, language and the actual model version. Old historical records remain preserved with uncertainty wording.

Emergency recognition remains independent of inference, confirmation checkboxes and ordinary questions. Severe breathing warnings display guidance immediately. A positive breathing-warning answer overrides stale trailing replies. Missing models, unavailable schema and failed history storage cannot override a recognized warning. Relevant English/Swahili emergency paths were tested.

Safety and general advice were informed by [NICE first-presentation respiratory assessment](https://www.nice.org.uk/guidance/ng237/chapter/Recommendations), [NICE acute-cough guidance](https://www.nice.org.uk/guidance/ng120/chapter/Recommendations), [CDC common-cold information](https://www.cdc.gov/common-cold/about/), and [WHO TB information](https://www.who.int/news-room/fact-sheets/detail/tuberculosis). No unverified local emergency number, prescription or definitive diagnosis was added.

## 6. Measured model results

Complete, label-independent 198-feature signatures were used to remove represented-profile overlap between training and evaluation groups. Tuning used 26,477 profiles; separate validation reporting used 26,445. Final testing used 53,386 profiles after training/validation overlap removal. All masked versions of a source profile remain in their source group. Final test data was not used for parameter selection.

“Positive” below means up to that many native positive evidence observations. The three-positive inputs are identical when comparing zero versus three explicit negative answers.

| Final V3 test input | Top-one accuracy | True source label in top three | Macro-F1 |
|---|---:|---:|---:|
| 1 positive, no negatives | 36.60% | 68.44% | 0.3321 |
| 2 positives, no negatives | 53.34% | 86.89% | 0.5190 |
| 3 positives, no negatives | 66.04% | 94.83% | 0.6656 |
| 3 positives, 3 explicit negatives | 72.69% | 96.49% | 0.7378 |

In a separate 2,000-profile test rollout, top-three recall increased from 70.1% before model questions to 88.5% after three informative questions. Actual source profiles supplied those test answers.

On matched one-positive inputs, old V2 top-one/top-three performance was 27.54%/64.14%, versus V3's 36.60%/68.44%. V3 improves model log loss across the compared settings and can use negative answers. **V3 does not win every metric:** V2 retains higher top-one accuracy with two/three positive observations. This is a useful partial-evidence model, not proof of general clinical superiority.

Per-class precision/recall/F1, confusion matrices, ECE, log loss, selection details, comparisons and rollouts: [model report](ucs31-madhaparia-ml/reports/consultation_v3/README.md).

## 7. Final software verification

| Layer | Executed and passed |
|---|---:|
| ML/NLP/model/evaluation suite | 339 tests, plus 5 subtests |
| Backend/API/PostgreSQL suite | 226 tests |
| Frontend component/service suite | 104 tests |
| Real V3 Edge browser journeys | 10 tests |
| **Total current verification** | **679 tests, plus 5 subtests** |

Final runs have zero failures or skipped cases. Frontend lint and production build passed with an explicit local API URL. The backend emits an existing Starlette/httpx test-client deprecation warning; it did not prevent validation.

The browser journeys use real login, Vite, FastAPI, PostgreSQL and the saved model, without mocked HTTP. They cover sparse English/Swahili reports, negation, follow-ups, reload, saved history, emergencies, vague input and rejection of obsolete caches. An earlier cough-only browser assertion wrongly assumed unmentioned fever was absent; it was corrected to preserve the actual distinction, and the final ten-journey run passed.

All twelve originally supplied cases remain in regression tests and were rerun through the current local API. Ten non-emergency, non-vague cases completed with ranked possibilities; the breathing-warning case stopped for urgent guidance, and the vague case requested clarification. No expected diagnosis was fabricated for those synthetic phrases. Different follow-up answers legitimately produce different rankings, including serious alternatives.

Evidence:

- [Backend JUnit](audit-artifacts/consultation-v3/backend-final-tests.xml) and [test log](audit-artifacts/consultation-v3/backend-final-tests.txt)
- [ML JUnit](ucs31-madhaparia-ml/reports/consultation_v3/ml_final_tests.xml)
- [Browser log](audit-artifacts/consultation-v3/browser-final-tests.txt)
- [Frontend log](audit-artifacts/consultation-v3/frontend-final-tests.txt)
- [All twelve current API journeys](audit-artifacts/consultation-v3/twelve-v3-journeys-final.json)
- [Frontend validation notes](ucs31-madhaparia-frontend/docs/consultation-v3-validation.md)

## 8. Main implementation files

| Area | Files |
|---|---|
| New model/training | `ucs31-madhaparia-ml/scripts/train_v3_partial_evidence.py`, `inference/v3_predictor.py`, `models/v3_partial_evidence.json` |
| Model evaluation | ML `scripts/evaluate_v3_consultations.py`, `scripts/audit_v3_source_priors.py`, `reports/consultation_v3/` |
| New backend flow | Backend `app/services/consultation.py`, `v3_prediction.py`, `consultation_guidance.py`, `app/main.py` |
| Serving/model registration | Backend `app/ml/v3_predictor.py`, `app/ml/artifacts/v3_partial_evidence.json`, `app/db/register_v3_model_version.py`, `seed_model_version.py` |
| NLP and catalogue | Both repositories' `nlp/symptom_mapper.py` and catalogue/alias JSON; backend `retired_aliases.json`, `seed_symptom_catalog.py` |
| Results/history | Frontend `src/components/PossibleExplanations.jsx`, prediction/input/confirmation/history pages and prediction cache service |
| New regressions | ML `test_patient_language_corpus.py`, `test_v3_partial_evidence.py`; backend `test_v3_consultation.py`, `test_symptom_catalog_retirement.py`; frontend component/service/browser suites |

The serving and evaluated V3 JSON files match by SHA-256:

`ae709ef5ddf6dd7a101fe426b610c3e83ef58aa93cb895ca13e7500220dc889c`

A runtime-parity regression verifies that serving and evaluation functions match. Source snapshots and patches from before this iteration are retained in `audit-artifacts/consultation-v3/source-backup/` and `*-before.patch`. The user's existing condition-information edits, original datasets, V1/V2 artifacts, experimental scripts and images were preserved.

## 9. Activating the new version

The isolated local audit database was migrated, reseeded and explicitly switched to V3 for verification. The default model-initialization command now selects V3. Existing V1/V2 records and artifacts remain available; old test fixtures explicitly select their legacy versions.

For an intended application environment, first set/verify its database configuration, then run from the backend repository:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.db.seed_symptom_catalog
.\.venv\Scripts\python.exe -m app.db.seed_model_version
```

Restart the backend and serve/rebuild the frontend with its intended API URL. `/model/status` should report `v3_partial_evidence`, 34 features and 21 conditions. Do not confuse an older deployed site or saved historical record with this current local implementation.

No configured `.env` database was contacted or changed during this work; all database writes were to isolated local audit/test databases. No commits, pushes, remote branches, publishing or deployments occurred.

## 10. Remaining limitations

- This is simulated-data research. Neither these metrics nor the passing software tests establish clinical validity.
- Dataset class frequencies are deliberately altered by the generator; they are not local population prevalence. Rare or serious conditions can still be ranked, particularly after additional negative answers. TB has not been universally ruled out or hidden.
- The app covers 21 source conditions. It cannot exclude other causes, including conditions without reliable training labels. The prior synthetic COVID/allergic-rhinitis extensions were not relabelled as authentic data.
- A single symptom remains nonspecific. Even a ranked differential may be wrong; the app does not replace examination, vital signs or diagnostic tests.
- Duration/severity are retained for questions and guidance but are not learned disease-model features. Real, trustworthy duration-labelled clinical data would be needed to change that honestly.
- Rule-based language handling cannot recognize every expression. Clinical review, fluent-speaker review, demographic fairness evaluation and independent real-patient validation remain necessary before real patient use.

Local audit API and PostgreSQL test services were stopped after final verification. The tested V3 registration remains saved in the isolated audit database for reproducibility.
