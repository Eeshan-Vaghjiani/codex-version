# CHANGELOG — Muse improvements, 2026-10-29 (base c04aca7)

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
