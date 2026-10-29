# V3 partial-evidence consultation model

This subsequent repair replaces blanket sparse-input abstention with ranked research possibilities from a separately fitted model. Original datasets, V1 and V2 artifacts remain intact. No clinical diagnosis labels or transcript data were invented.

## What was trained

A missing-evidence likelihood model was fitted to all 443,075 authentic-labelled DDXPlus respiratory training records, covering the 21 original source conditions. It estimates empirical source class priors and positive/negative evidence likelihoods. Unknown user symptoms contribute no likelihood. Explicit no answers now affect inference; old V1/V2 scores could not learn negative answers. The schema retains 32 binary native evidences plus forehead-pain and upper-chest-pain location indicators, with locations conditioned on generic pain when it is known. Generic headache must not be converted to forehead pain without explicit location information.

A declared validation search compared no demographics, age groups and age-plus-sex with two shrinkage strengths and five temperatures. It selected age groups, shrinkage 1000 and temperature 0.75 by mean validation log loss. Sex is excluded and provably does not change scores. Temperature was fitted on source validation, never selected to make example phrases produce attractive scores. No disease is selectively hidden, boosted or prohibited.

DDXPlus generates complete simulated evidence; the authors describe supplying all experienced evidence and answering additional questions negatively. That supports negative labels for complete simulated records, while unmentioned user symptoms remain unknown. See the [primary DDXPlus paper, sections 3.2–3.3](https://papers.nips.cc/paper/2022/file/cae73a974390c0edd95ae7aeae09139c-Paper-Datasets_and_Benchmarks.pdf) and [official schema documentation](https://github.com/mila-iqia/ddxplus/blob/main/README.md).

The source deliberately alters disease rates and is not a Kenyan prevalence dataset. All ranking scores remain dataset-relative research outputs; the app cannot turn them into clinical probabilities. COVID-19 and allergic-rhinitis extension labels lack authentic source ground truth and are absent from the new 21-class training universe; original V2 remains unchanged for comparison.

## Independent evaluation

Source grouping uses label-independent complete 198-feature signatures. Training-overlap validation profiles are removed, and signature parity separates tuning (26,477 records) from validation reporting (26,445). The final test is opened after selection is frozen; training/validation-overlap test profiles are excluded, leaving 53,386. All masked versions of one source profile stay in its original group. This prevents exact represented-profile leakage; it cannot establish independence from the synthetic data generator or exclude every near duplicate.

One, two, three and eight mean **up to k native positive feature observations**, retaining every source case with at least one supported positive. They are nested masks. Positive reports are identical with and without the three explicit negative observations. Multiple native features can describe one clinical symptom. These metrics must not be compared to older studies that excluded cases with fewer than k positives without accounting for their different cohorts.

| Final test input | Top-1 accuracy | Top-3 recall | Macro F1, 21 classes | ECE |
|---|---:|---:|---:|---:|
| 1 positive 0 negative | 0.3660 | 0.6844 | 0.3321 | 0.0417 |
| 2 positive 0 negative | 0.5334 | 0.8689 | 0.5190 | 0.0510 |
| 3 positive 0 negative | 0.6604 | 0.9483 | 0.6656 | 0.0657 |
| 3 positive 3 negative | 0.7269 | 0.9649 | 0.7378 | 0.0210 |
| 8 positive 0 negative | 0.7812 | 0.9703 | 0.7602 | 0.0838 |

Per-class precision/recall/F1 and confusion matrices are saved for every validation/test setting. See evaluation.json for log loss, selection candidates, source counts and overlap removals.

## Matched baseline comparison and tradeoffs

| Same final-test masks | V2 top-1 / top-3 | V3 top-1 / top-3 | V2 / V3 log loss |
|---|---:|---:|---:|
| 1 positive 0 negative | 0.2754 / 0.6414 | 0.3660 / 0.6844 | 2.1479 / 1.6396 |
| 2 positive 0 negative | 0.5733 / 0.8662 | 0.5334 / 0.8689 | 1.4351 / 1.0057 |
| 3 positive 0 negative | 0.7530 / 0.9614 | 0.6604 / 0.9483 | 1.0102 / 0.6713 |
| 3 positive 3 negative | 0.7530 / 0.9614 | 0.7269 / 0.9649 | 1.0102 / 0.5971 |

V3 improves one-feature ranking and model log loss throughout, and learned negatives improve subsequent assessments. V2 retains higher top-1 accuracy on two/three positives and slightly higher top-3 recall on three positives. V3 is not universally superior on every metric. Its intended gains are missing-state integrity, useful sparse rankings, explicit-negative learning, interpretable evidence associations, measured uncertainty and question utility.

## Question utility and bounded questioning

Question utility recomputes the actual predictor under hypothetical yes/no answers; generative likelihoods weight the outcomes. Because temperature scaling breaks exact Bayesian consistency, this is explicitly a heuristic entropy utility, not clinical triage or diagnostic certainty. Safety checks take priority.

On 2,000 validation source profiles, the 0.02-nat engineering stop policy reduced mean model questions from 3.000 to 2.5945 (13.5%) while measured top-3 recall stayed 0.877; top-1 changed 0.621 to 0.620. Alternative 0.01/0.05 policies are reported transparently. These thresholds are not medical sufficiency cutoffs. They control the value of another model question only.

On a separate 2,000-profile final-test rollout, top-3 recall rose 0.701 → 0.780 → 0.8575 → 0.885 after zero through three informative questions; top-1 rose 0.362 → 0.530 → 0.6015 → 0.6165. Source records, rather than invented answers, supplied each yes/no response. This classification experiment does not validate clinical interviewing or triage and does not simulate the emergency-stop policy.

## Example model observations

At age 21, before follow-ups:

| Native evidence | Ranked conditions |
|---|---|
| cough | URTI, Viral pharyngitis, Bronchitis |
| fever | URTI, Viral pharyngitis, Influenza |
| cough fever | URTI, Viral pharyngitis, Influenza |
| cough no fever | Viral pharyngitis, Chronic rhinosinusitis, Allergic sinusitis |
| runny nose sore throat generic pain | URTI, Influenza, Bronchitis |
| cough weight loss | Tuberculosis, Pulmonary neoplasm, Acute rhinosinusitis |

These are observed outputs, not required diagnoses. In particular, cough with weight loss retains TB and pulmonary-neoplasm possibilities; the application must route relevant risk or emergency signs appropriately. English/Swahili text interpretation and final multi-turn UI behavior are verified separately through backend/frontend tests.

## Artifacts and reproduction

- `models/v3_partial_evidence.json`: fitted likelihoods, selected parameters, native feature definitions, provenance and evaluation metadata.
- `inference/v3_predictor.py`: portable pure-Python runtime; backend copy changes only the artifact path. It returns supporting and contradicting **data associations**, not causal explanations.
- `scripts/train_v3_partial_evidence.py`: deterministic training, selection, source grouping and final evaluation.
- `scripts/evaluate_v3_consultations.py`: matched legacy comparisons and question rollouts.
- `scripts/audit_v3_source_priors.py`: empirical conditional frequencies and an explicitly labelled uniform-prior counterfactual.
- `tests/test_v3_partial_evidence.py`: 58 new behavior/integrity/metric-consistency cases.
- `ml_final_tests.xml`: complete ML run at this stage: 333 passed, 5 subtests passed.

```powershell
.\.venv\Scripts\python.exe scripts\train_v3_partial_evidence.py
.\.venv\Scripts\python.exe scripts\evaluate_v3_consultations.py
.\.venv\Scripts\python.exe scripts\audit_v3_source_priors.py
.\.venv\Scripts\python.exe -m pytest tests -q
```

No commits, pushes or deployments were performed. Passing software tests and simulated-data metrics do not constitute clinical validation.
