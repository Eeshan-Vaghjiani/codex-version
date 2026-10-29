# Fixes following the audit and confirmation screenshot

The audit commit `c1c069e` reported defects; it did **not** fix them. This follow-up
changes application code. Original failed reports and ten critical cases remain
unchanged for comparison. No model or naming threshold was retrained/relaxed.

## Implemented fixes

1. **Shared negation scope:** intrinsic loss/weakness phrases (“no sense of smell”,
   “no taste”, “no energy”, “no appetite”, “sina nguvu”) no longer deny neighbouring
   symptoms. Genuine denials, uncertainty and contradiction handling remain tested.
   Both backend and research mappers have the same change. The existing independent
   safety detector uses that same context logic, so infant fever is detected before
   routine mapping/model questions, not patched only in the result screen.
2. **Old history and caches:** history rechecks warning signs from the original
   description and age, including formerly missed infant fever. Old patient-policy
   results and cached consultations require reassessment under the new version.
3. **Audited phrase gaps:** “voice changes”, “sauti kukwaruza”, “whistling sound when
   breathing out”, and “eyes are itching” map to their existing catalogue concepts.
   No new trained feature or disease was invented.
4. **Screenshot's reassessment error:** discriminator buttons formerly added raw
   codes to local confirmation without updating the input text. They now append
   only explicit Yes answers as new sentences, re-map them and call server
   confirmation. Neither text nor confirmation is saved until both calls succeed.
   No/Not-sure answers add no evidence. Breathing Yes still goes to urgent advice.
   Combined runny-or-blocked wording is retained instead of inventing which one.
   Strict backend validation was **not** disabled.

For a browser already holding the old inconsistent selections, use **Back to
confirmation** and confirm again, or start a new assessment with the full
description. The fix does not trust or silently turn stale local codes into
affirmative patient answers. An API mismatch now has a readable recovery message.

## Verification so far

- **Fixed 10,000-case replay: 10,000 / 10,000 pass, 0 failures** (original
  7,045 / 2,955). Every category clean; the 10 infant-fever bypasses and all
  smell false-absence cases are gone. The V3 model was not retrained and the
  simulated-source metrics are byte-identical to the original run.
  [Fixed replay report](UNIQUE_10000_FIXED_2026-10-29.md).
- All **ten recorded infant-fever failures** now pass regression tests that forbid
  routine mapping from running before urgent routing. The same ten cases also
  check correction of old saved-history projections.
- Six phrase-mapping regressions pass, including bilingual combined nasal wording.
- Eleven intrinsic-negation/context tests pass against both the backend and ML
  mappers. Genuine multi-symptom denials remain absent, not accidentally positive.
- Full regular suites: **backend 401**, **ML 434 + 5 subtests**, **frontend 129**.
- Frontend tests cover server-confirmed additions, safe failure without partially
  saved state, breathing Yes routing and recovery from an old invalid confirmation.
- One existing urgent-focus test needed to wait for its asynchronous focus effect;
  it still requires the warning to receive focus, rather than dropping that check.
- Frontend lint and production build pass.
- **48/48 real Playwright browser journeys pass**, including the previously missed
  `baby-fever-after-smell-loss` urgent route and a journey that confirms added
  discriminator symptoms against updated text before the next prediction.

## Two short prompts, actually exercised against the updated API

**Clear:** `I have cough, sore throat, runny nose and headache`

For age 22 / M, answering no to safety/fever and selecting under-three-days duration:
breathing difficulty → severe chest pain → fever → cough duration (**4 questions**),
then a **Flu-like illness / common cold family answer**, not a specific virus or
percentage. Different answers can change routing or the result.

**Vague everyday Kiswahili:** `Ninahisi vibaya, mwili hauna nguvu.`

This is a plausible everyday example, **not an evidenced “most popular” Kenyan
doctor complaint**. General weakness is recognised; `vibaya` remains unmatched.
With informative mild/general-low-energy context and no additional symptoms, this
test asked **9 questions** and withheld a disease name with guidance. Choosing
Not sure twice stops earlier. The current flow is not a promise of zero questions
on a clear prompt or a clinically validated interview.

## Still not solved by this patch

- The model's source-test mistakes and family-rule uncertainty were not removed.
  Do not change disease gates merely to improve naming coverage.
- Kiswahili/Sheng comprehension, clinical utility and safety for Kenyan patients
  still require external clinician/patient validation. A passing replay would be
  a software regression result, not proof of readiness for clinical deployment.
