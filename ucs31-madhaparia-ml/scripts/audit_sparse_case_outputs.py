"""Reproduce reported symptom cases and isolate demographic model effects.

Reads the preserved baseline NLP snapshot, so subsequent NLP repairs cannot
rewrite the original observation. Disease outputs here are observations,
never expected diagnoses or ground truth.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "reports/autonomous_audit"


def main():
    cases = json.loads((OUTPUT / "baseline_nlp_cases.json").read_text(encoding="utf8"))
    v1_features = json.loads((ROOT / "models/model_features.json").read_text())
    schema = json.loads((ROOT / "models/v2_feature_schema.json").read_text())
    models = {"v1": joblib.load(ROOT / "models/respiratory_random_forest_v1.joblib"),
              "v2": joblib.load(ROOT / "models/rf_v2_23class_prototype.joblib")}
    rows = []
    for case in cases:
        records = case["nlp"]["recognised_symptoms"]
        present = sorted({f for r in records if r.get("status") == "present"
                          and r.get("reported_subject") != "other_person" for f in r["features"]})
        absent = sorted({f for r in records if r.get("status") == "absent"
                         and r.get("reported_subject") != "other_person" for f in r["features"]})
        case["present_features"] = present
        case["absent_features"] = absent
        case["observations"] = []
        for version, model in models.items():
            features = v1_features if version == "v1" else schema["feature_names"]
            for age in (5, 21, 65):
                for sex in ("M", "F"):
                    vector = {f: 0. for f in features}
                    vector.update(AGE=float(age), SEX_M=float(sex == "M"))
                    for code in present:
                        name = code if version == "v1" else code + "__present"
                        if name in vector:
                            vector[name] = 1.
                    for code in absent:
                        name = code + "__absent"
                        if version == "v2" and name in vector:
                            vector[name] = 1.
                    frame = pd.DataFrame([vector], columns=features)
                    score = model.predict_proba(frame)[0]
                    order = np.argsort(-score, kind="stable")[:3]
                    observation = {"version": version, "age": age, "sex": sex,
                        "top_3": [{"condition": str(model.classes_[i]), "raw_score": float(score[i])} for i in order],
                        "ordinary_inference_should_be_skipped": not bool(present) or bool(case["nlp"]["has_red_flag"])}
                    case["observations"].append(observation)
                    rows.append({"case": case["case"], "version": version, "age": age, "sex": sex,
                                 "top_condition": observation["top_3"][0]["condition"],
                                 "raw_score": observation["top_3"][0]["raw_score"]})
    report = {"purpose": "Raw frozen-model observations, not clinical diagnoses or expected labels",
              "demographics": "Only AGE and SEX_M vary within each case/version; identical extracted symptom vectors",
              "v1_absence_limitation": "V1 has no independent explicit-absence features; zeros conflate unmentioned and absent",
              "v2_absence_feature_importance_sum": float(sum(v for k,v in zip(models["v2"].feature_names_in_, models["v2"].feature_importances_) if k.endswith("__absent"))),
              "v2_demographic_feature_importance": {k: float(v) for k,v in zip(models["v2"].feature_names_in_, models["v2"].feature_importances_) if k in ("AGE", "SEX_M")},
              "cases": cases}
    (OUTPUT / "baseline_model_cases.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    pd.DataFrame(rows).to_csv(OUTPUT / "demographic_case_outputs.csv", index=False)
    print(json.dumps([r for r in rows if r["age"] == 21], indent=2))


if __name__ == "__main__":
    main()
