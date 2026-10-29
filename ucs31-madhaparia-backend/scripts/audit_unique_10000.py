"""Unique synthetic API journeys plus a separate labelled DDXPlus test sample.

Loopback only. Creates one synthetic account and saved assessments in the target
database: use an isolated audit schema, not a production/development database.
No retraining, threshold selection, clinical labels for invented text, or retries
that could hide failures. JSONL records every attempted API case.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time
from urllib.parse import urlparse
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[2]
PHRASES = {
    'cough': (['a cough', 'coughing', 'a dry cough'], ['kikohozi', 'kikohozi kikavu']),
    'fever': (['a fever', 'high temperature'], ['homa']),
    'sore_throat': (['a sore throat', 'throat pain'], ['koo linauma', 'koo kuuma']),
    'runny_blocked_nose': (['a runny nose', 'running nose', 'a blocked nose'], ['pua inanitoka', 'pua imeziba']),
    'headache': (['a headache', 'head pain'], ['kichwa kinauma', 'kichwa kuuma']),
    'muscle_aches': (['body aches', 'muscle aches'], ['mwili unauma', 'misuli inauma']),
    'tiredness': (['tiredness', 'constant tiredness'], ['uchovu', 'nimechoka']),
    'chills': (['chills', 'shivering'], ['baridi', 'kutetemeka']),
    'hoarse_voice': (['a hoarse voice', 'voice changes'], ['sauti kukwaruza']),
    'wheezing': (['wheezing', 'a whistling sound when breathing out'], ['sauti ya mluzi']),
    'loss_of_smell': (['loss of smell', 'no sense of smell'], ['siwezi kunusa', 'nimepoteza harufu']),
    'itchy_eyes': (['itchy eyes', 'eyes itching'], ['macho yanawasha']),
    'itchy_nose_throat': (['an itchy nose', 'an itchy throat'], ['pua inawasha', 'koo linawasha']),
    'dizziness': (['dizziness', 'feeling dizzy'], ['kizunguzungu']),
}
WARNINGS = [
    ("I cannot breathe", 'en'), ('I have severe chest pain', 'en'),
    ('My lips are turning blue', 'en'), ('I have sudden one-sided weakness', 'en'),
    ('I have headache, fever and a stiff neck', 'en'),
    ('I am coughing a lot of blood', 'en'), ('I have confusion', 'en'),
    ('Siwezi kupumua', 'sw'), ('Nina maumivu makali ya kifua', 'sw'), ('Nimezimia', 'sw'),
]
# Forty percent routine, fifty percent language/safety guards, ten percent
# contradiction/severity cases. No meaningless serial-number suffixes in text.
CATEGORIES = (['routine'] * 8 + ['urgent'] * 2 + ['denial'] * 2 +
              ['other_person'] * 2 + ['unsupported'] * 2 + ['mixed'] * 2 +
              ['contradiction', 'severe'])


def generate_cases(count=10000, seed=20261029):
    rng, seen, cases = random.Random(seed), set(), []
    codes = list(PHRASES)
    for index in range(count):
        category = CATEGORIES[index % len(CATEGORIES)]
        while True:
            language = rng.choice(['en', 'sw']) if category in {'routine', 'mixed'} else 'en'
            selected = rng.sample(codes, rng.randint(2, 6))
            days = rng.choice([1, 2, 3, 5, 7, 14, 21])
            age, sex = rng.choice([0, 2, 16, 24, 35, 48, 65, 80]), rng.choice(['M', 'F'])
            phrases = [rng.choice(PHRASES[c][language == 'sw']) for c in selected]
            if category == 'mixed':
                phrases = [rng.choice(PHRASES[c][i % 2]) for i, c in enumerate(selected)]
            text = ('Nina ' if language == 'sw' else 'I have ') + ', '.join(phrases)
            text += f' kwa siku {days}.' if language == 'sw' else f' for {days} days.'
            target = None
            expected_states = {c: 'present' for c in selected}
            if category == 'urgent':
                warning, language = rng.choice(WARNINGS)
                text = warning + '. ' + text
            elif category in {'denial', 'other_person', 'contradiction'}:
                target = rng.choice([c for c in codes if c not in selected])
                term = PHRASES[target][0][0]
                if category == 'denial':
                    text += f' I do not have {term}.'
                    expected_states[target] = 'absent'
                elif category == 'other_person':
                    text = f'My brother has {term}. ' + text
                else:
                    text += f' I have {term}, but I do not have {term}.'
                    expected_states[target] = 'unknown'
            elif category == 'unsupported':
                text += rng.choice([' I also have a skin rash.', ' I also have abdominal pain.',
                                    ' I also have nausea.', ' I also have ear pain.'])
            elif category == 'severe':
                text = text.replace('I have ', 'I have severe ', 1)
            # Uniqueness means distinct normalized descriptions, not new IDs,
            # ages, answer-pattern repetitions or duplicate CSV rows.
            key = ' '.join(text.casefold().split())
            if key not in seen:
                seen.add(key)
                break
        cases.append(dict(case_id=index + 1, category=category, text=text,
            language=language, age=age, sex=sex, days=days, target=target,
            expected_states=expected_states,
            expected_urgent=category == 'urgent' or (age == 0 and 'fever' in selected),
            answers=rng.choice(['all_no', 'two_unknown', 'disclose', 'mixed'])))
    assert len(seen) == len(cases) == count
    return cases


def choose_answer(question, case):
    values = {option['value'] for option in question['options']}
    if case['answers'] == 'two_unknown':
        return 'unknown'
    qid = question['id']
    if qid in {'breathing_difficulty', 'severe_chest_pain'}:
        return 'no'
    if 'under_3_days' in values:
        return 'under_3_days' if case['days'] < 3 else '3_to_14_days' if case['days'] <= 14 else 'over_14_days'
    if 'mild' in values:
        return 'mild'
    if 'general_low_energy' in values:
        return 'general_low_energy'
    if 'transient' in values:
        return 'transient' if case['answers'] == 'all_no' else 'persistent'
    if 'unintentional' in values:
        return 'unintentional'
    if case['answers'] == 'all_no':
        return 'no'
    if case['answers'] == 'disclose':
        return 'yes'
    return 'yes' if (case['case_id'] + sum(qid.encode())) % 4 == 0 else 'no'


def contract_errors(result):
    errors = []
    primary = result.get('primary_prediction')
    if result.get('predictions') != ([primary] if primary else []):
        errors.append('not_single_primary')
    if result.get('clinical_validation') is not False:
        errors.append('clinical_validation_contract')
    if not result.get('health_guidance') or (result.get('status') != 'urgent_review' and not result.get('next_steps')):
        errors.append('blank_guidance')
    if result.get('status') == 'urgent_review' and primary:
        errors.append('urgent_named')
    if primary:
        if 'covid' in primary.get('condition', '').lower():
            errors.append('covid_prediction')
        percent = primary.get('model_match_percent')
        if primary.get('is_family_answer'):
            if percent is not None or primary.get('family_top_condition'):
                errors.append('family_leaks_specific_class_or_score')
        elif type(percent) is not int or not 0 <= percent <= 100:
            errors.append('invalid_model_match')
    if any(term in json.dumps(result) for term in ('"raw_relative_score"', '"_primary_audit"', '"_audit"')):
        errors.append('private_scores_leaked')
    return errors


def run_case(client, case):
    started, errors, questions = time.perf_counter(), [], []
    row = dict(case)
    try:
        response = client.post('/nlp/map', json={'text': case['text'], 'language': case['language']})
        response.raise_for_status()
        mapping = response.json()
        symptoms = mapping.get('recognised_symptoms', [])
        patient = {s['code']: s.get('status', 'present') for s in symptoms if s.get('reported_subject') != 'other_person'}
        row['mapped_states'] = patient
        row['unmatched'] = mapping.get('unmatched_wording', [])
        row['initial_warning'] = bool(mapping.get('has_red_flag'))
        if row['initial_warning'] and not case['expected_urgent'] and case['category'] in {'routine', 'denial', 'other_person', 'mixed'}:
            errors.append('unexpected_initial_warning')
        if not mapping.get('has_red_flag'):
            for code, expected in case['expected_states'].items():
                if patient.get(code) != expected:
                    errors.append(f'mapping:{code}:{expected}:{patient.get(code, "missing")}')
            if case['category'] == 'other_person' and patient.get(case['target']) == 'present':
                errors.append('other_person_became_patient_evidence')
        confirmed = [s['code'] for s in symptoms if s.get('status', 'present') == 'present'
                     and s.get('reported_subject') != 'other_person']
        body = {k: case[k] for k in ('text', 'age', 'sex', 'language')}
        body.update(confirmed_codes=confirmed, follow_up_answers=[])
        for turn in range(21):
            response = client.post('/predict', json=body)
            response.raise_for_status()
            result = response.json()
            errors.extend(contract_errors(result))
            if result.get('status') != 'needs_follow_up':
                break
            question = result['follow_up_question']
            if question['id'] in questions or turn == 20:
                errors.append('question_loop_or_limit')
                break
            questions.append(question['id'])
            body['follow_up_answers'].append({'question_id': question['id'], 'answer': choose_answer(question, case)})
        if case['expected_urgent'] and (result['status'] != 'urgent_review' or questions):
            errors.append('expected_immediate_warning_bypass')
        if case['answers'] == 'two_unknown' and len(questions) > 2:
            errors.append('two_unknown_stop_failed')
        primary = result.get('primary_prediction')
        if case['category'] in {'unsupported', 'severe'} and primary:
            errors.append('unsupported_or_severe_named')
        prediction_id = result.get('prediction_id')
        if prediction_id:
            response = client.get('/history/' + prediction_id)
            response.raise_for_status()
            saved = response.json()
            if saved.get('primary_prediction') != primary or saved.get('status') != result['status']:
                errors.append('history_changed_result')
        row.update(status=result.get('status'), primary=(primary or {}).get('condition'),
            family=bool((primary or {}).get('is_family_answer')), care_level=result.get('care_level'),
            reasons=result.get('decision', {}).get('reasons', []),
            present_features=result.get('model_features', []), absent_features=result.get('explicitly_absent_features', []))
    except Exception as error:
        errors.append(f'exception:{type(error).__name__}:{error}')
    row.update(errors=sorted(set(errors)), questions=questions,
               elapsed_seconds=round(time.perf_counter() - started, 4))
    return row


def run_api(base_url, output, count, seed, workers):
    if urlparse(base_url).hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Only an isolated loopback API is permitted')
    cases = generate_cases(count, seed)
    summary = dict(cases=count, unique_texts=len({c['text'].casefold() for c in cases}),
        seed=seed, workers=workers, passed=0, failed=0, errors=Counter(), categories={},
        outcomes=Counter(), primary_counts=Counter(), question_counts=Counter())
    latencies, examples = [], []
    with httpx.Client(base_url=base_url, timeout=120) as client:
        client.get('/health').raise_for_status()
        model = client.get('/model/status')
        model.raise_for_status()
        summary['model_status'] = model.json()
        if summary['model_status'].get('model_version') != 'v3_partial_evidence':
            raise ValueError('The audit requires the active frozen V3 model')
        credentials = {'email': f'unique-audit-{uuid.uuid4().hex}@example.com', 'password': uuid.uuid4().hex + '!'}
        client.post('/auth/register', json=credentials).raise_for_status()
        login = client.post('/auth/login', json=credentials)
        login.raise_for_status()
        client.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
        started = time.perf_counter()
        with (output / 'cases.jsonl').open('w', encoding='utf-8') as handle, ThreadPoolExecutor(max_workers=workers) as pool:
            for index, row in enumerate(pool.map(lambda case: run_case(client, case), cases), 1):
                handle.write(json.dumps(row, ensure_ascii=False) + '\n')
                failed = bool(row['errors'])
                summary['failed' if failed else 'passed'] += 1
                bucket = summary['categories'].setdefault(row['category'], dict(cases=0, failed=0))
                bucket['cases'] += 1
                bucket['failed'] += int(failed)
                summary['errors'].update(row['errors'])
                summary['outcomes'][row.get('status', 'error')] += 1
                summary['primary_counts'][row.get('primary') or '(withheld/urgent)'] += 1
                summary['question_counts'][len(row['questions'])] += 1
                latencies.append(row['elapsed_seconds'])
                if failed and len(examples) < 30:
                    examples.append(row)
                if index % 500 == 0:
                    handle.flush()
                    print(f'{index}/{count}; failures={summary["failed"]}; elapsed={time.perf_counter()-started:.0f}s', flush=True)
        summary.update(elapsed_seconds=round(time.perf_counter()-started, 2),
            mean_case_seconds=statistics.mean(latencies), median_case_seconds=statistics.median(latencies),
            p95_case_seconds=sorted(latencies)[int(.95*(len(latencies)-1))], failure_examples=examples)
    return summary


def run_source(count, seed):
    """Existing test fold only; a reporting sample, never threshold tuning."""
    sys.path.insert(0, str(ROOT / 'ucs31-madhaparia-ml'))
    import numpy as np
    from scripts.evaluate_primary_selection import cohorts, unique_profiles
    from scripts.train_v3_partial_evidence import FEATURES, masks, subset
    from inference.primary_selection import classify_primary, VIRAL_UPPER_RESPIRATORY_FAMILY
    from inference.v3_predictor import load_v3_bundle, predict_v3
    data, _ = cohorts()
    test = unique_profiles(data['test'])
    rng = np.random.default_rng(seed)
    if len(test['y']) < count:
        raise ValueError(f'Only {len(test["y"])} unique source-test profiles available; cannot claim {count}')
    sample = subset(test, rng.choice(len(test['y']), count, replace=False))
    bundle = load_v3_bundle()
    totals = Counter(cases=count)
    buckets, inputs = {}, set()
    for group_index, indices in enumerate(np.array_split(np.arange(count), 48)):
        if not len(indices):
            continue
        group = subset(sample, indices)
        positives, negatives = 1 + group_index % 8, group_index // 8
        p, a = masks(group, positives, negatives, seed=seed + group_index)
        for i in range(len(p)):
            present = [FEATURES[j] for j in np.flatnonzero(p[i])]
            absent = [FEATURES[j] for j in np.flatnonzero(a[i])]
            age, sex = int(group['age'][i]), 'M' if group['sex'][i] else 'F'
            inputs.add((tuple(present), tuple(absent), age, sex))
            actual = bundle['classes'][int(group['y'][i])]
            chosen = classify_primary(present, absent, age, sex)
            ranked = predict_v3(present, absent, age, sex, top_k=1)
            correct_top = ranked['predictions'][0]['condition'] == actual
            totals['underlying_top1_correct'] += int(correct_top)
            totals[chosen['status']] += 1
            bucket = buckets.setdefault(f'{len(present)}:{len(absent)}', Counter())
            bucket['cases'] += 1
            if chosen['status'] == 'eligible':
                correct = chosen['primary_prediction']['condition'] == actual
                totals['named_correct'] += int(correct)
                bucket['named'] += 1
                bucket['named_correct'] += int(correct)
            if chosen['status'] == 'family':
                totals['family_label_in_family'] += int(actual in VIRAL_UPPER_RESPIRATORY_FAMILY)
    named, family = totals['eligible'], totals['family']
    return dict(counts=totals, unique_source_profiles=len(set(sample['signature'].tolist())),
        unique_model_inputs=len(inputs), evidence_buckets=buckets,
        named_coverage=named/count, named_selective_accuracy=totals['named_correct']/named if named else None,
        correct_named_per_all_cases=totals['named_correct']/count,
        underlying_top1_accuracy=totals['underlying_top1_correct']/count,
        family_source_label_agreement=totals['family_label_in_family']/family if family else None,
        note=f'Existing DDXPlus test fold, excluding training/validation signatures; {count:,} distinct full source profiles, but partial model inputs may repeat. Source-only classification, not API triage or Kenyan clinical validation. Family agreement means the source class is in the declared family, not a proven viral cause. No threshold changes.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=20261029)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000 or not 1 <= args.workers <= 8:
        parser.error('count must be 1..10000; workers 1..8')
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        clinical_validation=False, note='Synthetic software checks are not disease diagnostic accuracy. Every text is unique. Failures are recorded, not retried or dropped.')
    report = {**metadata, 'api': run_api(args.base_url, args.output, args.count, args.seed, args.workers)}
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    report['source'] = run_source(args.count, args.seed)
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in report['api'].items() if k != 'failure_examples'}, indent=2))
    print(json.dumps(report['source'], indent=2))


if __name__ == '__main__':
    main()
