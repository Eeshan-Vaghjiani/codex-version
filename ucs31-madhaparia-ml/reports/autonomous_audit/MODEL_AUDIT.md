# Frozen-model reliability audit — 27 October 2026

This records the initial V1/V2 audit. A subsequent request led to fitting the separate V3 partial-evidence model; see `../consultation_v3/README.md`. Statements below about no retraining apply to this initial audit phase.

The original datasets and both saved models were preserved. No model was retrained or recalibrated. Software repairs change input integrity, abstention and presentation; they do not improve the frozen models’ measured accuracy. The ML and backend copies of both models and their schemas/classes/features have matching SHA-256 hashes.

## Confirmed causes

- V1 uses 198 features and encodes both unreported and absent evidence as zero. It was evaluated on rich simulated profiles; sparse free text does not reconstruct those profiles. The original cough/fever TB score is reproduced at 99.75% for age 21, male, rather than inferred to be a frontend rounding error.
- V2 has 66 features: age, sex and present/absent columns for 32 binary symptoms. Its saved trees never split on any absence column (total absence feature importance 0). Negation can be preserved correctly without changing its score. Duration and severity are not trained features.
- V2 is a research prototype with 400 synthetic COVID-19 and 400 synthetic allergic-rhinitis examples; neither extension has independently labelled test cases. Full-profile high scores cannot establish clinical certainty.
- Headache and chest pain share generic E_53 pain plus different location categories. V2 excludes those categories, so it loses location detail. A negative location-specific symptom cannot establish general pain absence.
- V1 startup loading previously checked feature/class counts without verifying exact ordered metadata. Direct loader validation now rejects permutations/duplicates. Artifact failure is isolated from independent emergency request handling.

## Frozen test evaluation

No fitting or threshold tuning used this evaluation. The source is the original DDXPlus test partition, which has been evaluated historically; it is not a pristine or clinical holdout. Sparse results use deterministic nested random subsets (seed 20261027) of true source positive symptoms; every unmentioned symptom remains unknown. They test a synthetic input projection, not free-text or clinical accuracy.

| Model/input | Cases | Accuracy | Macro F1, fixed 21 classes | Top-label ECE |
|---|---:|---:|---:|---:|
| v1_full | 56,817 | 0.9944 | 0.9933 | 0.0091 |
| v2_full | 56,817 | 0.8920 | 0.8698 | 0.2265 |
| v1_full_no_exact_train_overlap | 53,595 | 0.9941 | 0.9933 | 0.0096 |
| v2_full_no_exact_train_overlap | 53,595 | 0.9010 | 0.8753 | 0.2400 |
| v1_sparse_1 | 56,816 | 0.1153 | 0.1090 | 0.3110 |
| v2_sparse_1 | 56,816 | 0.3022 | 0.3521 | 0.0629 |
| v1_sparse_2 | 55,547 | 0.2162 | 0.2049 | 0.3250 |
| v2_sparse_2 | 55,547 | 0.6064 | 0.5831 | 0.1988 |
| v1_sparse_3 | 49,801 | 0.2113 | 0.2192 | 0.3167 |
| v2_sparse_3 | 49,801 | 0.7711 | 0.7095 | 0.2568 |

Training contains 443,075 records and 421,066 unique raw inputs: 22,009 repeated raw inputs and 0 conflicting raw signatures. 3,222 of 56,817 test records exactly match a training input. Removal addresses exact matches only; near duplicates and simulation-generator leakage are unresolved.

Two- and three-symptom eligibility leave only 20 source classes represented (no laryngospasm cases). The fixed 21-class macro denominator retains its zero-support class; metrics over all 23 model labels are also saved separately. Per-class precision/recall/F1, confusion matrices, multiclass Brier score, log loss and ECE bin counts are provided in accompanying CSV/JSON files. The training-majority URTI baseline has test accuracy 0.15388.

## Preserved twelve-case model observations

The table records raw frozen-model observations with the original baseline NLP, age 21 and male. These outputs are not ground-truth diagnoses. Emergency and vague inputs must bypass ordinary inference; their observational scores are retained only for audit reproducibility.

| Case | V1 top/raw score | V2 top/raw score |
|---|---|---|
| 1 | Croup / 37.25% | Tuberculosis / 12.75% |
| 2 | Allergic sinusitis / 45.50% | URTI / 36.47% |
| 3 | Tuberculosis / 99.75% | Tuberculosis / 16.18% |
| 4 | Tuberculosis / 62.75% | Tuberculosis / 11.09% |
| 5 | Allergic sinusitis / 68.50% | Allergic sinusitis / 14.81% |
| 6 | Tuberculosis / 99.75% | Tuberculosis / 16.18% |
| 7 | Tuberculosis / 81.75% | Tuberculosis / 69.18% |
| 8 | Tuberculosis / 73.25% | Bronchospasm / acute asthma exacerbation / 20.34% |
| 9 | Whooping cough / 18.25% | Tuberculosis / 8.53% |
| 10 | Tuberculosis / 62.75% | Tuberculosis / 11.09% |
| 11 | Tuberculosis / 99.75% | Tuberculosis / 16.18% |
| 12 | Tuberculosis / 62.75% | Tuberculosis / 11.09% |

The matched demographic experiments evaluate 144 combinations: twelve inputs × two models × three ages (5, 21, 65) × two sexes. For cough and fever at age 21, V1 male/female scores are 99.75%/96.75%; V2 scores are 16.18%/16.45%. The claim that selecting male consistently yields approximately 99.5% is not reproduced. Differences arise from learned demographic splits, with V2 AGE/SEX_M impurity importances 0.091732/0.002283. These experiments do not establish demographic fairness. Equivalent English/Swahili positive and negative cases yield equivalent feature encodings.

## Repairs and executed verification

- Exact V1 feature/class ordering and unique-name integrity validated at load time. V2 metadata reports research status, absence-column learning limitations and unsupported duration.
- ML predictor bounds age to 120 and validates unique schema/classes; encoder rejects boolean/invalid demographics; score summarizer rejects duplicate/empty labels. Raw scores remain unchanged.
- ML predictor always flags the actual artifact as experimental/uncertain; provisional generic score-separation rules do not establish clinical certainty.
- Baseline entire ML suite: 97 tests passed plus 5 subtests. Integrated suite after model/NLP repairs: 201 tests passed plus 5 subtests; 104 added tests (79 NLP, 21 model-input integrity, 4 evaluation-metric correctness). See ml_final_tests.xml.
- Backend test migration preserves malformed-request, authentication, readiness, ownership, history and feedback goals while updating intentional V1/sparse abstention and dense V2 research-output contracts. Six affected files: 33 tests passed against isolated local PostgreSQL. Original eight loader tests plus added integrity/startup cases were separately exercised; final overall backend totals belong to the integrated engineering report.

## Reproduce

```powershell
.\.venv\Scripts\python.exe scripts\audit_saved_model_reliability.py
.\.venv\Scripts\python.exe scripts\audit_sparse_case_outputs.py
.\.venv\Scripts\python.exe -m pytest tests -q
```

Source: scripts/audit_saved_model_reliability.py, scripts/audit_sparse_case_outputs.py, scripts/train_v2_23class_prototype.py, scripts/build_v2_dataset.py and models/rf_v2_23class_prototype_manifest.json. See baseline_nlp_cases.json and nlp_case_comparison.json for extraction before/after; final application-level regression outcomes are reported by the backend integration audit. No commits, pushes or deployments were performed. Software test success is not clinical validation.
