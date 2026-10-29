# RespiraCare: a calm, bounded symptom conversation

Design/review note, 29 October 2026. This is a proposed product flow, not a
clinician-approved triage protocol. No clinical application rules were changed
in this review. Published guidance was consulted; Kenyan doctors/patients were
not interviewed. The app must not claim to replace a consultation, examination
or tests.

## 1. What the example does today

Input: `i feel tired and have weaknes for 3 days`

The local NLP runtime was executed on this exact text and on the correctly spelt
`weakness` version. Both recognise tiredness and a three-day duration, but leave
weakness unmatched. Generic tiredness has no trained constant-fatigue feature,
which correctly avoids asserting persistence. However, its display label is
still **Constant tiredness**, which overstates the patient's report.

The current question/decision functions were exercised with a synthetic adult
(24, F), all unreported breathing/chest/fever/cough answers set to no. This was a
function-level check, **not a fresh database/API/browser journey**:

- Questions: breathing difficulty, severe chest pain, fever, cough.
- Final status: `assessment_uncertain`; primary: `null`; no match score.
- Message: some wording was not understood; nothing is ruled out.
- Defect: the three-day advice still lists acute respiratory infections despite
  no respiratory complaint. Duration must not manufacture respiratory scope.
- Gap: the flow does not clarify what weakness means or its functional impact.

Additional executed language example:
`Ninahisi uchovu na sina nguvu kwa siku tatu` recognises tiredness but misses the
duration and leaves wording unmatched. This specific failure does not measure
overall Kiswahili performance. `Sina nguvu` must not be interpreted as denying
weakness merely because it contains a negative word.

Independent gap validation remains blocked by missing labelled source files.
All live condition names are currently withheld. High internal scores do not
override that blocker or the scope/safety checks.

## 2. Separate four jobs

1. **Understanding:** what the patient actually said, including ambiguity,
   negatives, another person's symptoms, duration and change over time.
2. **Care priority:** emergency, same-day assessment, other clinical review, or
   monitoring with clear return instructions. Independent of disease scores.
3. **Limited pattern matching:** V3's 21 respiratory classes, only when in scope
   and all validated selection gates permit naming.
4. **Communication:** plain explanation, next action and when to seek help.

Understanding more words must not silently add trained features or diagnoses.
Safety-only observations can change advice without becoming disease-model inputs.

## 3. Proposed patient journey

| Stage | Patient experience | Guardrail |
|---|---|---|
| Immediate safety | Prominent warning guidance when a danger sign is reported; no waiting for an account/form/model | Emergency before routine questions; unfamiliar wording is not evidence of safety |
| Understand | “You have felt tired for 3 days. What do you mean by weak?” | Distinguish low energy from loss of muscle power, especially sudden/localised weakness; clinician-approved routing needed |
| Confirm/correct | Present / absent / uncertain / not mentioned, duration, severity/ability to do usual tasks | Not mentioned is never automatically no; don't count synonyms as independent symptoms |
| Essential context | Age; infant age in months, relevant existing conditions, pregnancy or medicines only when needed for care | Minimise sensitive data; explain why asked; untrained context must not alter model scores |
| Safety screen | Breathing, severe chest pain, fever and duration; other complaint-specific danger checks | Maintain graded breathing response and stop on red flags |
| Scope decision | Respiratory complaint → bounded respiratory path. Nonrespiratory/unclear complaint → clarification and appropriate care guidance | Do not fish for respiratory symptoms until a serious source class can be named |
| Useful follow-ups | Only questions whose answers can change the primary or care action | Preserve cap 5, 0.02-nat stop, two unknowns, no-change stop and red-flag stop; do not silently extend limits |
| Summary | What was understood; one eligible possibility or no specific name; explicit limitations | A broad symptom summary is not a new trained disease class |
| Plan | What to do now, when to seek review, what deterioration requires immediate help | No blanket 24–48h wait for severe, worsening or high-risk symptoms |
| Handover/recheck | Copyable summary for a health worker; edit symptoms or report change | Never claim a clinician received it unless an actual referral integration exists |

Start with a small number of reviewed paths: breathing difficulty, cough/fever,
prolonged cough, sore throat/nose symptoms, and nonspecific tiredness/weakness.
Do not attempt a general virtual doctor for all medicine by adding keywords.

### Draft exchange for the example

> You have felt tired and weak for 3 days. These symptoms alone do not tell us
> the cause. By weak, do you mean low energy all over, or difficulty moving an
> arm or leg normally?

New sudden one-sided weakness, facial droop or speech difficulty would require
emergency care guidance, not a respiratory prediction. This is a proposed safety
extension needing clinician-reviewed wording and regression tests; it is not
claimed to be implemented in the current app.

For general low energy, relevant next questions may concern usual activities,
fever/respiratory symptoms, eating/drinking, symptom progression and relevant
medical context. Ask conditionally within the agreed limits, not all at once.
An examination or tests may be needed; the app must not infer anaemia, malaria,
diabetes, influenza or any other diagnosis from tiredness alone.

Draft outcome after appropriate safety/context checks:

> **We cannot name a condition from this information.** You reported tiredness
> and general weakness for 3 days. This tool checks a limited set of chest and
> breathing conditions and cannot assess every cause. Nothing is ruled out.
> If symptoms are not improving, affect your normal activities, or worry you,
> arrange a health-worker review; seek care sooner if they worsen. Urgent
> symptoms should not wait for a monitoring period.

Draft Kiswahili opening, not professionally reviewed:

> Umesema unahisi uchovu na mwili hauna nguvu kwa siku tatu. Dalili hizi pekee
> hazitoshi kujua chanzo. Hebu tufafanue unachomaanisha na kuangalia kama
> unahitaji huduma ya haraka.

