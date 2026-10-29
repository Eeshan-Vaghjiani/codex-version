# Random Forest Version 2 — Development and Evaluation Log

## 1. Purpose

This document records the development and evaluation activities carried out during the improvement of the respiratory disease prediction system.

The purpose of Version 2 is to improve the handling of incomplete patient information and reduce unsupported, overconfident predictions while preserving Version 1 for comparison.

## 2. Version 1 Sparse-Input Evaluation

The original Random Forest model was tested using short symptom combinations to examine its behaviour when users provided limited information.

The tests were performed using the saved Version 1 model and its original feature structure. Unreported evidence features were encoded as zero, following the existing Version 1 input representation.

The patient age was set to 21 years. Sex was encoded as male unless otherwise specified.

### 2.1 Evaluation Results

| Input Symptoms | Predicted Condition | Model Probability |
|---|---|---|
| Fever only | Croup | 37.25% |
| Cough only | Tuberculosis | 62.75% |
| Fever and cough (male) | Tuberculosis | 99.75% |
| Fever and cough (female) | Tuberculosis | 96.75% |
| Fever, cough and muscle aches | Tuberculosis | 90.00% |
| Fever, cough and sore throat | Tuberculosis | 75.50% |
| Runny nose and sore throat | Allergic sinusitis | 69.25% |
| Cough, heavy sweating and weight loss | Tuberculosis | 74.25% |

### 2.2 Observations

The evaluation showed that Version 1 frequently selected tuberculosis when limited symptoms were provided.

For example, fever and cough produced a tuberculosis prediction with a model probability of 99.75% for a 21-year-old male.

The results also showed differences in model probabilities between male and female inputs.

These findings suggest that Version 1 may be unreliable when processing incomplete symptom information, despite its high accuracy on the original synthetic DDXPlus test dataset.

The exploratory scenarios did not contain independently verified diagnoses. Therefore, these results demonstrate potentially misleading confidence behaviour rather than a measured clinical misdiagnosis rate.

## 3. Version 2 Feature Representation

A new Python module, `nlp/symptom_state.py`, was developed to represent patient symptoms using three states:

- Present: The patient confirms having a symptom.
- Absent: The patient explicitly denies having a symptom.
- Unknown: The patient has not provided information about the symptom.

The module also supports storing minimum and maximum symptom duration in days.

For example, a patient reporting a cough lasting five days while denying headache can be represented with cough marked as present, headache marked as absent and other unreported symptoms marked as unknown.

This representation is intended to support future NLP improvements and Version 2 model development.

The new module does not yet replace Version 1's model input encoding.

## 4. Automated Testing

Eight automated tests were added in `tests/test_symptom_state.py`.

The tests covered:

- Present, absent and unknown symptom states.
- Coverage of supported canonical symptoms.
- Symptom duration storage.
- Unsupported symptom rejection.
- Invalid status rejection.
- Duration validation.

All eight new tests passed.

The complete test suite was also executed, including the existing NLP tests.

**Test results:**

- Existing NLP tests: 12 passed.
- New symptom-state tests: 8 passed.
- Total: 20 tests passed.
- Failed tests: 0.

These results confirm the tested symptom-state functionality but do not establish model prediction accuracy or resolve the known sentence-level NLP issues.

## 5. Identified Limitations

The following issues remain:

- Version 1 produces highly confident predictions from limited symptom information.
- Existing NLP processing does not correctly handle some negated symptoms.
- Symptom duration is not yet extracted automatically from user text.
- Certain respiratory expressions and urgent warning signs are not consistently recognised.
- The Version 2 feature representation has not yet been integrated into model training.
- The system has not been clinically validated using Kenyan patient data.

## 6. Planned Improvements

The following development activities will address these limitations:

- Improve English and Kiswahili symptom processing.
- Implement sentence-level negation and duration extraction.
- Improve red-flag identification.
- Refine training-data augmentation.
- Train Random Forest Version 2.
- Introduce evaluated uncertainty handling.
- Compare Version 2 with Version 1 using realistic symptom inputs.

## 7. Conclusion

The initial evaluation identified important limitations in the behaviour of Random Forest Version 1 when processing incomplete symptom information.

The new symptom-state module provides a foundation for representing patient information more accurately.

Further NLP improvements, model retraining and independent evaluation are required before Version 2 can be considered ready for integration into the health-awareness application.


## 8. Version 1 NLP Baseline Audit

### 8.1 Purpose

An additional NLP audit was conducted before implementing
Version 2 improvements. The purpose was to identify
limitations in symptom interpretation, English and
Kiswahili processing, red-flag recognition, and
symptom duration extraction.

### 8.2 Audit Results

The audit was performed using scripts/audit_nlp_v1.py
against the original NLP symptom mapper.

| Test Category | Passed | Total |
|---|---:|---:|
| Sentence-level scenarios | 1 | 24 |
| Canonical symptom alias checks | 36 | 36 |
| Symptom duration checks | 0 | 2 |
| Overall | 37 | 62 |

### 8.3 Key Findings

