
# V2 Backend Integration Guide

## Overview

This document describes how the existing FastAPI backend
can integrate with the Random Forest V2 prototype.

V2 is the preferred experimental candidate from the V1/V2
comparison. It is not clinically validated and must not be
used to diagnose patients.

## Existing ML Components

- Model: `models/rf_v2_23class_prototype.joblib`
- Schema: `models/v2_feature_schema.json`
- Feature encoder: `scripts/v2_feature_encoder.py`
- Predictor: `inference/v2_predictor.py`
- Uncertainty handling: `inference/prediction_confidence.py`
- Backend adapter: `inference/backend_adapter.py`

The model supports 23 prediction classes and requires
66 features: AGE, SEX_M, 32 symptom-presence flags and
32 symptom-absence flags.

## Backend Adapter

Use:

```python
from inference.backend_adapter import predict_v2_from_backend

result = predict_v2_from_backend(
    age=25,
    sex="M",
    confirmed_features=["E_91", "E_201"],
)
```

The function accepts:

- `age`: age within the supported range of 0–120
- `sex`: "M" or "F"
- `confirmed_features`: evidence codes confirmed as present
- `explicitly_absent_features`: optional evidence codes
  explicitly denied by the patient

At least one confirmed symptom is required for prediction.

The adapter validates inputs and creates the complete
66-feature dictionary using the saved V2 schema.

## Symptom State Rules

- Present: `CODE__present = 1`, `CODE__absent = 0`
- Absent: `CODE__present = 0`, `CODE__absent = 1`
- Unknown: both values remain 0

Rejected NLP suggestions are not automatically treated
as absent symptoms.

The adapter rejects conflicting states, unsupported
evidence codes and duplicate codes.

## Compatibility With Existing Backend

The backend symptom catalogue maps canonical symptom names
to DDXPlus evidence codes.

All 32 V2-supported evidence codes appear in the current
backend catalogue.

The backend also has two mapped evidence features outside
the V2 schema. These must be handled explicitly during
backend integration.

Do not silently discard unsupported evidence codes.
Do not allow unsupported features to bypass red-flag checks.

The current adapter rejects unsupported codes.

## Prediction Response

The adapter returns:

- `predicted_condition`
- `confidence_score`
- `second_condition`
- `second_score`
- `score_margin`
- `uncertain`
- `uncertainty_reasons`
- `message`
- `score_note`
- `model_version`
- `feature_count`
- `active_symptom_features`
- `explicitly_absent_features`

The confidence and margin thresholds are provisional
prototype rules.

Model scores are uncalibrated and must not be presented
as clinically validated disease probabilities.

The current adapter returns a leading condition and
runner-up rather than the existing backend's ranked
top-three response.

The backend response mapping must be updated separately.

## Safety Requirements

The existing backend must continue to:

1. Recognise and confirm symptoms.
2. Perform independent red-flag checks.
3. Bypass prediction when urgent red flags are confirmed.
4. Provide urgent guidance for red-flag cases.
5. Show non-diagnostic messages and uncertainty warnings.

The ML adapter is not a replacement for these safety checks.

## Integration Status

Completed in Issue #30:

- Verified model/schema compatibility.
- Verified all 32 V2 evidence codes are mapped.
- Implemented a reusable backend adapter.
- Preserved unknown and explicitly absent symptom states.
- Added automated adapter tests.
- Verified real V2 prediction execution.

Remaining work in the existing backend:

- Update model loading and artifact configuration.
- Connect the prediction service to V2.
- Decide how to handle the two additional backend features.
- Update the API response mapping and model-version tracking.
- Preserve and test independent red-flag handling.
- Run backend integration and regression tests.

Frontend changes should be limited to necessary response
display updates after the backend API is finalised.

## Testing

```powershell
python -m pytest tests/test_backend_adapter.py -q
python -m pytest tests/ -q
```

Issue #30 verification:

- 11 backend adapter tests passed.
- Full suite: 97 tests passed, 5 subtests passed.

## Limitations

Training and evaluation data are simulated. The validation
audit identified exact train-validation overlap.

COVID-19 and allergic rhinitis do not have independent
held-out real-patient evaluation cases in this prototype.

V2 showed weaker sparse-input recall for some conditions,
including pneumonia and asthma exacerbation.

Neither the model nor its uncertainty thresholds have been
clinically validated.
