
import json
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Load the original Random Forest V1 model
model = joblib.load(
    ROOT / "models" / "respiratory_random_forest_v1.joblib"
)

features = json.loads(
    (ROOT / "models" / "model_features.json").read_text(
        encoding="utf-8"
    )
)

symptoms = json.loads(
    (ROOT / "nlp" / "canonical_symptoms.json").read_text(
        encoding="utf-8"
    )
)

symptom_features = {
    symptom["code"]: symptom["features"]
    for symptom in symptoms
}

# Test incomplete symptom inputs
test_cases = [
    ("Fever only", ["fever"], 1),
    ("Cough only", ["cough"], 1),
    ("Fever + cough (male)", ["fever", "cough"], 1),
    ("Fever + cough (female)", ["fever", "cough"], 0),
    ("Fever + cough + muscle aches",
     ["fever", "cough", "muscle_aches"], 1),
    ("Fever + cough + sore throat",
     ["fever", "cough", "sore_throat"], 1),
    ("Runny nose + sore throat",
     ["runny_blocked_nose", "sore_throat"], 1),
    ("Cough + sweating + weight loss",
     ["cough", "heavy_sweating", "weight_loss"], 1),
]

print("\nRANDOM FOREST V1 - SPARSE INPUT EVALUATION\n")

for name, codes, sex_m in test_cases:

    # Reproduce Version 1 input encoding
    row = {feature: 0 for feature in features}

    row["AGE"] = 21
    row["SEX_M"] = sex_m

    for code in codes:
        for feature in symptom_features[code]:
            if feature in row:
                row[feature] = 1

    X = pd.DataFrame([row], columns=features)

    probabilities = model.predict_proba(X)[0]

    ranked = sorted(
        zip(model.classes_, probabilities),
        key=lambda item: item[1],
        reverse=True
    )

    print(f"Input: {name}")
    print(f"Prediction: {ranked[0][0]}")
    print(f"Model probability: {ranked[0][1]:.2%}")
    print(f"Second prediction: {ranked[1][0]}")
    print(f"Second probability: {ranked[1][1]:.2%}")
    print("-" * 45)
