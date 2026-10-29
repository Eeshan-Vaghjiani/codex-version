"""Exercise the supplied cases through a locally running API; no disease ground truth.

Run after local migration/seed. Never points to a production server or edits model
selection. Saves the current active version's actual extraction and flow results.
"""
import argparse
import json
import uuid
from pathlib import Path
from urllib.parse import urlparse
import httpx

CASES = [
    'I have fever.',
    'Runny nose, for a few days with headache and sore throat.',
    'I have a cough and fever.', 'I have a cough.',
    'I have a runny nose, sneezing and a mild cough.',
    'I have had a cough and fever for two days.',
    'I have had a cough for several weeks and have been losing weight.',
    'I have a cough and I am struggling to breathe.', 'I feel unwell.',
    'I have a cough, but I do not have a fever.',
    'Nina homa na kikohozi.', 'Nina kikohozi lakini sina homa.',
]


def run(base_url):
    if urlparse(base_url).hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('This software-audit script permits loopback API servers only.')
    results = []
    with httpx.Client(base_url=base_url, timeout=60) as client:
        credentials = {'email': f'audit-cases-{uuid.uuid4().hex}@example.com',
                       'password': 'LocalAuditPassword2026!'}
        registered = client.post('/auth/register', json=credentials)
        registered.raise_for_status()
        login = client.post('/auth/login', json=credentials)
        login.raise_for_status()
        client.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
        for number, text in enumerate(CASES, 1):
            mapping_response = client.post('/nlp/map', json={'text': text})
            mapping_response.raise_for_status()
            mapping = mapping_response.json()
            confirmed = [item['code'] for item in mapping['recognised_symptoms']
                         if item.get('status', 'present') == 'present'
                         and item.get('reported_subject') != 'other_person']
            payload = {'age': 21, 'sex': 'M', 'text': text, 'confirmed_codes': confirmed,
                       'follow_up_answers': []}
            questions = []
            for _ in range(6):
                response = client.post('/predict', json=payload)
                response.raise_for_status()
                result = response.json()
                if result['status'] != 'needs_follow_up':
                    break
                question = result['follow_up_question']
                assert question['id'] not in questions
                questions.append(question['id'])
                values = {item['value'] for item in question['options']}
                payload['follow_up_answers'].append({'question_id': question['id'],
                                                     'answer': 'no' if 'no' in values else 'unknown'})
            else:
                raise AssertionError('Follow-up limit exceeded')
            assert len(questions) <= 5
            assert (result['status'] == 'urgent_review') == (number == 8)
            results.append({'case': number, 'input': text, 'mapping': mapping,
                            'questions': questions, 'request': payload, 'result': result})
    return {'purpose': 'Observed software behavior; no diagnostic ground truth or clinical validation',
            'demographics': {'age': 21, 'sex': 'M'}, 'cases': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([{'case': item['case'], 'status': item['result']['status'],
                       'questions': len(item['questions']),
                       'candidates': len(item['result']['predictions'])} for item in report['cases']]))
