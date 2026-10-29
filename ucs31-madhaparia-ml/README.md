# IS Project 2 - Respiratory Health Awareness and Prediction System

> Current assessment: the frozen **V3 partial-evidence likelihood model**, with an independently checked selective primary policy. The underlying model is unchanged by the latest patient experience work. See [matched before/after metrics and reusable charts](reports/kenya_patient_experience/EVALUATION_REPORT.md) and the [application report](../KENYA_PATIENT_EXPERIENCE_REPORT.md). These are simulated DDXPlus results, not Kenyan clinical validation. Earlier model descriptions below are historical.

## Machine Learning Component

This repository contains the machine learning and NLP components of the IS Project 2 Respiratory Health Awareness and Prediction System.

The system uses the DDXPlus dataset to identify respiratory condition patterns from user-reported symptoms. It is designed to provide preliminary health-awareness support and does not provide a medical diagnosis.

## Project Scope

- Dataset: DDXPlus
- Domain: Respiratory conditions
- Conditions: 21
- Primary model: Random Forest
- Benchmark model: XGBoost
- Prediction output: Top 3 possible respiratory condition patterns with confidence values
- Languages: English and Swahili
- NLP input: English, Swahili and mixed-language symptom descriptions
- Purpose: Health-awareness support, not medical diagnosis

## Respiratory Condition Selection

The respiratory subset contains conditions whose ICD-10 codes belong to Chapter J together with:

- Tuberculosis
- Pulmonary neoplasm
- Whooping cough

The final filtered dataset contains:

- Training: 443,075 records
- Validation: 55,808 records
- Test: 56,817 records
- Total: 555,700 records
- Conditions: 21

The source data contains substantial class imbalance. For this reason, model evaluation uses macro precision, macro recall, macro F1-score, weighted F1-score, confusion matrices and per-class performance in addition to accuracy.

## Repository Structure

```text
ucs31-madhaparia-ml/
│
├── data/
│   ├── raw/                  # Original DDXPlus files - not committed to Git
│   ├── processed/            # Generated model-ready datasets
│   └── readable/             # Human-readable patient examples
│
├── models/
│   ├── respiratory_random_forest_v1.joblib
│   ├── model_features.json
│   ├── disease_classes.json
│   └── model_metadata.json
│
├── nlp/
│   ├── canonical_symptoms.json
│   ├── english_aliases.json
│   ├── swahili_aliases.json
│   ├── feature_catalog.json
│   └── symptom_mapper.py
│
├── notebooks/
│   ├── 01_DDXPlus_Data_Exploration.ipynb
│   └── 02_Model_Training_and_Evaluation.ipynb
│
├── results/
│   ├── figures/
│   └── metrics/
│
├── scripts/
│   ├── prepare_data.py
│   ├── decode_patients.py
│   ├── build_symptom_mapping.py
│   └── build_canonical_symptoms.py
│
├── tests/
│   └── test_symptom_mapper.py
│
├── requirements.txt
└── README.md
```

## Environment Setup

Python 3.11 was used during development.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the environment in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```powershell
pip install -r requirements.txt
```

## Main Dependencies

The project uses:

- NumPy
- pandas
- matplotlib
- scikit-learn
- joblib
- JupyterLab
- IPython kernel
- RapidFuzz
- SHAP
- XGBoost

## Data Preparation

Place the required DDXPlus source files inside:

```text
data/raw/
```

The raw DDXPlus dataset is not committed to Git.

Prepare the respiratory subset with:

```powershell
python .\scripts\prepare_data.py .\data\raw .\data\processed
```

The data preparation process:

- Filters the dataset to the 21 respiratory conditions in scope
- Encodes DDXPlus evidences into machine-learning features
- Preserves the original training, validation and test partitions
- Generates processed datasets for model development
- Preserves symptom and antecedent/history information

The complete processed representation contains 797 model input features:

```text
AGE + SEX_M + 795 encoded DDXPlus evidence features
```

During model development, constant-zero evidence features were removed from the final production model.

The final Random Forest therefore uses 198 active input features:

```text
AGE + SEX_M + 196 active evidence features
```

The exact production feature order is stored in:

```text
models/model_features.json
```

The backend must preserve this exact feature order during prediction.

## Human-Readable Data

The script:

```text
scripts/decode_patients.py
```

converts coded DDXPlus evidence into readable patient examples.

The readable files are intended for:

- Understanding dataset structure
- Checking evidence mappings
- Selecting demonstration examples
- Supporting documentation and report writing

The readable output is not used directly for model training.

## Exploratory Data Analysis

Exploratory analysis is documented in:

```text
notebooks/01_DDXPlus_Data_Exploration.ipynb
```

The notebook examines:

- Disease distribution
- Class imbalance
- Patient age distribution
- Sex distribution
- Evidence usage
- Initial evidence distribution
- Data quality
- Active and inactive model features

Generated EDA metrics are stored in:

```text
results/metrics/
```

and figures are stored in:

```text
results/figures/
```

## Model Development

Model development and evaluation are documented in:

```text
notebooks/02_Model_Training_and_Evaluation.ipynb
```

