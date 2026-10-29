# CHANGELOG — Muse improvements, 2026-10-29 (base c04aca7)

## Follow-up 2026-10-29: dual naming + common flu-like fix + uncapped symptom gathering

### Dual naming, stable format (simple Kenyan-known name + medical name, every time)
- `app/data/patient_terminology.json`: all 21 V3 classes now display as
  simple (medical) in EN and SW, enforced by `patient_term()` which raises
  if a display name lacks the parenthesised medical name. Changed entries:
  COPD, allergic sinusitis, bronchospasm/asthma, croup, pneumonia (SW),
  pulmonary neoplasm, tuberculosis (EN). Examples: "Chest infection
  (bronchitis)" / "Maambukizi ya kifua (bronchitis)", "Seasonal flu
  (influenza)" / "Influenza (mafua ya influenza)" (bare "mafua" is never
  used alone for confirmed influenza), "Lung infection (pneumonia)" /
  "Maambukizi ya mapafu (pneumonia)", "TB (tuberculosis)" / "Kifua kikuu
  (TB)", "Abnormal growth in the lung (pulmonary neoplasm)". Medical
  class names are unchanged; only presentation changed.
- `app/services/patient_terminology.py`: returns `dual_name` (= display
  name) and `simple_name` alongside `medical_name`.
- `ucs31-madhaparia-frontend/src/components/PossibleExplanations.jsx`:
  the single result title is now `dual_name`; the old separate
  "Medical name:" line was removed (it duplicated the dual title), and
  the TB note and family note are rendered when present.
- `app/services/primary_assessment.py`: when TB is named, the result
  carries `tb_note` (EN+SW): bacterial, testable, treatable, having TB
  does not mean having HIV, nothing to be ashamed of.
- Tests: `tests/test_muse_dual_and_family.py` (dual format for all 21
  classes in both languages, spot checks, TB note). One existing frontend
  test that asserted the old separate medical-name line was updated to
  assert the new dual title instead.

### Common flu-like fix
- `app/nlp/canonical_symptoms.json`, `app/nlp/english_aliases.json`:
  "running nose" added as an alias for runny_blocked_nose (previously
  only "runny nose" / "nose is running" were recognised).
- `app/ml/primary_selection.py` (+ ML copy, logic identical except the
  policy path): narrow 4:0 family exception, chosen route — NOT a general
  4:0 enablement. When the 4:0 bucket is disabled only for its
  source-validation risk bound, and the top score is >=0.75, the top-two
  gap is >=0.20, the top condition is in the viral upper-respiratory
  family (URTI, Influenza, Viral pharyngitis, Acute rhinosinusitis), and
  no dangerous condition is a close second, the result is a FAMILY
  answer, not a specific disease name. A 4-symptom close case still
  withholds (verified: fever+cough+tiredness+sore throat, top 51%).
- `app/services/primary_assessment.py`: family answer rendered as
  "Flu-like illness / common cold (viral upper respiratory infection)"
  (SW draft equivalent), with a family note stating it is a family of
  common viral illnesses, not one confirmed disease and not a diagnosis,
  plus flu-like care steps, the COVID out-of-scope + test note, and a
  match band from the top viral-family score. It is NOT a new model
  class and adds no trained condition.
- Sparse-serious guard, in `primary_selection.py` AND as defence in
  depth in `primary_assessment.py`: Pulmonary neoplasm is never named on
  <=3 present features without a specific supporting feature (weight
  loss E_162, coughing blood E_45, chest pain at rest E_14, breathing
  difficulty E_66, heavy/night sweats E_50); Tuberculosis is never named
  as strong on the same sparse, non-specific input. Guarded cases
  withhold the serious name and get professional-review guidance.
  Chronic cough + weight loss still names TB moderate (specific feature
  present), so that journey is unchanged.
- Withheld screens still useful: `patient_guidance()` now always adds a
  malaria-test step when fever is present in Kenya, on top of the
  existing rest/fluids, warning-sign and 24-48 hour review wording.
- Tests: `tests/test_muse_dual_and_family.py` (alias, family answer,
  close case, neoplasm guard, TB-strong guard, withheld care steps,
  family/TB/guard through the assessment layer).

### Uncapped symptom gathering (authorised 2026-10-29)
- `app/services/consultation.py`: the old hard cap of 5 questions is now
  a soft guide (`SOFT_QUESTION_GUIDE = 5`); the hard ceiling is 20, a
  safety stop only. Information-gain (>=0.02 nats), eligible, 2x
  "I don't know", and red-flag stops are unchanged and still end the
  consultation earlier in practice.
