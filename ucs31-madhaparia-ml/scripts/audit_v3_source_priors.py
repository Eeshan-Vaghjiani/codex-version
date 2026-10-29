"""Measure sparse symptom associations without assigning new disease labels."""
import json
from pathlib import Path

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    frame=pd.read_csv(ROOT/"data/processed/train.csv",usecols=["PATHOLOGY","E_201","E_91"])
    counts=frame.PATHOLOGY.value_counts()
    report={"source":"Original DDXPlus respiratory source training split",
        "clinical_validation":False,"training_class_counts":counts.to_dict(),"patterns":{}}
    for name,mask in (("cough",frame.E_201==1),("fever",frame.E_91==1),
                      ("cough_and_fever",(frame.E_201==1)&(frame.E_91==1)),
                      ("cough_and_no_fever",(frame.E_201==1)&(frame.E_91==0))):
        selected=frame.loc[mask,"PATHOLOGY"].value_counts().reindex(counts.index,fill_value=0)
        likelihood=selected/counts
        uniform=likelihood/likelihood.sum()
        report["patterns"][name]={"matching_source_records":int(mask.sum()),
            "counts":selected.to_dict(),
            "empirical_source_conditional_distribution":(selected/selected.sum()).sort_values(ascending=False).to_dict(),
            "uniform_class_prior_counterfactual":uniform.sort_values(ascending=False).to_dict()}
    report["limitations"]=["Source generator deliberately caps disease rates; empirical priors are not local population prevalence",
        "Uniform-prior counterfactual isolates a class-prior effect and does not reproduce the RF training algorithm",
        "No model or source record is changed by this audit"]
    target=ROOT/"reports/consultation_v3/source_priors.json"
    target.write_text(json.dumps(report,indent=2),encoding="utf8")
    print(target)


if __name__=="__main__":
    main()
