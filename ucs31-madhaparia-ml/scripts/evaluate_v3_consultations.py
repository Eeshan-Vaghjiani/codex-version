"""Matched frozen-model comparison and source-grounded question rollouts."""
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, log_loss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.train_v3_partial_evidence import CLASSES, FEATURES, OUTPUT, masks, read_source, score, subset
from inference.v3_predictor import load_v3_bundle, predict_v3, question_information_gain


def summarize(actual, probabilities, labels):
    labels = np.asarray(labels)
    predicted = labels[probabilities.argmax(axis=1)]
    true = np.array(CLASSES)[actual]
    order = np.argsort(-probabilities,axis=1)
    report = classification_report(true,predicted,labels=CLASSES,output_dict=True,zero_division=0)
    return {"cases":len(actual),"accuracy":float((predicted==true).mean()),
            "top3_recall":float(np.any(labels[order[:,:3]]==true[:,None],axis=1).mean()),
            "macro_f1_21_classes":report["macro avg"]["f1-score"],
            "log_loss":float(log_loss(true,probabilities,labels=labels))}


def legacy_scores(model, present, absent, data, version):
    names = list(model.feature_names_in_)
    values = np.zeros((len(present),len(names)),dtype=np.float32)
    values[:,names.index("AGE")] = data["age"]
    values[:,names.index("SEX_M")] = data["sex"]
    for fi,feature in enumerate(FEATURES):
        positive = feature if version=="v1" else feature+"__present"
        if positive in names:
            values[:,names.index(positive)] = present[:,fi]
        if version=="v2" and feature+"__absent" in names:
            values[:,names.index(feature+"__absent")] = absent[:,fi]
    return model.predict_proba(pd.DataFrame(values,columns=names))


def main():
    train, val, test = read_source("train"), read_source("validate"), read_source("test")
    clean_val = subset(val,~np.isin(val["signature"],train["signature"]))
    validation = subset(clean_val,clean_val["signature"]%2 != 0)
    test = subset(test,~np.isin(test["signature"],np.concatenate([train["signature"],val["signature"]])))
    bundle = load_v3_bundle()
    v1 = joblib.load(ROOT / "models/respiratory_random_forest_v1.joblib")
    v2 = joblib.load(ROOT / "models/rf_v2_23class_prototype.joblib")
    report = {"methodology":"Identical original source groups, native 34-feature sparse masks; V1 cannot encode explicit negative evidence; V2 ignores its negative columns and the two native pain-location categories. No classes removed from legacy predictions.","matched_test":{},"question_rollout":{}}
    for count, negatives in ((1,0),(2,0),(3,0),(3,3)):
        present,absent = masks(test,count,negatives)
        eligible=present.sum(axis=1)>0
        p,a,data=present[eligible],absent[eligible],subset(test,eligible)
        name=f"{count}_positive_{negatives}_negative"
        report["matched_test"][name] = {
            "v1": summarize(data["y"],legacy_scores(v1,p,a,data,"v1"),v1.classes_),
            "v2": summarize(data["y"],legacy_scores(v2,p,a,data,"v2"),v2.classes_),
            "v3": summarize(data["y"],score(bundle,p,a,data),CLASSES)}
        print(name,report["matched_test"][name],flush=True)
    candidates=["E_181","E_97","E_144","E_214","E_77","E_162","E_50","E_91","E_201"]
    for split,data in (("validation",validation),("test",test)):
        rng=np.random.default_rng(20261028)
        sample=subset(data,rng.choice(len(data["y"]),min(2000,len(data["y"])),replace=False))
        p,a=masks(sample,1)
        snapshots=[];questions=Counter();all_probabilities=[]
        gains=np.zeros((len(p),3))
        for turn in range(4):
            eligible=p.sum(axis=1)>0
            probabilities=score(bundle,p,a,sample)
            all_probabilities.append(probabilities)
            snapshots.append(summarize(sample["y"][eligible],probabilities[eligible],CLASSES))
            if turn==3:
                break
            for i in range(len(p)):
                present=[FEATURES[j] for j in np.flatnonzero(p[i])]
                absent=[FEATURES[j] for j in np.flatnonzero(a[i])]
                ranked=question_information_gain(present,absent,int(sample["age"][i]),"M" if sample["sex"][i] else "F",candidates)
                if not ranked:
                    continue
                gains[i,turn]=ranked[0]["information_gain"]
                feature=ranked[0]["feature"];fi=FEATURES.index(feature)
                # The simulated source, rather than a manufactured answer,
                # determines each yes/no response.
                if sample["x"][i,fi]==1:
                    p[i,fi]=1
                else:
                    a[i,fi]=1
                questions[feature]+=1
        report["question_rollout"][split]={"sample_size":len(sample["y"]),"initial_plus_0_to_3_questions":snapshots,"question_counts":dict(questions),"limitations":"Synthetic source yes/no truth; no emergency stop used in classification experiment, so this is not triage validation or a clinical interview evaluation."}
        if split=="validation":
            policies={}
            for threshold in (0.,.01,.02,.05):
                turns=np.full(len(p),3,dtype=int)
                for turn in range(3):
                    turns[(turns==3)&(gains[:,turn]<threshold)]=turn
                chosen=np.array([all_probabilities[turns[i]][i] for i in range(len(p))])
                policies[str(threshold)]={**summarize(sample["y"],chosen,CLASSES),
                    "mean_model_questions":float(turns.mean()),
                    "question_count_distribution":{str(k):int((turns==k).sum()) for k in range(4)},
                    "policy_note":"Question utility in nats; not a clinical certainty or triage threshold. Selected on validation only."}
            report["validation_question_stop_policies"]=policies
            print("validationstop",policies,flush=True)
        print("rollout",split,snapshots,flush=True)
    (OUTPUT/"matched_comparison_and_rollouts.json").write_text(json.dumps(report,indent=2),encoding="utf8")


if __name__=="__main__":
    main()