- Question pool expanded from 9 to 25 codes, all already in the repo
  catalogue with trained V3 features: chills, intense coughing fits,
  vomiting after coughing, night breathlessness, wheeze after coughing,
  difficulty swallowing, hoarse voice, nasal discharge, loss of smell,
  itchy nose/throat, itchy eyes, worse lying down, worse with exertion,
  activity fatigue, loss of appetite, plus the original 9. No new
  disease, symptom code or model feature was invented. Chest pain and
  pain on deep breathing are deliberately NOT routine pool questions
  (a "yes" needs clinical assessment, not a model question); they
  remain mappable from free text. A "yes" to night breathlessness sets
  urgent review, like breathing difficulty.
- Alias coverage expanded for the new pool (EN + SW, existing codes
  only): e.g. "nakosa pumzi usiku" (night breathlessness), "macho
  yanawasha" (itchy eyes), "kamasi za kijani" (nasal discharge),
  "siwezi kunusa" (loss of smell), "siwezi kufanya shughuli zangu"
  (activity fatigue).
- Tests: `tests/test_muse_uncapped_followup.py` (5-is-soft-guide,
  withheld fever+cough resolves to URTI moderate after a sore-throat
  "yes", pool uses only existing codes, new aliases, new questions
  exist in EN and SW).
- Before/after for a withheld case: fever + cough alone withholds
  (uncertain). With the old 5-cap, a case with 5 questions already
  asked stopped there. Now the consultation still offers sore throat;
  answering "yes" gives URTI, 70% moderate. Note honestly: the
  information-gain stop still ends some sparse cases (e.g. cough +
  tiredness alone, gains ~0) — uncapped means the count no longer
  blocks a useful question, not that every case can be resolved by
  asking more.

## Backend (`ucs31-madhaparia-backend/`)
- `app/nlp/breathing_tier.py` (NEW): graded tier + one severity check. Tests: `test_muse_p0_improvements.py`, `test_muse_journeys.py`, live `/nlp/map` smoke.
- `app/nlp/symptom_mapper.py`: attaches `breathing_tier` to shortness_of_breath flags.
- `app/services/assessment_safety.py`: attaches tier; "severe chest pain" added as red flag.
- `app/services/health_guidance.py`: tiered urgent guidance (`emergency`/`urgent`/`None`) + `COVID_SCOPE_NOTE`.
- `app/main.py`: `/nlp/map` and `/predict` return `breathing_tier` and tiered guidance.
- `app/ml/primary_selection.py` + `ucs31-madhaparia-ml/inference/primary_selection.py` (kept AST-identical): `patient_match` band, `MIN_CLOSE_GAP=0.10`, `DANGEROUS_CLOSE_GAP=0.20`, gap gate.
- `app/services/primary_assessment.py`: attaches match fields to the primary only; withheld message/reason (EN+SW); COVID note; dangerous-close-second forces professional review.
- `app/data/patient_terminology.json`: bronchitis plain alias; `covid_scope_note`.
- `app/nlp/canonical_symptoms.json`, `english_aliases.json`, `swahili_aliases.json`: `loss_of_taste` (no features); "lost my sense of…" and safety phrasing aliases.
- `app/services/consultation.py`: `MAX_UNKNOWN_ANSWERS=2` stop.
- `app/services/consultation_guidance.py`: duration advice (inserted after the primary care step, so `health_guidance` stays the care recommendation).
- `app/ml/artifacts/v3_primary_selection.json`, `v3_primary_scope.json` (+ ML `models/` copies, byte-identical): `model_sha256` recomputed to match the shipped V3 artifact; scope `base_policy_sha256` recomputed. Integrity checks unchanged.
- `app/ml/artifacts/*.joblib` restored (V1 53M, V2 8.8M) so the full app and existing V1/V2 tests run; V1/V2 are NOT the patient path.
- `tests/test_muse_p0_improvements.py` (NEW, 18 tests), `tests/test_muse_journeys.py` (NEW, 21 tests).

## Frontend (`ucs31-madhaparia-frontend/`)
- `src/services/patientResult.js`: `getPatientMatch()` added; `getPatientPrimary` contract unchanged.
- `src/components/PossibleExplanations.jsx`: renders the single rounded match + band + label, never a raw score.
- `src/pages/PredictionPage.jsx`: urgent title graded by tier; withheld message/reason + COVID note rendered; "What we understood" + Edit link to `/symptoms/confirm`; next steps capped at 3 shown; Edit control in result actions.
- `src/pages/HomePage.jsx`: promise reworded to "one possible condition and how strongly it matched".
- `src/services/__tests__/patientResult.test.js`: match-band test added.

## ML (`ucs31-madhaparia-ml/`)
- `inference/primary_selection.py`: same gap gate as backend (AST parity preserved).
- `models/v3_primary_selection.json`, `models/v3_primary_scope.json`: same hash fix as backend.
