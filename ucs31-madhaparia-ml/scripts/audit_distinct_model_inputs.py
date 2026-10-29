"""10k distinct *effective* V3 inputs; label-blind source-test stress sample.

Unlike merely unique full source records or literal ages, uniqueness here uses
present/absent features and the demographic group actually consumed by V3.
Duplicates are skipped, not counted. No training or threshold selection.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inference.primary_selection import classify_primary, VIRAL_UPPER_RESPIRATORY_FAMILY
from inference.v3_predictor import MODEL_PATH, _group, load_v3_bundle, predict_v3
from scripts.evaluate_primary_selection import cohorts, unique_profiles
from scripts.train_v3_partial_evidence import FEATURES, masks, subset


def run():
    data, _ = cohorts()
    source = unique_profiles(data['test'])
    bundle = load_v3_bundle()
    seen, signatures, counts = set(), set(), Counter()
    buckets, named_errors, family_labels = {}, Counter(), Counter()
    for attempt, index in enumerate(np.random.default_rng(20261031).permutation(len(source['y']))):
        record = subset(source, [index])
        positive_count, negative_count = 1 + attempt % 8, (attempt // 8) % 6
        p, a = masks(record, positive_count, negative_count, seed=20261031 + attempt)
        present = [FEATURES[j] for j in np.flatnonzero(p[0])]
        absent = [FEATURES[j] for j in np.flatnonzero(a[0])]
        if not present:
            counts['empty_profiles_skipped'] += 1
            continue
        age, sex = int(record['age'][0]), 'M' if record['sex'][0] else 'F'
        key = (tuple(present), tuple(absent), _group(bundle, age, sex))
        if key in seen:
            counts['duplicate_effective_inputs_skipped'] += 1
            continue
        seen.add(key)
        signatures.add(int(record['signature'][0]))
        actual = bundle['classes'][int(record['y'][0])]
        chosen = classify_primary(present, absent, age, sex)
        ranked = predict_v3(present, absent, age, sex, top_k=1)
        counts['cases'] += 1
        counts['underlying_top1_correct'] += int(ranked['predictions'][0]['condition'] == actual)
        counts[chosen['status']] += 1
        bucket = buckets.setdefault(f'{len(present)}:{len(absent)}', Counter())
        bucket['cases'] += 1
        if chosen['status'] == 'eligible':
            predicted = chosen['primary_prediction']['condition']
            correct = predicted == actual
            counts['named_correct'] += int(correct)
            bucket['named'] += 1
            bucket['named_correct'] += int(correct)
            if not correct:
                named_errors[f'{actual} -> {predicted}'] += 1
        if chosen['status'] == 'family':
            counts['family_label_in_family'] += int(actual in VIRAL_UPPER_RESPIRATORY_FAMILY)
            family_labels[actual] += 1
        if counts['cases'] == 10000:
            break
    assert counts['cases'] == len(seen) == len(signatures) == 10000, 'Cannot claim 10k distinct inputs'
    named, family = counts['eligible'], counts['family']
    return dict(cases=10000, unique_effective_model_inputs=len(seen), unique_source_profiles=len(signatures),
        seed=20261031, model_sha256=hashlib.sha256(Path(MODEL_PATH).read_bytes()).hexdigest(),
        demographic_mode=bundle['demographic_mode'], counts=counts, evidence_buckets=buckets,
        named_coverage=named/10000, named_selective_accuracy=counts['named_correct']/named if named else None,
        correct_named_per_all_cases=counts['named_correct']/10000,
        underlying_top1_accuracy=counts['underlying_top1_correct']/10000,
        family_source_label_agreement=counts['family_label_in_family']/family if family else None,
        named_error_pairs=named_errors, family_source_labels=family_labels,
        clinical_validation=False,
        note='Existing DDXPlus test fold, excluding training/validation signatures. Label-blind randomized source order and masks; repeated effective inputs skipped. This diversity-selected sample is not population-representative or fresh independent validation. Direct model/selection only, not API triage. Family agreement is source-class membership, not proof of a virus. No thresholds changed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = run()
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'evidence_buckets'}, indent=2))
