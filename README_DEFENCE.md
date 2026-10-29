# RespiraCare — defence one-pager

**What it is.** Respiratory health-awareness guidance, not a diagnosis, a
substitute for a qualified healthcare professional, or an emergency service.
It considers a limited set of conditions. **V3 partial-evidence is live: 21
conditions, 34 features, simulated DDXPlus only. V2 is not live. Nothing here is
clinically validated for patients in Kenya.**

**Patient flow.** English, Kiswahili or mixed free text → extracted present,
absent and uncertain symptoms → correction → breathing, severe chest pain,
fever and duration safety screening → only useful bounded follow-ups → one
primary or withheld. Result-page symptoms, duration and severity can be corrected
and rechecked. Negated symptoms and another person's symptoms are not positive
patient evidence. Duration/severity affect questions/advice, never disease scores.

**Safety first.** Cannot breathe/speak, gasping or breathing difficulty at rest:
stop prediction, no further questions, nearest hospital casualty immediately.
Ambiguous difficulty: same-day advice plus at most one exertion/full-sentence
check if safe. Exertion-only difficulty with normal speech: urgent same-day care.
Severe chest pain, fainting, blue lips, blood, confusion, infant fever and the
headache/stiff-neck warnings also stop routine prediction. Scores never downgrade
red flags. A potentially serious unresolved second pattern prompts same-day review
without exposing a disease list.

**Naming and score decision.** V3's relative match can be displayed only for a
selected primary, rounded to a whole percent: **model match — not a probability,
not a diagnosis, not overall accuracy**. Below 60 is low/not sure; 60–79 moderate;
80+ can be strong only after separation/safety gates. Withheld/urgent results have
no score. **Names require the checked V3 bucket + scope + gap policy.** The
official source data is restored and V3 reproduced exactly from all 443,075
training rows (the 2,000-per-class cap was V2 only). A predeclared 0.15 gap and
0.60 floor passed **24 of 48** evidence buckets on a separate source-validation
fold with no test tuning; the rest stay disabled. Sparse cases get no name, and
no arbitrary 50% / 10% rule is used. The parent fold had previously contributed
aggregate reporting metrics: this is **not** new-patient or Kenyan clinical
validation. HomePage states this conditional selection explicitly.

**Abstention trade-off.** The retained *pre-change* simulated DDXPlus report at
three reported symptoms recorded **91.22% selective accuracy with 50.24% coverage**,
and **45.83% correct primary over all cases**; at one symptom it named none.
Those numbers describe the earlier policy, **not** the new checked gate. The new
test fold reports **0% coverage** for 1–3 positive features (sparse patterns are
withheld) and about **93.8–96.3% selective accuracy / 47–50% coverage** for the
5–8 positive-feature buckets that passed; the reporting fold agrees. Do not
substitute older model accuracy for current performance, and never present the
selected accuracy without coverage. Abstention says **nothing is ruled out**;
monitor 24–48 hours and seek care sooner if worsening, or sooner as urgency requires.

**COVID and Kenyan fit.** V3 has no COVID class, taste feature, test/exposure input.
A positive test, exposure or taste/smell loss warrants testing/clinical advice;
sinusitis/flu-like output never excludes COVID. Severe influenza is not proof of
COVID. Bronchitis is explained as chest infection / airway inflammation with its
medical name. Influenza wording retains the warning against bare mafua; homa is
not a flu diagnosis. TB and pneumonia wording remain. Everyday English, Kiswahili
and Sheng phrasings (tiredness `nimechoka`, chest/head/sore-throat pain, runny
nose, body aches, night sweats, and stated cold/flu/dizziness) are recognised as
context only, never model evidence. Clinician and patient-comprehension
validation remain pending.

**Say to the panel:** “We prioritise warning signs and refuse unsupported names.
Our model is evaluated only on simulated-source data, not Kenyan patients. The
new gap policy remains disabled until independent validation is possible.”
