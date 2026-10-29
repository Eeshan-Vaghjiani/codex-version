# CHANGELOG — Muse improvements, 2026-10-29 (base c04aca7)

## Final merge 2026-10-29: prompt-first, all-no fallback, Codex 292acf1/178a3a8 merge, 2 x 10,000-case sweeps

### Prompt-first: questions are truly optional (Eeshan's settled rule)
- `app/services/consultation.py` `next_consultation_question()` rewritten
  with the order documented in code comments: (1) safety (breathing)
  first, once — the only question allowed before a result is known;
  (2) severe severity stops, it goes to clinical assessment, not to
  more questions; (3) prompt-first stop: if the original prompt already
  gives an eligible primary or a family answer, return no more
  questions immediately — duration, severity and fatigue-pattern
  refinement must NOT delay a clear result; (4) context family: if the
  user already said "cold"/"flu", no model discriminator is left to ask;
  (5) only then, discriminators that would actually change the
  prediction or the action — for non-respiratory scope: fever, cough,
  sore throat, runny/blocked nose, in that order; for respiratory
  scope not yet clear: fatigue_pattern (changes the tiredness feature),
  weight_loss_intent (changes the weight-loss feature),
  symptom_duration only when a cough is reported (duration changes the
  action, not the model score), weight_loss for a prolonged cough,
  then the information-gain pool (0.02 nats, soft guide 5, hard
  ceiling 20, unchanged).
- Duration and severity are NO LONGER asked before a result for
  non-respiratory cases. That was the waste Eeshan reported: those
  questions are advice-only in V3 and do not change the prediction,
  yet they blocked the result. Tests that asserted the old sequence
  were updated and the change is recorded here, not hidden as a test
  fix: `test_muse_nonspecific.py` (new discriminator-only sequence),
  `test_kenya_patient_experience.py` (allowed question set, duration
  test renamed to assert duration is NOT asked first).
- Service errors are NOT swallowed by the prompt-first check: a
  missing selection policy still propagates as ServiceNotReady (503).
  The first version of this change swallowed it into a follow-up
  question and broke `test_missing_selection_policy...`; fixed before
  delivery, test passes again.

### Bug fixed in the prompt-first pass: answering "no" killed the family answer
- Answering "no" to the breathing safety question moved the common
  cluster from bucket 4:0 to 4:1/4:2, which is disabled for the same
  source-validation bound, and turned a clear family answer into a
  withheld blank — exactly the "questions lead to nothing" failure.
- Fix, in `app/ml/primary_selection.py` AND the ML copy (logic
  identical except the policy path): the narrow family exception now
  applies to ANY 4-present bucket disabled only for its
  source-validation bound, when the top is viral-family, >=0.75, gap
  >=0.20, and no dangerous condition is a close second. Still a
  family answer, never a specific disease name; absent evidence is
  already inside the ranking. Verified: cluster + breathing absent =
  family 83% moderate; cluster + fever absent = family 78%; cluster +
  both absent = family 86%.

### All-no fallback: a withheld result is always a useful result
- If the user answers "no" (or "not sure") to all follow-ups, the
  consultation ends and `build_primary_assessment()` gives the best
  answer from the ORIGINAL prompt: (a) a context cold/flu word gives
  the family answer (below); (b) tiredness + headache (+/- fever)
  gives the full non-specific screen (title, plain explanation,
  flu-like care, malaria-test step when fever is present, warning
  signs, 24-48 hour review), never blank, never a tumour name;
  (c) in general, withheld results carry guidance, never an empty
  screen. This was already the design for (b)/(c); the prompt-first
  rewrite makes it reachable without advice-only blockers, and the
  new tests prove it end to end at consultation level.
- Settled rule recorded here (Eeshan, 2026-10-29 13:56 EAT): NO disease
  name is ONLY for when the user answers the questions poorly / gives
  no usable information. NOT otherwise. If the user answers well on
  what was asked, the app must use those answers and give something.
  There is NO limit on what may be asked — the full catalogue may be
  used — as long as each question would change the answer, and a
  clear initial prompt asks nothing.