This is calm through clear explanation and a plan, not through saying “nothing
serious” or concealing a genuine need for urgent care.

## 4. Scores: current reality and intended policy

Current local build: the whole-percent selected-primary display exists. A
predeclared 0.15 gap / 0.60 floor passed 24 of 48 evidence buckets on a separate
source-validation fold, so richer eligible patterns show one actual V3 match;
sparse patterns still show no name or score. No changes were pushed/deployed; a
hosted version may differ.

After independent validation, the agreed presentation bands are:

| Match | Meaning, not a clinical certainty threshold |
|---|---|
| Below 60, including below 50 | Low/not sure. Clarify if useful; do not force a specific name or equate low match with low risk |
| 60–79 | Moderate pattern match; name only if the independently checked bucket/gap/scope/safety gates all permit |
| 80+ | Strong relative pattern match only when those gates permit; never a diagnosis or a reason to ignore warning signs |

The bands are product wording, not validated clinical cutoffs. A score by itself
never authorises a disease name. No separate validated 50% rule exists.

V3 normalises its 21 internal relative scores to sum to 1 (100%). The runtime
and a numerical check confirmed this. **Two conditions cannot both have over
80% in one V3 ranking.** Such a display would indicate a bug, mixed assessments,
or a different independent scoring scheme. Real coexisting illnesses are still
possible: this single-label model does not evaluate them reliably. It also can
give a high relative score when the real cause is outside its limited menu.

## 5. COVID, flu and “viral flu”

| Term | Honest interpretation in this app |
|---|---|
| COVID | Not a V3 prediction class. Provide scope/testing advice; never infer it from severity or smell/taste alone. A future patient-reported positive test must be labelled as reported, not as the model's discovery |
| Seasonal flu (influenza) | A specific existing V3 class. If naming is eventually enabled and eligible, say possible influenza, not confirmed influenza |
| Flu-like symptoms | A description of a symptom pattern with cause uncertain, not a new disease prediction or proof of a virus |
| “Viral flu” | Avoid as a separate output: influenza is already viral and this wording does not distinguish influenza, COVID or other infections |
| Nose/throat infection (URTI) | Existing broad class; not synonymous with confirmed influenza |
| Viral sore throat (viral pharyngitis) | Existing specific source class; not “viral flu” |
| Chest infection / airway inflammation (bronchitis) | Explain with the medical name; a broad familiar phrase alone does not prove bronchitis or exclude pneumonia |

Keep the warning that bare mafua does not confirm influenza and homa is not a
flu diagnosis. COVID addition requires adequate labelled data and independent
evaluation; enabling the synthetic V2 extension is not the solution.

## 6. Next work, in order

Done in this pass (implemented, tested, browser-verified):

- Weakness/typo recognition, concept-aware `sina nguvu` negation, Kiswahili
  duration attachment, generic tiredness no longer labelled "constant", and a
  weakness clarification (general vs sudden one-sided / facial droop / speech
  difficulty → emergency).
- Scope-aware advice: duration alone no longer names a respiratory cause;
  generic tiredness/weakness with denied cough/fever gets neutral rest, hydration
  and review guidance, not a respiratory list.
- Official DDXPlus v15 restored and V3 reproduced exactly from all 443,075
  training rows (the 2,000-per-class cap was V2 only).
- A predeclared 0.15 gap / 0.60 floor checked on a separate source-validation
  fold; 24/48 buckets enabled; selective accuracy reported with coverage.

Still to do, in order:

1. Have a Kenyan clinician review the small conversation paths, danger checks,
   age/risk context and review timeframes. Have Kiswahili speakers and patients
   test comprehension, including Sheng/mixed wording. Do not call this validation
   merely because a doctor has read the copy.
2. Before patient deployment, evaluate real-world extraction errors, missed
   urgent cases, unnecessary referral, unsupported complaints, coexisting illness
   and subgroup differences under appropriate consent/data governance. Adding
   many labels or a free-form LLM diagnostic layer is not a substitute.

Acceptance examples now cover this exact misspelling; correctly spelt weakness;
`sina nguvu`; general versus sudden one-sided weakness; no respiratory complaint
despite a 3-day duration; inability to do usual activities; denied fever;
other-person symptoms; correction/recheck; and escalation despite a high score.

## Sources and limits

- [Kenya MOH community guidelines, 2024](https://health.go.ke/sites/default/files/2025-04/Clinical%20Guidelines%20for%20Level%201%20Community%20Health%20Services.pdf): dialogue/assessment/options/action-plan framework (PDF p.43, in a maternal-health context), danger-sign recognition, referral and respectful communication. Principles inform the design; this is not a validated general app algorithm.
- [Kenya MOH primary-care guidelines, 2024](https://health.go.ke/sites/default/files/2025-04/Clinical%20Guidelines%20for%20Level%202%20Dispensaries%20Medical%20Clinics%20Level%203%20Health%20Centres%20Nursing.pdf): clinical assessment, physical examination, investigations and referral; weakness/fatigue appear in several nonrespiratory contexts. Published guidance is not evidence of what every Kenyan doctor says, and medication protocols were not copied into the app.
- [WHO seasonal influenza](https://www.who.int/news-room/fact-sheets/detail/influenza-(seasonal)): influenza is viral; other pathogens can cause influenza-like illness; definitive identification may require laboratory testing.
- [CDC flu/COVID comparison](https://www.cdc.gov/flu/about/flu-vs-covid19.html): symptom overlap, testing to distinguish causes and possibility of co-infection. US treatment pathways/phone numbers are not transplanted into Kenyan care.

No Kenyan patient clinical validation, clinician interview study, Kiswahili
comprehension validation or COVID prediction validation was performed here.
