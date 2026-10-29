
# Random Forest V2 — Data Preparation

## 1. Objective

Prepare symptom-based training data for Random Forest V2, with improved support for incomplete patient information.

The aim is to improve prediction reliability rather than deliberately increase or decrease model accuracy.

## 2. Data Source

The dataset is derived from the synthetic DDXPlus dataset.

Only the original DDXPlus training split was used for V2 training-data generation.

The original V1 datasets, model and feature definitions were preserved.

## 3. Dataset Audit

The original respiratory dataset contained:

- Training: 443,075 records
- Validation: 55,808 records
- Test: 56,817 records
- Diseases: 21

The V1 model used 198 features and achieved approximately 99.44% accuracy on the synthetic DDXPlus test set.

An overlap audit identified 3,222 test records with identical raw input profiles also occurring in training.

V1 accuracy was:
- Previously seen feature patterns: 100.00%
- Unseen feature patterns: 99.41%

These findings do not establish real-world clinical accuracy.

## 4. Synthetic Scenario Generation

V2 generates partial-symptom scenarios from existing DDXPlus training records.

Rules:
- Preserve the original disease label.
- Select only documented positive binary symptoms.
- Treat unreported symptoms as unknown.
- Do not invent explicitly absent symptoms.
- Preserve source-row information.
- Use deterministic random seeds.
- Do not augment validation or test records for training.

The current generator produces one scenario per eligible original training record.

## 5. Generated Dataset

The full generated dataset contains:

- Total examples: 443,067
- Partial-symptom scenarios: 382,281
- Original binary observations: 60,786
- Excluded records with no supported symptom: 8
- Diseases represented: 21

These examples are derived from existing synthetic cases, not new independent patients.

## 6. NLP and Feature Schema

The NLP system contains 36 canonical symptom entries.

The V2 data generator currently uses 32 compatible binary symptom features.

The numerical feature schema contains:

- AGE: 1 feature
- SEX_M: 1 feature
- Confirmed-present indicators: 32 features
- Explicitly-absent indicators: 32 features

Total: 66 numerical features.

The exact ordering is stored in:

models/v2_feature_schema.json

## 7. Symptom Ambiguity

The generated dataset contains 2,059 unique reported-symptom patterns.

Of the generated records, 320,997 (72.45%) share their reported-symptom pattern with records assigned to other diseases.

This analysis excludes age and sex and is not a model-error rate.

Incomplete symptom information may not uniquely identify a disease.

Confidence calibration and uncertain predictions must be evaluated in later development stages.

## 8. Validation

The implementation passed:

- 72 automated tests across the project.
- Generated-data provenance checks.
- Source-label preservation checks.
- Feature-ordering checks.
- Complete numerical export integrity checks.
- Training-only source checks.

All 443,067 exported rows passed the structural and alignment audit.

## 9. Reproducibility

Generate V2 symptom scenarios:

python scripts/build_v2_dataset.py

Export numerical features:

python scripts/export_v2_feature_matrix.py

Run all tests:

python -m unittest discover -s tests -p "test_*.py" -v

The generator and exporter use Windows temporary directories by default.

The outputs include:

- X_train.csv
- y_train.csv
- provenance.csv
- feature_schema.json

## 10. Limitations

- DDXPlus is synthetic and does not establish clinical reliability.
- The generated examples are not independent patient records.
- Only 32 NLP-supported binary symptom features are used.
- Categorical evidence and medical history are not included in the current V2 numerical representation.
- Symptom duration is collected by the NLP system but is not a trained model feature.
- The 32 absent indicators contain only zeros in the generated training dataset.
- The encoder can represent explicit absence, but the model cannot learn its predictive meaning from this data.
- The original DDXPlus splits contain some identical profiles across partitions.
- Real-world and Kenyan population validation has not been completed.
- The model must not be presented as providing a medical diagnosis.

## 11. Next Steps

Issue #27 will train Random Forest V2 using the prepared numerical features.

Later work will address uncertainty, confidence calibration, sparse-input evaluation, safety assessment and backend integration.

Urgent red-flag handling remains independent of model prediction.