### "i have cold" recognition + context family answer
- `app/nlp/canonical_symptoms.json` and `app/nlp/english_aliases.json`:
  "i have cold", "have cold", "got cold", "got a cold", "having cold"
  and bare "cold" added as common_cold context aliases. Bare "cold"
  is safe: the longer "feel cold"/"feeling cold" chills aliases match
  first and occupy that span, so "I feel cold" still maps to chills
  only (tested). "I have cold" now maps to common_cold, exactly like
  "I have a cold" did.
- `app/services/primary_assessment.py`: when no model primary exists
  and the user said common_cold/flu_like, and no input guard
  (unsupported wording / severe severity) has withheld the case, the
  result is the family answer "Flu-like illness / common cold (viral
  upper respiratory infection)" with a family note, labelled as coming
  from the user's own words, with NO model match percent — there are
  no model features behind a context word, so inventing a percent
  would be dishonest. A model primary, when present, still wins.
  Decision status is possible_explanation / prediction_complete, so
  the frontend renders it (it requires a display/dual name, a policy
  version and that status).

### Codex 292acf1 / 178a3a8 merged (see COMPARISON_CODEX.md for the full record)
- Codex branch head at comparison time was `178a3a8` (2026-10-29
  13:44 EAT), whose parent is the assigned target `292acf1`
  (13:20 EAT). `178a3a8` is CHANGELOG only; `292acf1` is the only
  code change since `f423bde`.
- Taken, with credit: Codex's symptom-aware withheld guidance
  (`symptom_specific_advice()` in `consultation_guidance.py`, wired
  into `patient_guidance()` for withheld results at self-care/review
  level only). NOT taken: Codex's paracetamol lines and its
  antibiotics line — Muse never recommends a specific medicine; the
  adapted lines use rest/fluids/monitor wording. Codex's gap gate,
  5-question cap and "final: codex" decision were NOT adopted: they
  would regress Eeshan's settled prompt-first, uncapped-gathering,
  family-answer and guard rules. The disagreement is recorded in
  COMPARISON_CODEX.md, not papered over. Branches are the contact
  channel: Codex and Muse do not share a chat; the merged branch is
  the record of what was taken from each.
- Codex test counts (backend 372 claimed in 292acf1) were NOT re-run
  by Muse and are reported as Codex's claims.

### Sweep fixes from batch 1 (8 prompt-first failures) and alias gaps
- Initial-clear anchor + safety freeze, in
  `app/services/consultation.py`: `prepare_consultation()` computes
  whether the ORIGINAL prompt was already clear (eligible/family) and
  passes it to `next_consultation_question()`. If it was clear, only
  the safety question is asked, then the consultation stops — a
  follow-up "no" cannot reopen the queue. And for an initially clear
  case, a safety "no" is recorded in symptom_states but does NOT
  rewrite the model evidence (model_features/absent stay at the
  initial set), so the final result is the initial name. Without the
  freeze, the safety negative alone dropped clear cases below their
  bucket minimum and the result became withheld instead of the
  initial name. For cases that were NOT initially clear, all answers
  still count as model evidence, as before. Verified on all 8
  batch-1 failure cases: 1 question (safety only), final = initial
  name (COPD, pulmonary edema, Bronchiolitis, Bronchitis).
- Red-flag alias gaps found by batch 1: chest_pain_at_rest, stridor
  and drooling had NO Swahili aliases, and "chest pain even at rest"
  (the display name itself) was not an alias, so 18 red-flag-category
  cases withheld with "unsupported_information" instead of bypassing
  to urgent review. Fixed: EN alias "chest pain even at rest" added;
  draft SW aliases added for all three codes (unreviewed, as with all
  Kiswahili copy). Tests added.
