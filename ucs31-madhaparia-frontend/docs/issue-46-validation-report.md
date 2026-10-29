
# Issue #46 — Frontend Build and System Validation

**Project:** NLP-Assisted Symptom-Based Disease Prediction System
**Date:** 23 October 2026
**Environment:** Local React frontend, FastAPI backend and separate Neon test database

## 1. Objective

To verify that the frontend communicates correctly with the backend and supports the complete patient workflow, including symptom processing, confirmation, prediction, history, feedback and red-flag handling.

## 2. Automated Frontend Validation

| Check | Result |
|---|---|
| Vitest tests | 66 passed |
| Test files | 16 passed |
| Oxlint | 0 errors, 0 warnings |
| Git whitespace check | Passed |
| Vite production build | Passed |
| Modules transformed | 108 |

The production build used a temporary local API URL for compilation.

## 3. Live Integration Testing

The frontend was connected to FastAPI using a separate Neon test database. Database migrations, symptom catalogue seeding and model registration were completed in the test environment.

| Workflow | Result |
|---|---|
| Patient registration | Passed |
| Patient login and dashboard | Passed |
| Frontend-to-backend API communication | Passed |
| English symptom recognition | Passed |
| Symptom confirmation | Passed |
| V1 prediction baseline | Passed |
| V2 single-condition prediction | Passed |
| V2 confidence and uncertainty messages | Passed |
| Saved prediction history | Passed |
| Prediction feedback submission | Passed |
| Red-flag detection and urgent-review guidance | Passed |
| Red-flag history retrieval | Passed |

## 4. Model Verification

V1 was tested using 198 features and 21 disease classes.

Experimental V2 was activated only in the separate test database, using 66 features and 23 disease classes.

For the dummy symptom input "I have fever and cough for two days", the V2 workflow displayed one condition with a 16.18% model confidence score and an uncertainty warning.

The saved prediction's model_version field was confirmed as `v2_23class_prototype`.

These results demonstrate software integration, not clinical accuracy. Model confidence must not be interpreted as the probability of having a disease.

## 5. Red-Flag Safety Test

The dummy input "I am coughing up blood" was recognised as safety-sensitive.

After confirmation, the backend returned urgent-review guidance. No disease prediction or model confidence score was displayed.

The urgent-review session was also saved and retrieved successfully from patient history.

## 6. Observations and Limitations

- The `/model/status` endpoint currently reports the statically loaded V1 artifact, rather than the database-selected active model. V2 was verified separately using the active model registration and saved prediction version.
- Earlier development testing showed temporary backend connection errors during server availability changes.
- The production build passed, but deployment to a public hosting environment was not tested.
- V2 remains an experimental research prototype without completed clinical validation.
- Automated frontend tests and local workflow testing do not establish clinical reliability or production readiness.

## 7. Conclusion

The frontend passed 66 automated tests, lint checks, production compilation and the tested local frontend-backend workflows.

The application successfully handled V2 single-condition predictions, uncertainty guidance, patient history, feedback and urgent-review cases.

Issue #46 frontend integration validation is complete for the tested local environment. Further model evaluation, production deployment testing and clinical validation remain outside this validation scope.
