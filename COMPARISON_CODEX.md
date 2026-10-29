# Muse vs Codex vs git baseline — final comparison, 2026-10-29

Branches compared (all on top of git baseline `c04aca7`, main unchanged):
- Muse: `muse/respiracare-improvements-2026-10-29` (this branch)
- Codex: `codex-respiracare-improvements-2026-10-29` at `f423bde`
  (two commits: `85ccf0e` improvements, `f423bde` everyday aliases)
- Baseline: git `c04aca7` — V3 partial-evidence live, single primary,
  no score shown, no graded breathing tier, no gap gate, no family
  answer, no sparse guard, 5-question consultation cap, no everyday
  context codes.

Codex's own validation record (`audit-artifacts/VALIDATION_2026-10-29.md`
on its branch) reports: backend 360 passed, ML 395 passed, frontend
124 passed (21 files), 45 Edge browser journeys. Its commit message
says 366 / 398; the validation doc's 360 / 395 are used here. Those
counts were NOT re-run by Muse; they are Codex's claims. Muse's counts
in this branch were re-run here: backend 350 passed, frontend 117
passed, vite build succeeds, 21 function-level journeys passed.
Browser journeys did not run on the Muse side.

## Per-item verdicts

| Item | Git baseline (c04aca7) | Muse (this branch) | Codex (f423bde) | Winner / final takes |
|---|---|---|---|---|
| Score shown | No score at all, but HomePage promised "confidence information" | Single rounded whole-% match band, labelled model match not probability/diagnosis/accuracy; HomePage reworded | Same whole-% match contract; match preserved in history | Tie on score. Muse's reworded HomePage + match band is the final. |
| Dual naming, all 21 classes | Medical-heavy names; bronchitis "Airway inflammation (bronchitis)" | Every class dual EN+SW, simple first, medical in parentheses, enforced in code; e.g. "Chest infection (bronchitis)", "Abnormal growth in the lung (pulmonary neoplasm)" | Only bronchitis changed, to "Chest infection / airway inflammation (bronchitis)" — not Eeshan's decided format | **Muse, clearly.** Final keeps Muse's table. |
| Common flu-like cluster (headache + sore throat + cough + runny nose) | Withheld: bucket 4:0 disabled (risk 0.1025 > 0.10) | Family answer "Flu-like illness / common cold (viral upper respiratory infection)", 78% moderate, + care steps + COVID test note; "running nose" alias added | Withheld: its gap buckets enable only 5-8 positives, so 4:0 never names anything; no family answer | **Muse.** This was Eeshan's approved fix. |
| Sparse-serious guard (headache + tiredness + cough = neoplasm 100%) | Names Pulmonary neoplasm strong in the function path | Hard guard in selection AND assessment: never neoplasm, never TB-strong, on ≤3 features without a specific feature (weight loss, coughing blood, chest pain at rest, breathing difficulty, night sweats) | Blocked only indirectly: 3-positive buckets are disabled in its gap policy, so it withholds — but it has no explicit guard, and no guard if a bucket were ever enabled | **Muse** for explicitness; Codex's bucket strictness is a second, independent safety net. Final keeps Muse's guard. |
| Close-gap gate | Gap recorded, never gated | 0.10 general / 0.20 when second is dangerous, on top of bucket thresholds; dangerous close second → professional review | 0.15 gap + 0.60 floor, predeclared and checked on a separate 6,479-profile source-validation fold; 24/48 buckets enabled; fail-closed (missing policy → withhold) | **Codex on evidence, Muse on coverage.** Codex's thresholds are fold-checked; Muse's are conservative choices, unvalidated on a fresh fold. But Codex's gate withholds the approved 4:0 family case, so it was NOT adopted wholesale. Final: keep Muse's gate + family + guard; use Codex's validation protocol as the method to check Muse's thresholds on a fresh fold (future work, not claimed done). |
| Graded breathing tier | One code for can't-breathe and difficulty; no tier | Emergency (can't breathe / at rest / cannot speak) vs urgent same-day (exertion only + full sentence), one severity check, tiered guidance | Emergency vs exertional + one combined exertion/speech check; emergency phrases extended; severe chest pain asked as a first consultation question | Tie, slight **Codex** edge on proactive safety questions (severe chest pain asked, not only free-text). Muse's tier is the final; the proactive chest-pain question is a follow-up candidate. |
| COVID out of scope + test note | No COVID class, no taste feature, smell → sinusitis, no test note | COVID note on withheld / sinusitis / flu-like / taste-smell results; taste recognised as advice-only note, never a model feature | Fuller COVID scope message (exposure, positive test, variants, severity ≠ COVID) + taste/smell drives COVID-testing advice; withheld viral guidance | **Codex wording taken into Muse** (see CHANGELOG). Final note is Codex's wording. Codex's paracetamol recommendation was NOT taken (no specific medicine is recommended here). |
| Withheld / non-specific output | Withheld message + reason, but non-specific cases dead-ended after fever/cough with no further question | Full withheld screen: title, plain explanation, care guidance, malaria-test step for fever, temperature check, AND discriminator questions in consultation and on the result screen (re-check adds "yes" symptoms); breathing "yes" → urgent review | Withheld viral-cold guidance, but only when sore throat + runny nose (or a stated cold/flu) are present — tiredness + headache alone, and tiredness + headache + fever, get no such guidance; result-page correction + health-worker summary with copy | **Muse** for Eeshan's exact cases. Final keeps Muse's withheld screen. Codex's copyable health-worker summary is comparable to Muse's take-to-clinic summary. |
| Everyday EN/SW/Sheng understanding | 42 codes; "running nose" unmapped | Running nose, night breathlessness, itchy eyes, green nasal discharge, loss of smell, activity fatigue, etc. (uncapped pass) | 46 codes: weakness ("sina nguvu"), dizziness, common_cold ("kipooza"), flu_like ("I have flu") as context codes (no features); everyday variants ("nimechoka", "koo linaniuma", "pua inatoka", "chest inauma", "having challenges breathing") | **Codex aliases + context codes taken into Muse** (see CHANGELOG). Final has 46 codes with both sets of aliases. |
| Sudden neurological change | Not detected | Not detected before this pass | Sudden one-sided weakness / face drooping / slurred speech → emergency flag; general weakness → clarification question | **Codex detection taken into Muse** (emergency routing). Codex's clarification question was NOT taken (needs its own review). |
| Symptom gathering | 5-question cap, 0.02-nat stop | Soft guide 5, hard ceiling 20, pool expanded 9 → 25 codes (all existing catalogue codes), safety / 2x-don't-know / no-change stops kept | 5-question cap kept, 0.02-nat stop kept, safety screen first | **Muse**, per Eeshan's uncapped-gathering authorisation. |
| Result order, edit, take-to-clinic | Result shrinks to a list; correction means starting again | Urgency first, single result + band, what-we-understood + Edit on the result page, next step with when/where/what to ask for, take-to-clinic summary | Result-page correction, duration/severity visible, stale policy/cache invalidation, health-worker summary with copy | Tie; both fixed the baseline gap. |
| Repo hygiene | Baseline | Zip/branch clean: no .env/.venv/node_modules/dist/__pycache__/.git/raw CSVs | Removed tracked frontend dist; no .env/.venv/node_modules/dist/raw DDXPlus committed; DDXPlus v15 restored locally with checksums, V3 reproduced from all 443,075 rows (2,000-per-class cap confirmed V2-only) | **Codex** on provenance work (DDXPlus restore + reproduction check). Not code the patient sees; noted for defence material. |
| Verification | Claimed 282 backend / 369 ML / 114 frontend / 14 browser (reports only) | Backend 350, frontend 117, vite build, 21 function journeys — all re-run here; no browser journeys | Backend 360, ML 395, frontend 124, 45 Edge browser journeys — per its validation doc, not re-run by Muse | **Codex** on browser verification breadth; Muse on re-run honesty for its own counts. Neither side's numbers are Kenyan-patient validation. |

## Final stable version: what it takes from each

From Muse (kept): dual naming for all 21 classes; family answer for the
common cluster; sparse-serious guard; close-gap gate + dangerous-second
review; graded breathing tier; uncapped symptom gathering; non-specific
withheld screen with discriminator re-check; malaria-test step for fever;
no specific medicine recommended; no forced name on sparse or mild cases.

From Codex (taken, credited in CHANGELOG): everyday aliases and the four
context codes; sudden-neurological-change emergency detection; fuller
COVID scope wording.

From Codex (not taken, with reasons): gap gate (would withhold the
approved family case; no sparse guard); bronchitis display variant
(decided format differs); paracetamol recommendation (no specific
medicine rule); 5-question cap (superseded); weakness-clarification
question (needs its own review); severe-chest-pain consultation question
(follow-up candidate, not in this pass).

Still open (both sides): gap / family / guard thresholds are not
validated on a fresh fold (Codex's protocol is the template for that
check); Kiswahili copy is draft and unreviewed; nothing here is
clinically validated for patients in Kenya; browser journeys have not
been run on the Muse branch.
