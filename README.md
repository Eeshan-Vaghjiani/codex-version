# RespiraCare — Muse improvements (2026-10-29)

Branch: `muse/respiracare-improvements-2026-10-29`. Base: git `c04aca7` (codex-version, main).
This is Muse's parallel implementation for comparison with Codex's version. It is NOT
clinically validated for patients in Kenya. All model numbers are simulated DDXPlus only.

## Live model
V3 partial-evidence, 21 conditions, 34 features. V1/V2 joblibs are kept in the repo
for internal comparison and existing tests only; they are NOT the patient path.
`/predict` falls back to empty + uncertain (never a V2 top-3) when V3 is inactive.

## What changed (P0, all in code)
1. **Patient score, restored honestly** — `primary_selection.py` now emits a rounded
   whole-percent `match_percent_rounded` + `match_band` (low <60, moderate 60–79,
   strong 80+ only with a clear gap), labelled "Model match, not a probability."
   Never a 2-decimal percent, never a probability, never overall accuracy.
   `HomePage.jsx` was reworded to match exactly what the result page shows.
   Forbidden patient keys from `test_kenya_patient_experience.py` are still forbidden;
   `match_percent_rounded` / `match_band` are the only new patient numbers.
2. **Graded breathing tier** — new `app/nlp/breathing_tier.py`, wired into
   `symptom_mapper.detect_safety_signs`, `assessment_safety`, and `main.py`
   (`/nlp/map` and `/predict` return `breathing_tier` + graded guidance).
   Emergency = can't breathe / gasping / cannot speak / difficulty at rest:
   emergency screen, no further questions, no prediction.
   Urgent = difficulty only on exertion + can speak a full sentence, after exactly
   one severity check (at rest or only on exertion, can you speak a full sentence?).
   "I can breathe fine" / "napumua vizuri" do NOT trigger.
3. **Close-gap gate** — `primary_selection.py` (backend + ML copies, kept AST-identical):
   dangerous close second (pneumonia, TB, tumour, pulmonary edema, pneumothorax,
   epiglottitis) with gap < 0.20, or any gap < 0.10, withholds the name
   (`dangerous_close_second` / `close_alternative`) and forces professional review
   for the dangerous case. Thresholds are conservative and UNVALIDATED on a fresh
   fold (see LIMITATIONS.md). In practice the real V3 distribution is extremely
   peaked, so the bucket threshold withholds most close cases before this gate.
4. **Abstention wording** — withheld/uncertain results say, EN + SW: cannot name one
   condition, this does NOT mean you are fine, it does NOT rule out any condition,
   check again in 24–48 hours, seek care sooner if worse, plus a reason line.
5. **COVID out of scope** — stated in `patient_terminology.json` (`covid_scope_note`)
   and on the result screen whenever taste/smell loss, a sinusitis/flu-like result,
   or a withheld result is involved. COVID is NOT predicted; a test is recommended
   on exposure or loss of taste/smell; a sinusitis/flu-like result does NOT rule
   out COVID. Loss of taste is a recognised symptom NOTE with no model features
   (advice-only, like duration/severity). Smell loss never produces a COVID label.
6. **Terminology** — bronchitis = "Chest infection (bronchitis)" /
   "Maambukizi ya kifua (bronchitis)". Seasonal-flu wording and the bare-mafua
   warning are kept. Kiswahili copy is draft, unreviewed by a clinician.
7. **Safety recognition fixes found by the journeys** — "severe chest pain" is now
   a red flag (checklist item; baseline only flagged "sudden severe chest pain");
   natural phrasings added: "coughing a lot of blood", "lips turned blue",
   "feel confused", "lost my sense of smell/taste".
8. **Follow-ups** — cap 5 + 0.02-nat stop kept; added the 2x "I don't know" stop
   in `consultation.py`. Safety screen first is the existing breathing-first order.
9. **Duration advice** — `consultation_guidance.py`: 2–3 days = acute thinking
   (flu/viral, COVID possible, acute chest infection, early pneumonia, malaria test
   if fever in Kenya); >2 weeks cough = chronic workup (TB, asthma, COPD).
   Duration/severity are advice-only, NOT model features (test proves it).
10. **Result screen order** — urgency banner → single result + band → what we
    understood + Edit (back to `/symptoms/confirm`, keeping selections) → what to
    do next (max 3 steps shown) → one short disclaimer. No disease list, no second score.
11. **Baseline bug fixed** — the frozen V3 policy's `model_sha256` did not match the
    shipped V3 artifact, so `classify_primary` failed its own integrity check in
    the baseline. The implementation recomputes the hash (policy + scope, backend
    and ML copies kept byte-identical). The check itself is unchanged.

## Run it
Backend (needs PostgreSQL + Alembic migrations + seeded catalogue/model version,
as in the original README; `TEST_DATABASE_URL` for tests):
```
cd ucs31-madhaparia-backend
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --port 8000
```
Frontend (needs `VITE_API_BASE_URL`, as the baseline vite config requires):
```
cd ucs31-madhaparia-frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run build   # or npm run dev
```

## Defence one-pager
- Patient flow: text → what we understood (correctable) → follow-ups (max 5,
  safety first) → safety → ONE possible condition + rounded match band, or withheld.
- Live model: V3 partial-evidence, 21 classes, simulated DDXPlus only, NOT
  clinically validated for patients in Kenya.
- Abstention trade-off (simulated, from the baseline Kenya report): ~91% selective
  accuracy on named cases, ~50% coverage overall, 0% coverage at 1 symptom,
  ~46% correct primary over all cases. Always report coverage WITH selective accuracy.
- Never quote V1 99.44% or V2 89% as app accuracy. Never present a score as
  "you X% have it". COVID is out of scope; graded breathing and the close-gap
  gate are the new safety changes; the gap threshold is unvalidated (see LIMITATIONS.md).
