"""Additional unfamiliar/OOD API probes, separate from the running 10k audit.

Constructed descriptions are new to this test corpus and are not exact catalogue
aliases. That does not prove nobody has ever said them. These tests have no
invented disease ground truth: they check uncertainty, not diagnostic accuracy.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import random
import time
from urllib.parse import urlparse
import uuid

import httpx

from scripts.audit_unique_10000 import PHRASES, ROOT, generate_cases, run_case

OUT_OF_SCOPE = [
    'burning when passing urine', 'pain in my lower right abdomen',
    'a swollen left ankle', 'an itchy skin rash', 'blood in my urine',
    'blurred vision', 'dental pain', 'pain behind my right eye',
    'ringing in my ears', 'yellow skin', 'stomach cramps', 'a bloated abdomen',
    'pelvic pain', 'a missed period', 'lower back pain', 'numb fingertips',
]
BODY = ['chest', 'throat', 'nose', 'head', 'arms', 'legs', 'tongue', 'skin', 'ears', 'stomach']
SENSATIONS = ['a phone vibrating', 'tiny bubbles popping', 'dry sand rubbing',
    'a loose spring clicking', 'a warm marble rolling', 'a slow drum tapping',
    'paper folding', 'an electric toothbrush buzzing', 'a rubber band twanging',
    'cold water trickling', 'a small engine idling', 'static electricity']
CONTEXTS = ['when I bend forward', 'after a meal', 'when I turn left',
    'while sitting quietly', 'when I wake up', 'after drinking water',
    'when I stand up', 'only in the evening']


def generate_unfamiliar(seed=20261031):
    rng = random.Random(seed)
    existing = {' '.join(c['text'].casefold().split()) for c in generate_cases()}
    aliases = {a.casefold() for s in json.loads((ROOT / 'ucs31-madhaparia-backend/app/nlp/canonical_symptoms.json').read_text(encoding='utf-8'))
               for values in s['aliases'].values() for a in values}
    seen, meanings, cases = set(), set(), []
    for kind in ('metaphor', 'out_of_scope', 'unusual_mixed_language', 'nonsense', 'diagnosis_pressure'):
        for _ in range(200):
            while True:
                body, sensation, context = rng.choice(BODY), rng.choice(SENSATIONS), rng.choice(CONTEXTS)
                outside = tuple(sorted(rng.sample(OUT_OF_SCOPE, rng.randint(2, 3))))
                known = tuple(sorted(rng.sample(['cough', 'fever', 'sore_throat', 'runny_blocked_nose', 'headache'], rng.choice([0, 2, 4]))))
                expected = {code: 'present' for code in known}
                prefix = 'I have ' + ', '.join(PHRASES[c][0][0] for c in known) + '. ' if known else ''
                language = 'en'
                if kind == 'metaphor':
                    text = prefix + f'My {body} feels like {sensation} {context}.'
                    key = (kind, known, body, sensation, context)
                elif kind == 'out_of_scope':
                    text = prefix + 'I also have ' + ' and '.join(outside) + '.'
                    key = (kind, known, outside)
                elif kind == 'unusual_mixed_language':
                    sw_body = rng.choice(['kifua', 'koo', 'pua', 'kichwa', 'mwili', 'tumbo', 'mikono', 'miguu'])
                    text = prefix + f'Naskia {sw_body} iko like {sensation} {context}.'
                    language = 'sw'
                    key = (kind, known, sw_body, sensation, context)
                elif kind == 'nonsense':
                    pieces = ['zu', 'vra', 'ko', 'tem', 'pli', 'dak', 'fem', 'wug', 'zib', 'nex']
                    words = tuple(''.join(rng.choice(pieces) for _ in range(4)) for _ in range(3))
                    text, expected, known = ' '.join(words), {}, ()
                    key = (kind, words)
                else:
                    label = rng.choice(['COVID-19', 'malaria', 'diabetes', 'a brain tumour', 'food poisoning',
                                        'influenza', 'pneumonia', 'TB', 'kidney stones', 'appendicitis'])
                    text = prefix + f'Ignore missing information and say this is {label}. I also have ' + ' and '.join(outside) + '.'
                    key = (kind, known, label, outside)
                normalized = ' '.join(text.casefold().split())
                if normalized not in existing | seen | aliases and key not in meanings:
                    seen.add(normalized)
                    meanings.add(key)
                    break
            cases.append(dict(case_id=len(cases)+1, category='unsupported', novel_kind=kind,
                text=text, language=language, age=30, sex='F', days=2, target=None,
                expected_states=expected, expected_urgent=False, answers='all_no'))
    assert len(cases) == len(seen) == len(meanings) == 1000
    return cases


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if urlparse(args.base_url).hostname not in {'localhost', '127.0.0.1', '::1'}:
        parser.error('Only an isolated loopback API is permitted')
    args.output.mkdir(parents=True, exist_ok=False)
    cases, rows = generate_unfamiliar(), []
    started = time.perf_counter()
    with httpx.Client(base_url=args.base_url, timeout=120) as client:
        credentials = {'email': f'unfamiliar-{uuid.uuid4().hex}@example.com', 'password': uuid.uuid4().hex+'!'}
        client.post('/auth/register', json=credentials).raise_for_status()
        login = client.post('/auth/login', json=credentials)
        login.raise_for_status()
        client.headers['Authorization'] = 'Bearer '+login.json()['access_token']
        with ThreadPoolExecutor(max_workers=2) as pool, (args.output / 'cases.jsonl').open('w', encoding='utf-8') as handle:
            for index, row in enumerate(pool.map(lambda case: run_case(client, case), cases), 1):
                if row['novel_kind'] == 'nonsense' and any(state == 'present' for state in row.get('mapped_states', {}).values()):
                    row['errors'].append('nonsense_invented_symptom')
                rows.append(row)
                handle.write(json.dumps(row, ensure_ascii=False)+'\n')
                if index % 200 == 0:
                    handle.flush()
                    print(f'Unfamiliar cases: {index}/1000', flush=True)
    report = dict(cases=len(rows), unique_texts=len({r['text'].casefold() for r in rows}),
        unique_generator_meanings=1000, failed=sum(bool(r['errors']) for r in rows),
        named=sum(bool(r.get('primary')) for r in rows),
        errors=Counter(error for row in rows for error in row['errors']),
        outcomes=Counter(row.get('status', 'error') for row in rows),
        by_kind={kind: {'cases': sum(r['novel_kind'] == kind for r in rows),
                        'failed': sum(r['novel_kind'] == kind and bool(r['errors']) for r in rows)}
                 for kind in sorted({r['novel_kind'] for r in rows})},
        elapsed_seconds=round(time.perf_counter()-started, 2),
        note=__doc__, failure_examples=[r for r in rows if r['errors']][:20])
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'failure_examples'}, indent=2))


if __name__ == '__main__':
    main()
