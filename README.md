# RespiraCare

**Live model: V3 partial-evidence, 21 conditions, 34 features; simulated DDXPlus
only; not clinically validated for patients in Kenya. V2 is not live.**

RespiraCare is a React frontend, FastAPI backend and ML research project for
respiratory health awareness. It provides guidance, not a diagnosis or a
substitute for a qualified healthcare professional. It considers only a limited
set of respiratory conditions. Everyday English, Kiswahili and Sheng phrasings
are understood (tiredness, chest/head/throat pain, runny nose, body aches, night
sweats, and stated cold/flu/dizziness as context only). Kenyan clinician and
patient comprehension review remain pending.

**Latest stress-audit warning:** 10,000 distinct-text API cases exposed a negation
bug that can mark positively reported fever absent, including missed infant-fever
warning routes. This version is **not ready for patient deployment**. See the
[full audit and measured coverage](audit-artifacts/UNIQUE_10000_2026-10-29.md).

## Current safety decision — 29 October 2026

**Specific disease names require the checked V3 bucket + scope + gap policy.** The official source
data is now restored locally, publisher checksums verified, and the current V3
parameters reproduced exactly from all **443,075** respiratory training rows. The
historical **2,000-per-class cap belongs to V2 only**, not V3. See the
[training provenance check](audit-artifacts/TRAINING_PROVENANCE_2026-10-29.md).

A predeclared 0.15 relative-score gap and 0.60 match floor were checked on a
separate 6,479-profile source-validation fold, with **no test-set threshold
tuning**. **24 of 48 evidence buckets passed** the declared source error bound;
the rest stay disabled. Only the 5–8 positive-feature buckets passed this
experiment; this is **not** a clinical "five symptoms" rule. Sparse cases still
receive no name, and no arbitrary 50% / 10% rule is used. The source-validation
parent partition had previously contributed aggregate reporting metrics: this is
**not** newly collected or external patient validation. See the
[frozen protocol](docs/GAP_VALIDATION_PROTOCOL.md) and
[current evaluation](ucs31-madhaparia-ml/reports/gap_validation/evaluation.json).

The selected-result contract supports one primary with a rounded whole-percent
**model match** from V3's relative ranking. This is **not a probability, diagnosis,
or overall accuracy**. Withheld and urgent results show no score. An eligible
richer pattern now displays one actual V3 primary and match; sparse patterns
remain withheld. HomePage states this conditional selection, rather than
promising a score/name for every non-urgent assessment.

**Separate family-only answer:** a four-present viral upper-respiratory pattern
can return **“Flu-like illness / common cold”**, including after negative answers.
It names no particular virus and shows no match percentage. The adopted Muse
0.75 score / 0.20 gap rule is **not independently fold-checked** and is not covered
by the checked disease-gate metrics above. No disease bucket or model artifact
was changed to enable it. All 21 model classes use simple + medical names.

## Patient flow

1. English, Kiswahili or mixed free text; show extracted present, absent and
   uncertain symptoms. Another person's symptoms are not patient evidence.
2. Reported red flags bypass prediction. Inability to breathe/speak, gasping or
   difficulty at rest leads to immediate hospital casualty advice, no questions.
   Ambiguous breathing difficulty gets at most one combined exertion/speech
   severity check, alongside same-day advice. Exertional difficulty with normal
   full-sentence speech remains urgent same-day care, never a routine prediction.
3. Safety/context screening precedes routine discriminators. Breathing is first
   for respiratory reports, later for non-respiratory reports. Five questions is
   a soft guide, not a cutoff; the hard ceiling is **20**, with a 24-code routine
   pool. Stop below 0.02-nat expected
   information gain, after two unknown answers, when no answer changes the
   primary/care action, at a separated 80%+ match, a family answer, or a red flag.
4. One possible explanation only when every gate permits, otherwise explicitly:
   **not enough information; nothing is ruled out; monitor 24–48 hours and seek
   care sooner if worsening**. Persistent/severe symptoms need professional
   review, not a wait-and-see instruction. Urgency always takes priority.
5. Result-page extraction, duration and severity can be corrected and rechecked.
   Old cached/saved policies cannot silently restore old labels or scores.

Duration/severity guide advice and questions, **not model features**. Keep the
14-day prolonged-cough boundary and weight-loss question. Acute fever advice
includes asking about malaria testing in Kenya. Bronchitis is explained as chest
infection (bronchitis), retaining the medical name; bare mafua does not
confirm influenza.

**COVID is not predicted by V3.** It has no COVID class, taste feature, test-result
or exposure input. Exposure, a positive test or loss of taste/smell warrants
COVID testing/clinical advice. A flu-like or sinusitis pattern does not rule it
out. Severity alone cannot identify COVID. V2 is not enabled to supply a label.

## Evidence and defence

- [Defence one-pager](README_DEFENCE.md)
- [Changes and test coverage](CHANGELOG.md)
- [Baseline, final checks and limitations](audit-artifacts/VALIDATION_2026-10-29.md)
- [Simulated-source results and fresh-evaluation blocker](audit-artifacts/SIMULATED_EVALUATION_2026-10-29.md)
- [Training provenance: was the model trained on only 2,000 records?](audit-artifacts/TRAINING_PROVENANCE_2026-10-29.md)
- [Manual cases and recorded browser outcomes](RESPIRACARE_MANUAL_TEST_CASES.md)

Historical reports and V1/V2 joblibs are retained for provenance, **not live
performance claims**. Report selective accuracy **with coverage**, never a
standalone headline accuracy. No result establishes Kenyan patient accuracy.

## Local checks

Use Python with `ucs31-madhaparia-backend/requirements-dev.txt` installed and Node
24.15+ (the locked frontend dependencies require it). No .env is needed for tests.

- Backend: set `TEST_DATABASE_URL` to a **disposable PostgreSQL** database, then
  `python -m pytest tests` from `ucs31-madhaparia-backend`.
- ML: `python -m pytest` from `ucs31-madhaparia-ml`. The DDXPlus source files are
  restored locally by `python scripts/restore_ddxplus.py`; raw data and processed
  cohorts stay ignored, never committed.
- Frontend: `npm ci`, `npm test`, `npm run lint`, `npm run build` in
  `ucs31-madhaparia-frontend`.
- Browser: migrate and seed an isolated backend database (including the default
  V3 model), start the API, set `E2E_API_URL`, then `npm run test:e2e`.
  Playwright uses local Edge. These are software journeys, not clinical trials.

Do not commit .env, virtual environments, node_modules, dist or raw DDXPlus CSVs.
The previously tracked frontend dist is removed from the index and ignored.
No remote push, deployment, Drive merge or credential access was performed.
