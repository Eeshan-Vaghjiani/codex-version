> **Current default: V3 partial-evidence consultation (28 October 2026).** The V1/V2 policy below remains legacy documentation. New initialization selects `v3_partial_evidence`; it supports sparse symptom reports, explicit negative answers and up to five targeted questions, returning tentative ranked possibilities. See [the current improvement report](../../RESPIRACARE_IMPROVEMENTS.md) for activation, metrics, limitations and validation.

# Assessment API and safety policy

The application is a health-awareness research tool, not a clinically validated diagnostic service. Saved model scores are uncalibrated. Software regression tests do not establish diagnostic performance.

## Request lifecycle

1. `POST /nlp/map` first checks bundled warning aliases without database/model access. A warning returns `safety_status: urgent_review`, localized guidance, and no confirmation requirement. Routine extraction uses the seeded database catalogue.
2. `POST /symptoms/confirm` validates unique positive patient mentions. It retains explicitly absent/uncertain mentions separately. Rejecting a suggested symptom does not mean it is absent. Warning evidence cannot be removed with a checkbox.
3. `POST /predict` accepts `age` (strict integer 0–120), `sex` (`M`/`F`), original `text`, original `confirmed_codes`, optional `language` (`en`/`sw`), and `follow_up_answers` (at most three `{question_id, answer}` objects).
4. Each request re-extracts the original text and replays answers in order. Unknown, absent, present and unmentioned states remain distinct. Invalid/skipped/duplicate answers are rejected; a positive breathing-warning answer takes precedence over stale trailing answers.
5. `needs_follow_up` returns `follow_up_question: {id, text, options: [{value, label}], rationale}`. Submit the original text/codes and append the selected stable answer to the answer history. Questions stop after three accepted answers or when no relevant information remains.
6. `urgent_review` bypasses inference and ordinary questions. History storage failure cannot hide guidance. Severe breathing guidance uses no guessed local telephone number.
7. `insufficient_evidence` returns no disease candidates. V1 abstains because its serving representation conflates absent and unreported information and performs poorly on sparse projections. V2 also abstains below three supported positive evidence features. Three is a conservative research-display guard, not a validated medical sufficiency threshold.
8. V2 inputs with at least three supported positive features may return up to three **experimental pattern matches**, always with `uncertain: true`, a score limitation, and `clinical_validation: false`. No class is individually prohibited and raw scores are not rescaled or inflated.

Responses retain original `confirmed_codes`; `effective_confirmed_codes` includes accepted positive follow-ups. `assessment_context` contains `symptom_states`, `symptom_durations`, the cough/primary `duration`, `severity`, accepted answers, question IDs, language, model version and uncertainty reasons. Terminal results store context in PostgreSQL JSONB; list/detail history retain localized uncertainty and safety guidance.

## Features the models do not support

- V1 has no independent explicit-absence representation.
- V2 has absence columns, but no saved tree uses any of them. Negative answers are recorded and affect question selection; a negative column alone does not change its learned score.
- Duration and severity are preserved for advice, not model inputs.
- V2 drops location categories that distinguish headache from chest pain. Denying either location never implies that generic `E_53` pain is absent everywhere.
- V2 COVID-19 and allergic-rhinitis training extensions are synthetic and lack independently labelled evaluation cases.

See the sibling ML repository's `reports/autonomous_audit/MODEL_AUDIT.md` for frozen test metrics, per-class results, calibration, data overlap and provenance.

## Database change and startup

Migration `d42ea86c5170` adds non-null `prediction_sessions.assessment_context` with an empty-object default for existing records. No original records or datasets are deleted. After reviewing the intended database target, apply Alembic migrations and reseed the symptom catalogue (new aliases/sneezing). This audit applied migrations/seeding **only to isolated local audit/test databases**; the configured `.env` database was untouched.

If schema/connectivity is unavailable at startup, the app logs degraded readiness and keeps bundled emergency mapping available. Routine SQL failures return 503. Missing/corrupt model artifacts also return readiness errors instead of activating an alternative model. `/model/status` describes the active version, exact feature/class counts and lack of clinical validation.

## Validation commands

```powershell
# Use a disposable local PostgreSQL database; pytest creates/drops an isolated schema.
$env:TEST_DATABASE_URL='postgresql+psycopg://audit_user@127.0.0.1:55432/respiracare_test'
.\.venv\Scripts\python.exe -m pytest -q
# With a migrated/seeded, locally running audit API:
.\.venv\Scripts\python.exe scripts\audit_local_case_journeys.py --output ..\audit-artifacts\case-journeys.json
```

The local case runner permits loopback hosts only, registers a synthetic user, and saves assessments. It does not select/activate a model or alter clinical ground truth.

## Safety references

- [NHS shortness-of-breath guidance](https://www.nhs.uk/symptoms/shortness-of-breath/): severe breathing difficulty, gasping, choking, inability to speak normally, or blue lips require emergency attention. UK phone numbers were not copied into the app.
- [WHO tuberculosis facts](https://www.who.int/news-room/fact-sheets/detail/tuberculosis): prolonged cough and unexplained weight loss warrant medical attention; the app gives assessment advice without assigning a TB diagnosis from these symptoms.

English/Swahili wording was checked in software regressions. Professional clinical and fluent-speaker review remains necessary before real patient use. Rule-based aliases cannot guarantee recognition of every expression.
