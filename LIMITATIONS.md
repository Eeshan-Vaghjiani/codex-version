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
  "chest infection" alias) is draft and unreviewed by a Kenyan clinician or
  Kiswahili reviewer.
- COVID-19, malaria, and HIV-associated illness are NOT predicted by this version.
  A sinusitis or flu-like result does NOT rule out COVID.
- Browser journeys did not run in this worker; only function-level journeys
  (mapping → safety → selection) and the unit suites ran here.
- No interviews, surveys, or doctor quotes were collected for this version.
  Kenyan patient-needs claims in the earlier research docs are hypotheses from
  small local studies, not national rates.
