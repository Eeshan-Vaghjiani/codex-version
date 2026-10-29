# V3 gap-gate check — frozen before computing the new fold results

29 October 2026. No model fitting and no test-set threshold tuning.

- Keep the V3 artifact, 21 classes, 34 features, original bucket score minima and
  respiratory-scope overrides unchanged.
- Candidate gap: **0.15 on the normalised relative score difference**, from the
  requested 10–15-point separation design, not selected on test results.
- Additional presentation eligibility: at least two reported native positive
  features and top relative match >=0.60. These are engineering candidates, not
  established clinical thresholds; the independent checks below may disable them.
- Use the existing source-validation reporting partition (complete 198-feature
  signatures %4 ==3), after removing training overlap and retaining one label-blind
  row per complete profile. Reserve %8 ==3 for this new gate's bound checks and
  %8 ==7 for reporting. Neither subset fitted the V3 parameters, model-selection
  settings or original bucket thresholds/bounds. Verify disjoint signatures.
- **Disclosure:** these are newly separated validation folds, not newly collected
  patients. The parent reporting partition contributed aggregate metrics to older
  reports. This is not a pristine external replication or Kenyan clinical study.
- Freeze one candidate, apply the existing score/scope rules plus the candidate
  gap/floor, and check each of the 48 evidence-count buckets. One-sided exact
  binomial upper error bound, familywise delta .05/48, target simulated-source
  selective error <=.10. Disable every failing bucket; no retry/retune against
  this fold. A minimum bound/check count is enforced by that bound, not guessed.
- Freeze the generated gap artifact, linked to the model and base-policy hashes,
  before calculating reporting-fold or test metrics. Missing/invalid artifacts
  never authorise naming. A changed gate requires a new evaluation/protocol.
- Report top-1/top-3 at 1/2/3 symptoms, selective accuracy AND coverage, correct
  named primary across all cases, and per-class recall. Do not treat rejected
  cases as correct or inherit accuracy guarantees after arbitrary extra filters.

Warning-sign routing and free-text/context guards remain separate and can
withhold more results. Passing these simulated-source checks does not establish
patient probabilities, real-world triage safety, Kenyan accuracy or language
comprehension. Previously published test results are not used to choose this gate.
