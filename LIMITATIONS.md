# LIMITATIONS — read before using or presenting this version

- NOT clinically validated for patients in Kenya. All numbers are simulated DDXPlus only.
- The patient match percent is a display mapping of a relative ranking share
  (scores sum to 1 across 21 classes). It is NOT a probability that the patient
  has the condition, NOT a diagnosis, and NOT overall accuracy.
- Gap thresholds (0.10 general, 0.20 dangerous second) are conservative choices
  from the checklist, NOT validated on a fresh fold. Do not present them as validated.
  In practice the real V3 distribution is extremely peaked, so the gap gate fires
  rarely; most close cases are withheld by the bucket threshold instead.
- New Kiswahili copy (emergency/urgent guidance, withheld wording, COVID note,
  "chest infection" alias, all dual names, family answer, TB note, new
  follow-up questions and new aliases) is draft and unreviewed by a Kenyan
  clinician or Kiswahili reviewer.
- The family answer ("Flu-like illness / common cold") is NOT a model class
  and NOT a diagnosis: it is a family-level presentation of a viral
  upper-respiratory pattern, used only under the narrow 4:0 exception.
  The family thresholds (top >=75%, gap >=20 points) and the
  sparse-serious guard thresholds are conservative choices, NOT validated
  on a fresh fold. Do not present them as validated.
- Uncapped gathering does not mean every case resolves: the
  information-gain stop (>=0.02 nats) still ends sparse cases whose
  features carry almost no discriminating information (e.g. cough +
  tiredness alone, gains ~0). The count cap no longer blocks a useful
  question; it does not manufacture information the model does not have.
- COVID-19, malaria, and HIV-associated illness are NOT predicted by this version.
  A sinusitis or flu-like result does NOT rule out COVID.
- Browser journeys did not run in this worker; only function-level journeys
  (mapping → safety → selection) and the unit suites ran here.
- No interviews, surveys, or doctor quotes were collected for this version.
  Kenyan patient-needs claims in the earlier research docs are hypotheses from
  small local studies, not national rates.
- "I can't speak" / "siwezi kuongea" as a shortness-of-breath alias
  (taken from Codex): in a symptom box this is treated as
  speech/breathing difficulty, per the checklist. Trade-off: the same
  words in a non-breathing sentence (e.g. "I can't speak French")
  would also map to breathing difficulty and show urgent guidance.
  Muse's breathing-tier full-text check already treated cannot-speak
  as an emergency-tier signal; the alias makes it a mapped symptom too.
- Weakness clarification was NOT taken from Codex: general weakness is
  recognised as context, and sudden one-sided weakness / face drooping
  / slurred speech goes to emergency, but there is no follow-up
  question yet asking what "weak" means (general low energy vs sudden
  one-sided). That question needs its own review before being added.
- The Codex gap gate was NOT adopted (see COMPARISON_CODEX.md): Muse's
  gap (0.10 / 0.20), family (75% / 20 points) and guard thresholds are
  still unvalidated on a fresh fold. Codex's fold-checked gate enables
  only 5-8-positive buckets, which would withhold the common 4-symptom
  cluster that Eeshan approved as a family answer.
- New Codex-taken aliases and the fuller COVID wording are draft
  Kiswahili, unreviewed, like all other new copy in this version.
- Model artefacts documented, never shown to patients: Pulmonary
  neoplasm scores 1.000 on headache + tiredness alone, and Epiglottitis
  0.216 on headache + tiredness + fever. Both are blocked from patient
  output by the respiratory-anchor gate (and, for sparse serious names,
  the sparse-serious guard). Never quote these as patient scores.
