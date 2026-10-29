# Random Forest Version 1 — Baseline Documentation

## 1. Overview

Version 1 is the original Random Forest model developed for the respiratory disease prediction system. It was trained using the respiratory subset of the DDXPlus synthetic dataset.

This baseline is preserved to support comparison with the improved Version 2 model.

## 2. Dataset

The dataset contains 21 selected respiratory conditions.

| Dataset Split | Number of Records |
|---|---:|
| Training | 443,075 |
| Validation | 55,808 |
| Testing | 56,817 |
| Total | 555,700 |

The original training, validation and test partitions were preserved during data preparation.

## 3. Model Configuration

| Parameter | Value |
|---|---|
| Algorithm | Random Forest |
| Number of estimators | 400 |
| Maximum depth | None |
| Minimum samples per leaf | 1 |
| Number of input features | 198 |
| Disease classes | 21 |

The final input structure contains age, encoded sex and 196 active DDXPlus evidence features.

The exact feature order is stored in `models/model_features.json`.

## 4. Evaluation Results

The final Random Forest was evaluated on the original DDXPlus test dataset.

| Metric | Result |
|---|---:|
| Accuracy | 99.44% |
| Macro Precision | 99.52% |
| Macro Recall | 99.22% |
| Macro F1-score | 99.33% |
| Weighted F1-score | 99.43% |
| Top-3 Accuracy | 100.00% |
| Log Loss | 0.022459 |

These results represent performance on the synthetic DDXPlus evaluation dataset and should not be interpreted as real-world clinical accuracy.

## 5. Saved Model Artifacts

The original trained model and supporting files are:

- `models/respiratory_random_forest_v1.joblib`
- `models/model_features.json`
- `models/disease_classes.json`
- `models/model_metadata.json`

These artifacts must remain unchanged during Version 2 development.

## 6. Identified Limitations

- The dataset contains synthetic rather than real patient records.
- The model was evaluated using detailed patient evidence, which may not reflect short user symptom descriptions.
- The current NLP symptom mapper covers only a subset of the trained model's evidence features.
- Unreported symptoms are not clearly distinguished from explicitly denied symptoms.
- The model may produce highly confident predictions from incomplete information.
- The model is restricted to 21 supported respiratory conditions.
- The current model has not been clinically validated for real-world diagnosis.

## 7. Purpose of Version 2

Version 2 will focus on improving prediction reliability for realistic symptom inputs.

The planned improvements include:

- Improved handling of incomplete symptom information.
- Better NLP symptom processing.
- Carefully controlled synthetic data augmentation.
- Improved confidence calibration and uncertainty handling.
- Single-disease prediction when supported by sufficient information.
- Independent red-flag safety checks.
- Evaluation against the preserved Version 1 baseline.

Version 1 will remain available for comparison throughout development.