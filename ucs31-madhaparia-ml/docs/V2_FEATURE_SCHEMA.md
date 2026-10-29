# Random Forest Version 2 — Feature Schema

## 1. Overview

Version 2 aims to improve the representation of patient symptoms and incomplete information while preserving the original Random Forest Version 1 model.

The initial system scope remains 21 respiratory conditions.

## 2. Existing Features

Version 1 uses 198 input features:

- AGE
- SEX_M
- 196 active DDXPlus evidence features

Examples:

| Symptom | Feature |
|---|---|
| Fever | E_91 |
| Cough | E_201 |
| Chills | E_94 |

The original feature order is stored in `models/model_features.json`.

## 3. Symptom Status

Version 2 will distinguish three states:

| Status | Meaning |
|---|---|
| Present | Patient confirms having the symptom |
| Absent | Patient explicitly denies the symptom |
| Unknown | Patient has not provided the information |

Unknown symptoms must not automatically be treated as confirmed absent.

## 4. Symptom Duration

Version 2 will support collecting symptom duration where relevant.

For example:

- Fever for 2 days
- Cough for 5 days
- Cough for 3 weeks

Duration will initially be stored as patient-reported information. Its use as a model feature will depend on available training data and validation.

## 5. Feature Encoding

The proposed feature representation will distinguish symptom values from whether information was observed.

For binary symptoms, separate present and absent indicators may be evaluated. When both indicators are zero, the symptom is unknown.

Categorical and multi-value DDXPlus evidences require separate encoding rules.

The final feature structure will be confirmed before training Random Forest Version 2.

## 6. Feature Coverage

The existing NLP mapping covers only part of the model's evidence features.

Version 2 will review the available mappings and identify additional clinically supported questions needed for the 21 conditions.

Unsupported symptom information must not be converted into invented evidence features.

## 7. Safety Handling

Urgent symptom checks will remain independent of Random Forest prediction.

Red-flag symptoms will be assessed before model inference, including whether the patient has explicitly denied them.

## 8. Compatibility

- Preserve the Version 1 model and supporting artifacts.
- Keep Version 2 features separate from Version 1.
- Update NLP and preprocessing to support the final Version 2 schema.
- Use consistent feature ordering during training and prediction.
- Validate the final representation before dataset augmentation and retraining.

## 9. Expected Outcome

The Version 2 feature structure should support incomplete patient information, prevent unknown symptoms from being treated as explicitly absent, and provide a consistent input representation for the improved Random Forest model.