The original NLP successfully recognised the first
tested English alias for each of the 36 canonical
symptom concepts.

However, it did not provide explicit present, absent
or unknown symptom statuses.

The audit also identified limitations involving:

- English and Kiswahili negation.
- Uncertainty and symptom context.
- Unrecognised respiratory expressions.
- Potentially urgent breathing-related expressions.
- Negated red-flag symptoms.
- Symptom duration extraction.
- Past symptoms and references to other people.

### 8.4 Interpretation

The low sentence-level score was primarily affected
by the absence of an implemented symptom-status field.
It must not be interpreted as an overall NLP accuracy
score or clinical prediction accuracy.

The alias checks tested only one English alias per
canonical symptom, rather than every possible phrase.

Some expected behaviours, particularly ambiguous
patient-context statements, require further review.

### 8.5 Next Development Activities

Issue #25 will address these limitations by improving
symptom recognition, negation, red-flag handling,
duration extraction and English/Kiswahili processing.

The same audit scenarios will be repeated after the
changes to assess whether the identified problems
have been resolved.

These tests evaluate NLP functionality and do not
establish clinical reliability.


## 9. Issue #25 — NLP Processing Improvements

### 9.1 Purpose

Issue #25 focused on improving English and Kiswahili symptom processing, particularly symptom recognition, negation, uncertainty, duration extraction and red-flag handling.

The improvements were made to support more accurate interpretation of patient-reported information before the development of Random Forest Version 2.

### 9.2 Implemented Improvements

The following changes were implemented:

- Added present, absent and unknown symptom-status interpretation.
- Improved English and Kiswahili negation handling.
- Added recognition of additional respiratory symptom expressions.
- Improved the handling of uncertain symptom descriptions.
- Added duration extraction for clearly expressed days and weeks.
- Improved interpretation of symptoms reported about other people.
- Added separate patient-context information using the reported_subject field.
- Improved the handling of repeated symptoms and different aliases referring to the same canonical symptom.
- Updated red-flag checks to consider symptom status and reported subject.
- Reduced incorrect fuzzy suggestions for unsupported wording.
- Improved unmatched-text handling to avoid repeating recognised symptom aliases.

### 9.3 Automated Testing Results

Automated tests were developed and executed for symptom mapping, negation, red-flag handling, duration extraction, patient context and structured symptom states.

The final test suite contained 54 tests.

**Results:**

- Tests executed: 54
- Tests passed: 54
- Tests failed: 0

The original NLP audit was also rerun after the improvements.

| Test Category | Passed | Total |
|---|---:|---:|
| Sentence-level scenarios | 24 | 24 |
| Canonical symptom alias checks | 36 | 36 |
| Symptom duration checks | 2 | 2 |
| Overall | 62 | 62 |

The original baseline recorded 37 out of 62 checks passing. The updated audit passed all 62 checks. However, the sneezing scenario's expected behaviour was clarified during development, so these scores should not be treated as a strictly unchanged benchmark or a general NLP accuracy percentage.

### 9.4 Additional Findings

Further testing identified problems involving repeated symptoms reported by different people.

For example, the system initially struggled to distinguish a patient's symptoms from symptoms reported about a family member when both used the same or different expressions.

The symptom-processing logic was improved to consider these statements separately.

Additional tests confirmed correct behaviour for the selected patient-context, negation and red-flag scenarios.

Unmatched-text processing was also improved so that recognised alternative symptom expressions were not incorrectly returned as unmatched wording.


A further code review identified incorrect duration attribution when a patient and another person reported the same symptom. The original extraction logic could select the other person's duration.

The duration extraction was improved to evaluate patient statements separately. Additional regression tests covered different statement orders, patient-specific duration extraction and conflicting patient durations.

All nine duration tests passed. Conflicting patient durations are returned as unknown (`None`) rather than selecting an unsupported value.

### 9.5 Remaining Limitations

Despite the improvements, the NLP component remains rule-based and has important limitations:

- Complex sentence structures, indirect wording and ambiguous references may still be interpreted incorrectly.
- English and Kiswahili coverage is limited to the supported symptom aliases and tested expressions.
- Duration extraction supports selected explicit patterns rather than unrestricted natural-language time descriptions.
- The current patient-context rules do not cover every possible relationship or conversational situation.
- Fuzzy matching and alias-based processing may still produce incorrect or missed symptom matches.
- Uncertain symptom information requires user confirmation and appropriate safety handling.
- The updated NLP representation has not yet been integrated with Random Forest Version 2.
- The system has not undergone independent clinical validation.

Passing the automated tests does not establish clinical reliability or diagnostic accuracy.

### 9.6 Conclusion

Issue #25 improved symptom recognition and interpretation, including negation, uncertainty, duration, patient context and red-flag handling.

The implemented changes passed the selected automated tests and NLP audit checks.

These improvements provide a stronger foundation for structured symptom confirmation and future Random Forest Version 2 development. Further integration testing, evaluation and validation remain necessary before the system can be relied upon for health-related decision support.
