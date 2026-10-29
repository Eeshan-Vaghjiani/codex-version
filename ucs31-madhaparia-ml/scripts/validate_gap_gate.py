"""Check one predeclared V3 gap candidate on a separate source-validation fold.

See docs/GAP_VALIDATION_PROTOCOL.md. The parent fold had reporting-only metrics
in earlier work; this is not new patient data or Kenyan clinical validation.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inference.primary_selection import GAP_POLICY_PATH, POLICY_PATH, load_gap_policy, load_primary_policy
from inference.v3_predictor import MODEL_PATH, load_v3_bundle
from scripts import evaluate_primary_selection as evaluation
from scripts.train_v3_partial_evidence import masks, score, subset

GAP, FLOOR = .15, .60
OUT = ROOT / 'reports/gap_validation'


def candidate_mask(base, probabilities, present_count):
    ranked = np.sort(probabilities, axis=1)
    return (base & (present_count >= 2) & (ranked[:, -1] >= FLOOR) &
            (ranked[:, -1] - ranked[:, -2] >= GAP))


def write_reports(data, splits, reporting, groups, gate):
    policy, bundle = load_primary_policy(), load_v3_bundle()
    OUT.mkdir(parents=True, exist_ok=True)
    evaluation.OUT = OUT
    evaluation.SCENARIOS = [(1, 0), (2, 0), (3, 0), (3, 3), (5, 0), (5, 2), (8, 0), (8, 5)]
    result = {'clinical_validation': False, 'model_unchanged': True, 'gate': gate,
        'split_profile_counts': {name: len(value) for name, value in groups.items()}, 'source_splits': splits,
        'reporting': evaluation.save_evaluation('reporting', reporting, bundle, policy),
        'test': evaluation.save_evaluation('test', data['test'], bundle, policy)}
    recall = {}
    for count in (1, 2, 3):
        p, a = masks(data['test'], count, 0)
        eligible = p.sum(axis=1) > 0
        sample = subset(data['test'], eligible)
        probabilities = score(bundle, p[eligible], a[eligible], sample)
        _, classes, _ = evaluation.summarize(sample['y'], probabilities)
        recall[str(count)] = {name: classes[name]['recall'] for name in ('Pneumonia', 'Tuberculosis', 'Bronchitis', 'Influenza')}
    result['underlying_sparse_per_class_recall'] = recall
    evaluation.dump(OUT / 'evaluation.json', result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluate-only', action='store_true', help='Report frozen gate; never refit it')
    args = parser.parse_args()
    if GAP_POLICY_PATH.exists() and not args.evaluate_only:
        raise ValueError('Gap artifact already frozen; refusing to refit after evaluation')
    if args.evaluate_only and not GAP_POLICY_PATH.exists():
        raise ValueError('No frozen gap artifact to evaluate')
    data, splits = evaluation.cohorts()
    parent = data['validation']
    calibration = subset(parent, parent['signature'] % 8 == 3)
    reporting = subset(parent, parent['signature'] % 8 == 7)
    groups = {name: set(values['signature'].tolist()) for name, values in {
        'tuning': data['tuning'], 'old_calibration': data['calibration'],
        'gap_calibration': calibration, 'gap_reporting': reporting, 'test': data['test']}.items()}
    for i, name in enumerate(groups):
        for other in list(groups)[i + 1:]:
            if groups[name] & groups[other]:
                raise ValueError('Source profile overlap in gap-validation folds')
    if args.evaluate_only:
        gate = load_gap_policy()
        write_reports(data, splits, reporting, groups, gate)
        return
    policy, bundle = load_primary_policy(), load_v3_bundle()
    entries = {}
    for key, original in policy['buckets'].items():
        p, a = masks(calibration, original['present_count'], original['absent_count'])
        counts, negatives = p.sum(axis=1), a.sum(axis=1)
        exact = (counts == original['present_count']) & (negatives == original['absent_count'])
        x = subset(calibration, exact)
        p, a, counts, negatives = p[exact], a[exact], counts[exact], negatives[exact]
        probabilities = score(bundle, p, a, x)
        base = evaluation.accept_vectorized(policy, probabilities, counts, negatives, p, apply_gap=False)
        accepted = candidate_mask(base, probabilities, counts)
        n = int(accepted.sum())
        errors = int((probabilities.argmax(axis=1)[accepted] != x['y'][accepted]).sum())
        bound = evaluation.upper_risk(errors, n, policy['per_bucket_delta'])
        entries[key] = {'enabled': bool(n and bound <= policy['target_source_selective_error']),
                        'cases': len(x['y']), 'accepted': n, 'errors': errors, 'risk_upper_bound': bound}
    gate = {'policy_version': 'v3_relative_gap_v1', 'clinical_validation': False,
        'model_sha256': evaluation.digest(MODEL_PATH), 'base_policy_sha256': evaluation.digest(POLICY_PATH),
        'protocol_sha256': evaluation.digest(ROOT.parent / 'docs/GAP_VALIDATION_PROTOCOL.md'),
        'minimum_relative_gap': GAP, 'minimum_relative_score': FLOOR, 'minimum_present_count': 2,
        'test_used_for_selection': False, 'buckets': entries,
        'source_note': 'Separate complete-profile source-validation fold (%8==3), previously reporting-only in aggregate. Not new patients; not Kenyan clinical validation.',
        'gap_calibration_profiles': len(calibration['y']), 'gap_reporting_profiles': len(reporting['y'])}
    # Freeze before calculating the reporting/test metrics. Never retune failures.
    evaluation.dump(GAP_POLICY_PATH, gate)
    serving = ROOT.parent / 'ucs31-madhaparia-backend/app/ml/artifacts/v3_gap_selection.json'
    serving.write_bytes(GAP_POLICY_PATH.read_bytes())
    load_gap_policy.cache_clear()
    load_gap_policy()
    write_reports(data, splits, reporting, groups, gate)
    print('Enabled evidence buckets:', sum(entry['enabled'] for entry in entries.values()), '/', len(entries), flush=True)


if __name__ == '__main__':
    main()