- "I can breathe fine" understood, not left unmatched: EN aliases
  "can breathe fine", "breathe fine", "breathing fine", "can breathe
  normally", "breathing normally" and SW "napumua vizuri",
  "ninapumua vizuri", "naweza kupumua vizuri" added for
  shortness_of_breath, with a special case in `infer_symptom_status`
  (like the existing "sikohoi" case) returning "absent" for those
  phrases. Before this, "can breathe fine" was unmatched wording,
  which vetoed an otherwise clear result in
  `build_primary_assessment` (cluster + "I can breathe fine" withheld
  instead of family). After: cluster + "I can breathe fine" = family
  83% strong, ZERO questions; cold + "I can breathe fine" = context
  family, ZERO questions; "I can't breathe" still bypasses to urgent
  review. Existing negative tests ("I can breathe fine",
  "napumua vizuri", "no difficulty breathing" must not trigger
  safety signs) still pass.

### 10,000-case sweeps (auditable files, not chat claims)
- Runner: `reports/test_sweep_10000.py` (deterministic seed, real
  pipeline: confirm_symptoms -> prepare_consultation loop with the
  case's answer pattern -> build_primary_assessment). Analyser:
  `reports/analyse_sweep.py` (recomputes derived flags from raw CSV
  columns, so a runner definition bug cannot hide a failure).
- Batch 1 (`reports/test_sweep_10000_1.csv`, 10,000 cases, seed
  20261029, 357s): exact prompts 50, singles 1000, pairs 2200,
  triples 2200, quads 1000, common clusters 1200, red flags 700,
  negations 500, duration/severity 600, context 300, poor/unusable
  250. Final outcomes: red-flag bypass 6340, withheld-with-guidance
  2602, context family 247, model family 104, named primary 707,
  blank 0, errors 0. Sparse-serious violations 0 (7 neoplasm namings,
  all with weight loss present = specific support, so not guard
  violations). Prompt-first violations 8 (the cluster above, all
  "all-no"). Advice-only questions asked 0. Questions asked: mean
  1.42, zero-question 3454, >=10 questions 316 (all still withheld
  — see open decision below). Negation: 0 red-flag bypasses for
  all-no/2x-unknown negation cases (all-yes/mixed red flags there
  are safety "yes" answers, not negation failures). Unmapped texts
  229, all poor/unusable, all still withheld-with-guidance, never
  blank. Red-flag rate 63% is a sweep-design artefact, not a failure
  rate: random codes include red-flag codes (3007 confirm bypasses)
  and all-yes/mixed patterns answer "yes" to the safety question
  first (3333 follow-up bypasses) — answering yes to breathing
  difficulty correctly bypasses to urgent review.
- Batch 1 pattern bug, disclosed: "2x-unknown" answered
  duration/severity/fatigue/weight-loss questions informatively
  instead of "not sure". Fixed for batch 2. Batch-1 failure clusters
  do not depend on that pattern (the 8 failures were all "all-no").
- Batch 2 (`reports/test_sweep_10000_2.csv`, 10,000 cases, seed
  20261030, 237s): mix = 8 batch-1 regressions + 50 exact prompts +
  9942 fresh random cases. As run: blank 0, prompt-first violations
  0, sparse-serious violations 0, advice-only questions 0, errors 8
  — all 8 errors were the regression cases, caused by a sweep
  generator bug (age carried as a CSV string "30" instead of int,
  rejected by the V3 age-group lookup), NOT a product failure. Fixed
  by coercing age to int in the runner, and the 8 regressions were
  re-run auditably (`reports/test_sweep_10000_2_regressions_rerun.csv`):
  all 8 named, 1 safety question each, final = initial name. Corrected
  batch-2 totals: named 807, model family 44, context family 241,
  withheld-with-guidance 1916, red-flag bypass 6984, blank 0, errors
  0 (after the generator fix; the as-run CSV keeps the 8 errors
  visible and the rerun file is the correction, not a rewrite).
  Batch 2 also ran while the "can breathe fine" alias fix landed, so
  early batch-2 cases used pre-fix mapping for that phrase and later
  cases used post-fix mapping; batch-2 fresh cases are random code
  combinations and do not contain that phrase, so the batch-2 failure
  clusters are unaffected.
- Open decision for Eeshan (NOT silently changed): 316 batch-1 cases
  and 86 batch-2 cases asked >=10 questions and still withheld —
  all single/vague cases where the information-gain pool kept finding
  >=0.02-nat questions. The soft guide of 5 exists in code but is
  unenforced, per the uncapped-gathering authorisation. If Eeshan
  wants it, the pool can be capped at 5 after discriminators (his
  original 3-5 stop), and those cases would withhold after 5
  questions with the same final outcome. Ask him; do not change the
  cap here.
- Observation, NOT fixed (needs Eeshan's decision): strong band on
  <=2 model features in 267 batch-1 / 384 batch-2 cases, mostly
  single highly specific symptoms (vomiting after coughing ->
  Whooping cough, difficulty swallowing -> Epiglottitis, night
  breathlessness -> Acute pulmonary edema, hoarse voice -> Acute
  laryngitis, itchy nose -> Allergic sinusitis). Those are
  model-policy outcomes for specific symptoms, with
  professional-review guidance for the serious ones. A "never name
  strong on 1 feature" guard was NOT invented here: it would break
  specific-symptom journeys and needs his decision.
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

## Final pass, 2026-10-29 — non-specific output fix + Codex comparison and takes

### Non-specific input is never a blank output (urgent fix, Eeshan's exact cases)
- Root cause (verified, not guessed): "Tiredness and headache" maps to
  E_53 + E_89, neither in `RESPIRATORY_ANCHOR_FEATURES`, so
  `classify_primary` returns `non_specific_input` /
  `no_supported_respiratory_anchor`, primary None, BEFORE the ranking.
  The raw V3 ranking underneath is Pulmonary neoplasm 1.000 on those two
  features alone. The anchor gate is what blocks that tumour name — it
  was NOT removed, and must never be removed to force a name.
- `app/services/consultation.py`: the non-respiratory question sequence
  used to dead-end after fever/cough. It now also asks breathing
  difficulty (safety first), sore throat, and runny/blocked nose before
  giving up: general_duration → symptom_severity → fever → cough →
  breathing_difficulty → sore_throat → runny_blocked_nose → withheld.
- `app/services/primary_assessment.py`: every withheld V3 result now
  carries `withheld_title` ("No single respiratory condition can be
  named from these symptoms alone"), a plain `non_specific_explanation`
  for non-specific cases, care guidance (rest/fluids, temperature check
  for non-specific cases, malaria-test step whenever fever is present in
  Kenya, warning signs, 24-48 hour review), and `discriminator_questions`
  (cough, sore throat, runny/blocked nose, fever, difficulty breathing —
  only ones not already known) so the patient can answer and re-check.
  A "yes" to difficulty breathing on that screen goes to urgent review,
  never to an ordinary prediction.
- `src/pages/PredictionPage.jsx`: the withheld screen renders the new
  title, the plain explanation, and a discriminator form (Yes / No /
  Not sure per question). "Yes" symptoms are added to the confirmation
  and the assessment re-runs from the result form; "No" / "Not sure"
  add nothing, so they never silently become negatives.
- Second exact case: tiredness + headache + fever (mild) still has no
  respiratory anchor, so it still names nothing — correctly. Mild
  severity does NOT change the model (severity is advice-only in V3),
  so picking "mild" cannot unlock a name, and no name was forced. What
  changed is the output: full explanation + flu-like care + the malaria
  test note (fever in Kenya) + warning signs + 24-48 hour review +
  discriminator follow-ups. After adding cough + sore throat it resolves
  to Seasonal flu (influenza) as a single primary, low match (51%
  present-only; 64% moderate with breathing absent) — never Epiglottitis
  (raw top 0.216 on the 3-feature case) or neoplasm.
- Honest limit on the first case: adding cough + sore throat + runny
  nose resolves to the 4:0 family answer only when the tiredness is
  transient (the consultation drops a transient tiredness feature, so
  the remaining pattern is headache + cough + sore throat + runny nose,
  78% moderate). If the tiredness is persistent it stays in the
  evidence, the 5-feature pattern scores only 45%, and the case still
  withholds rather than being given a forced weak name. Both branches
  are tested; the withheld branch still gives full guidance.
- Tests: `tests/test_muse_nonspecific.py` (7 tests) and one new
  PredictionPage vitest (withheld screen renders title, explanation,
  discriminator questions, re-check button, no disease name).

### Taken from the Codex branch, with credit (codex-respiracare-improvements-2026-10-29, f423bde / 85ccf0e)
- Everyday EN/SW/Sheng aliases for existing codes (43 canonical alias
  additions): e.g. "nimechoka", "nimechoka sana", "ninachoka" →
  tiredness; "sina nguvu" is covered by the new weakness context code
  below; "koo linaniuma" → sore throat; "pua inatoka" → runny/blocked
  nose; "kichwa kinauma" → headache; "chest inauma" → chest pain;
  "nina sauti ya mluzi" → wheezing; "I feel cold" → chills;
  "having challenges breathing", "difficulty breathing at rest",
  "I can't speak" → shortness of breath (in a symptom box this is
  treated as speech/breathing difficulty, per the checklist; see
  LIMITATIONS for the trade-off); "ladha imepotea" → loss of taste.
- Four honest context codes with NO model features (Codex f423bde):
  weakness ("sina nguvu", "I feel weak", "weak"), dizziness
  ("kizunguzungu"), common_cold ("niko na cold", "kipooza"), flu_like
  ("I have flu", "influenza", "mafua makali"). Recognising the
  patient's words without inventing a disease, feature or diagnosis.
  Files: `app/nlp/canonical_symptoms.json` (now 46 codes),
  `english_aliases.json`, `swahili_aliases.json`.
- Sudden neurological change as an emergency flag (Codex 85ccf0e focal
  block, in `app/services/assessment_safety.py` + `app/main.py`):
  sudden one-sided weakness, face drooping, slurred speech →
  `sudden_neurological_change`, routed to emergency guidance even with
  no breathing flag. General weakness does NOT trigger it.
- Fuller COVID out-of-scope wording (Codex terminology
  `covid_scope_message`) in `health_guidance.py` COVID_SCOPE_NOTE:
  adds that influenza and COVID are different infections, severity
  alone cannot identify COVID, and taste/smell changes are not proof
  and are less reliable with newer variants. Kiswahili still draft.
- Tests: `tests/test_muse_codex_takes.py` (5 tests). One existing test
  assertion was updated for the intentional COVID wording change
  (`test_covid_note_on_taste_or_smell` now also accepts "not ruled
  out"); the behaviour it checks is unchanged, no test was deleted.
- Full comparison: see COMPARISON_CODEX.md in this repo root.

### NOT taken from Codex, deliberately (see COMPARISON_CODEX.md)
- Codex gap gate (0.15 gap / 0.60 floor, only 5-8-positive buckets
  enabled on its source-validation fold): fold-checked, but it withholds
  the approved 4:0 family cluster and has no sparse-serious guard, so
  adopting it would regress Eeshan's approved family fix. Muse keeps
  its 0.10 / 0.20 gap gate + family exception + sparse guard; Codex's
  validation protocol is the template for checking Muse's thresholds on
  a fresh fold (future work, not claimed here).
- Codex bronchitis display ("Chest infection / airway inflammation
  (bronchitis)"): decided format is "Chest infection (bronchitis)".
- Codex withheld-viral guidance recommending paracetamol: no specific
  medicine is recommended in this version.
- Codex 5-question cap: superseded by the uncapped-gathering
  authorisation (soft guide 5, hard ceiling 20, safety stops kept).
- Codex weakness-clarification question: a new safety pathway needing
  its own review; the free-text emergency detection above was taken,
  the question was not.
