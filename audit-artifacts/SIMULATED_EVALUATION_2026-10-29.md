# Simulated-source evidence — not Kenyan patient accuracy

## Source validation checked on a separate fold

The official DDXPlus v15 files were restored locally (publisher checksums
verified) and the V3 parameters reproduced exactly from all 443,075 respiratory
training rows; see
[TRAINING_PROVENANCE_2026-10-29.md](TRAINING_PROVENANCE_2026-10-29.md). A
predeclared 0.15 relative-score gap and 0.60 match floor were checked on a
separate 6,479-profile source-validation fold per
[the frozen protocol](../docs/GAP_VALIDATION_PROTOCOL.md), with **no test-set
threshold tuning**. **24 of 48 evidence buckets passed** the declared source
error bound; the rest stay disabled. Only the 5–8 positive-feature buckets passed
this experiment; this is not a clinical "five symptoms" rule.

The **test** fold now reports **0% coverage** for 1–3 positive features (sparse
patterns withheld) and **93.8–96.3% selective accuracy / 47–50% coverage** for the
passed 5–8 positive-feature buckets; the reporting fold agrees. Correct named
primary over all cases is **0%** for the sparse buckets. The source-validation
parent partition had previously contributed aggregate reporting metrics: this is
**not** newly collected or external patient validation, and it is not Kenyan
clinical accuracy. Do not describe withheld cases as correct predictions.

The new gate still disables naming wherever the checked bucket does not pass.
Current policy is not "0% by construction" any more; it is "conditional on the
checked gate". Do not substitute older model accuracy for current performance.

## Retained pre-change DDXPlus simulation only

The following are read from the committed `reports/kenya_patient_experience/`
`baseline_frozen.json`, `evaluation.json` and `baseline_test_*_per_class.csv`,
not a rerun. They concern 53,386 simulated eligible test records under the older
masking scheme. They are **not Kenyan patient accuracy or clinical validation**.

### Underlying V3 ranking (not patient output)

| Reported symptoms | Top-1 | Top-3 |
|---|---:|---:|
| 1 | 36.60% | 68.44% |
| 2 | 53.34% | 86.89% |
| 3 | 66.04% | 94.83% |

Top-3 is an evaluation measure only; the patient never receives a ranked list.

### Earlier Kenya single-primary policy, before the pending gap gate

| Reported symptoms, no negatives | Selective accuracy | Coverage | Correct named primary / all cases |
|---|---:|---:|---:|
| 1 | Undefined (no names) | 0.00% | 0.00% |
| 2 | 91.44% | 24.89% | 22.76% |
| 3 | 91.22% | 50.24% | 45.83% |

These older coverage/accuracy pairs must not be attributed to the modified gate.

### Underlying per-class top-1 recall on sparse input

| True source class | 1 symptom | 2 symptoms | 3 symptoms |
|---|---:|---:|---:|
| Pneumonia | 22.28% | 46.16% | 69.25% |
| Tuberculosis | 7.18% | 19.89% | 36.68% |
| Bronchitis | 1.22% | 21.15% | 44.24% |
| Influenza | 14.18% | 37.17% | 57.71% |

These are unselected model recall figures, not sensitivity of the whole app and
not clinical reassurance. The fallback policy names no class.

## What is needed before enabling a numeric gap

Supply the source files locally without adding them to git. Retain the frozen V3
model and bucket thresholds. Predeclare the candidate-gap selection procedure and
simulated-source error/coverage targets. Select on a tuning partition; freeze it;
check on a fresh labelled fold whose complete profiles do not overlap training,
tuning, prior inspected/calibration folds or final test. Account for repeated
profiles and evidence-count buckets. Disable failures without retuning against
that fold. Only then report untouched-test top-1/top-3 at 1/2/3 symptoms, selective
accuracy WITH coverage, correct primary/all, and sparse per-class recall. A later
Kenyan clinical/language validation study is still required.

Behaviour tests of a hypothetical gap (0.12 in an isolated mocked unit fixture)
are **not** evidence that 0.12 or any other cutoff is validated. No numeric gap is
active in this build. Additional review for an unresolved dangerous runner-up is
a conservative software precaution and may over-refer.