The following classifiers were evaluated:

- Decision Tree
- Gaussian Naive Bayes
- Logistic Regression
- Random Forest
- XGBoost

Random Forest was retained as the primary project model.

XGBoost was included as a benchmark model to compare predictive performance, inference speed and model size.

## Random Forest Configuration

The selected Random Forest configuration used:

```text
n_estimators = 400
max_depth = None
min_samples_leaf = 1
```

The Random Forest was selected before the untouched test dataset was evaluated.

## Final Random Forest Test Performance

The final Random Forest was evaluated on the untouched test set containing 56,817 records.

Final test performance:

```text
Accuracy:            0.994421
Macro Precision:     0.995153
Macro Recall:        0.992220
Macro F1-score:      0.993296
Weighted F1-score:   0.994336
Top-3 Accuracy:      1.000000
Log Loss:            0.022459
```

Accuracy is not used alone because the dataset contains substantial class imbalance.

Detailed evaluation results are stored in:

```text
results/metrics/
```

including:

- Final classification report
- Confusion matrix
- Normalized confusion matrix
- Confusion errors
- Model comparison results
- Per-class metrics
- Random Forest tuning results
- XGBoost tuning results

## Saved Production Model

The production Random Forest model is stored at:

```text
models/respiratory_random_forest_v1.joblib
```

The supporting production artifacts are:

```text
models/model_features.json
models/disease_classes.json
models/model_metadata.json
```

These files should be loaded together during backend inference.

### Production Artifacts

`model_features.json`

- Stores the exact 198 model inputs
- Preserves the feature order required by the trained Random Forest

`disease_classes.json`

- Stores the 21 output disease classes

`model_metadata.json`

- Stores model information and supporting metadata

`respiratory_random_forest_v1.joblib`

- Contains the trained production Random Forest classifier

## Explainability

The project includes model explainability using:

- Random Forest feature importance
- Readable DDXPlus feature descriptions
- Global SHAP analysis
- Local SHAP example
- Tuberculosis one-vs-rest confusion analysis
- Full multiclass confusion matrix

SHAP and feature importance explain how the trained model uses its available features.

They should not be interpreted as proof that a feature clinically causes a particular condition.

## NLP Symptom Mapping

The NLP layer converts everyday user symptom descriptions into the canonical symptom representation used by the application.

The main NLP module is:

```text
nlp/symptom_mapper.py
```

The NLP component supports:

- English symptom expressions
- Swahili symptom expressions
- Mixed English and Swahili input
- Common misspellings
- Near-match detection
- Fuzzy matching
- Unmatched wording detection
- Review-only suggestions
- Red-flag detection
- Structured symptom confirmation output

## Canonical Symptoms

The project contains 36 user-facing canonical symptom concepts.

They are stored in:

```text
nlp/canonical_symptoms.json
```

A canonical symptom may map to one or more DDXPlus model features.

For example:

```text
Headache
→ E_53
→ E_55_@_V_89
```

and:

```text
Chest pain
→ E_53
→ E_55_@_V_101
```

This allows the interface to use understandable symptom names while maintaining compatibility with the DDXPlus feature representation.

## Feature Catalog

The complete catalog of active DDXPlus evidence features used by the final model is stored in:

```text
nlp/feature_catalog.json
```

It contains the active evidence features derived from the final 198-feature Random Forest input structure.

Demographic variables such as age and sex are handled separately from symptom mapping.

## English Symptom Aliases

English aliases are stored in:

```text
nlp/english_aliases.json
```

The alias layer supports everyday expressions such as:

```text
fever
high temperature
coughing
breathless
sore throat
night sweats
chest pain
```

The validated English alias vocabulary currently contains 136 aliases.

## Swahili Symptom Aliases

Swahili aliases are stored in:

```text
nlp/swahili_aliases.json
```

Examples include:

```text
homa
kikohozi
kukohoa
koo kuuma
kichwa kuuma
kupumua kwa shida
maumivu ya kifua
```

The current controlled Swahili starter vocabulary contains 29 aliases.

This vocabulary is a project localisation layer and is not intended to represent a complete validated Swahili medical terminology resource.

## Mixed-Language Input

English and Swahili aliases are combined into one symptom-mapping pipeline.

Example:

```powershell
python .\nlp\symptom_mapper.py "Nina homa and I have a sore throat"
```

The system can identify both languages in the same input and map them to the same canonical symptom representation.

Another example:

```text
homa na kichwa kuuma
```

maps to:

```text
Fever
Headache
```

## Fuzzy Matching

RapidFuzz is used to support common spelling errors and near matches.

Examples include:

```text
feaver → fever
couhg → cough
```

Exact matches are prioritised before fuzzy matching.

Weak near matches are not automatically treated as confirmed symptoms.

## Unmatched Wording and Suggestions

Unsupported or uncertain wording is preserved rather than silently converted into a symptom.

For example:

```text
I have fever and a skin rash
```

recognises:

```text
Fever
```

while leaving:

```text
skin rash
```

as unmatched wording.

Near matches can be returned as review-only suggestions.

For example:

```text
throt pane
```

can suggest:

```text
Sore throat
```

without automatically confirming it.

## Symptom Confirmation

Before prediction, recognised symptoms are returned in a structured confirmation format.

The confirmation structure contains:

- Canonical symptom code
- Display name
- Model feature or features
- Matched input wording
- Detected language
- Exact or fuzzy match type
- Match score
- Red-flag status
- Confirmation state
- Unmatched wording
- Possible suggestions

Recognised symptoms initially use:

```text
confirmed = false
```

so that the user can review the symptoms before prediction.

## Red-Flag Handling

The NLP layer identifies selected urgent or concerning symptom patterns.

Examples include:

- Coughing up blood
- Significant shortness of breath
- High-pitched breathing sound
- Chest pain even at rest
- Blue lips or face

Some safety-only red flags may not correspond to active Random Forest features.

They can still trigger safety guidance before model inference.

## Automated NLP Tests

The automated NLP tests are stored in:

```text
tests/test_symptom_mapper.py
```

Run the full test suite with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The current suite contains 12 automated tests covering:

- English symptom input
- Swahili symptom input
- Mixed-language input
- Mixed English and Swahili input
- Multi-feature symptom mapping
- Fuzzy typo matching
- Unmatched wording
- Near-match suggestions
- Red-flag detection
- Safety-only red flags
- Confirmation state
- Unrelated text rejection

Current test result:

```text
Ran 12 tests

OK
```

## Backend Integration

The backend should load the following production artifacts:

```text
models/respiratory_random_forest_v1.joblib
models/model_features.json
models/disease_classes.json
models/model_metadata.json
nlp/canonical_symptoms.json
```

The general prediction workflow is:

```text
User symptom text
        ↓
NLP symptom mapping
        ↓
Recognised symptoms
        ↓
User confirmation
        ↓
Red-flag safety check
        ↓
Canonical symptoms
        ↓
198-feature model vector
        ↓
Random Forest predict_proba()
        ↓
Top 3 respiratory condition patterns
        ↓
Confidence values
        ↓
Explanation and health-awareness guidance
```

The backend must construct the prediction vector using the exact feature order stored in:

```text
models/model_features.json
```

Age and sex are added directly as demographic model inputs.

Confirmed canonical symptoms are converted into their corresponding DDXPlus features.

## Important Limitations

### Synthetic Dataset

DDXPlus is a synthetic dataset generated from a medical knowledge base rather than real patient records.

The reported model performance therefore shows how well the machine-learning system learns patterns represented in DDXPlus.

It must not be interpreted as validated real-world clinical diagnostic accuracy.

### Restricted Disease Scope

The system is restricted to the 21 respiratory conditions selected for this project.

Conditions outside this scope cannot be predicted by the model.

### Sparse Real-User Input

Synthetic DDXPlus patients may contain more evidence than a real user would normally enter.

Real users may provide only a small number of symptoms.

For this reason, confirmation, confidence values, red-flag checks and safety guidance remain important parts of the final application.

### Language Coverage

DDXPlus evidence questions are primarily provided in English and French.

Swahili support in this project comes from the controlled alias-mapping layer developed for the prototype.

The current Swahili vocabulary is not a complete validated medical lexicon.

### Health-Awareness Purpose

The system provides preliminary health-awareness information.

It does not diagnose disease and should not be used to replace professional medical assessment.

## Health Awareness Disclaimer

This system is intended for educational and health-awareness purposes only.

The output represents patterns learned from the project dataset and must not be treated as:

- A medical diagnosis
- A prescription
- Professional medical advice
- A replacement for a qualified healthcare professional

Users should seek appropriate medical attention when symptoms are severe, worsening, urgent or concerning.

## Reproducing the NLP Component

Build the active feature catalog:

```powershell
python .\scripts\build_symptom_mapping.py
```

Build the canonical symptom mapping:

```powershell
python .\scripts\build_canonical_symptoms.py
```

Run an NLP example:

```powershell
python .\nlp\symptom_mapper.py "I have fever na kikohozi"
```

Run the automated tests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Recommended Workflow

The main project workflow is:

```text
1. Prepare DDXPlus respiratory data
2. Perform exploratory data analysis
3. Train and compare classification models
4. Select the Random Forest production model
5. Evaluate the untouched test dataset
6. Generate explainability outputs
7. Save production model artifacts
8. Build canonical symptom mappings
9. Add English and Swahili aliases
10. Process mixed-language symptom input
11. Apply fuzzy matching and unmatched-term handling
12. Confirm recognised symptoms
13. Convert confirmed symptoms to model features
14. Run backend prediction
15. Return Top 3 condition patterns with health-awareness guidance
```

## Dataset Reference

Fansi Tchango, A., Goel, R., Wen, Z., Martel, J., & Ghosn, J. (2022).  
**DDXPlus: A New Dataset for Automatic Medical Diagnosis.**  
Advances in Neural Information Processing Systems 35, Datasets and Benchmarks Track.

## Model and Software References

Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5-32.

Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems 30*.

Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research, 12*, 2825-2830.
