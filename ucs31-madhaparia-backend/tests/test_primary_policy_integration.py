"""Serving parity, native fatigue meaning and actual selective API decisions."""
import ast
import hashlib
from pathlib import Path

import pytest
from app.nlp.symptom_mapper import build_confirmation_output
from app.services.primary_assessment import RESPIRATORY_FEATURES
from tests.test_v3_consultation import v3_flow, payload, finish


def test_serving_selection_matches_evaluated_runtime_and_both_frozen_policies():
    backend = Path(__file__).resolve().parents[1]
    ml = backend.parent / 'ucs31-madhaparia-ml'
    for name in ('v3_primary_selection.json', 'v3_primary_scope.json'):
        assert hashlib.sha256((backend / 'app/ml/artifacts' / name).read_bytes()).digest() == hashlib.sha256((ml / 'models' / name).read_bytes()).digest()
    def definitions(path):
        return {node.name: ast.dump(node, include_attributes=False)
                for node in ast.parse(path.read_text(encoding='utf-8-sig')).body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    assert definitions(backend / 'app/ml/primary_selection.py') == definitions(ml / 'inference/primary_selection.py')
    from app.ml.primary_selection import RESPIRATORY_ANCHOR_FEATURES
    assert RESPIRATORY_FEATURES == RESPIRATORY_ANCHOR_FEATURES


@pytest.mark.parametrize('text,persistent', [
    ('I feel tired', False),
    ('I have a cough and feel tired after work', False),
    ('I am tired all the time', True),
    ('I have constant tiredness', True),
    ('Nina uchovu kila wakati', True),
])
def test_generic_tiredness_does_not_claim_constant_fatigue(v3_flow, text, persistent):
    mapped = build_confirmation_output(text, v3_flow.db)
    tired = next(row for row in mapped['recognised_symptoms'] if row['code'] == 'tiredness')
    assert ('E_89' in tired['features']) is persistent


def test_everyday_muscle_ache_phrase_is_recognized(v3_flow):
    mapped = build_confirmation_output('My muscles ache all over my body.', v3_flow.db)
    aches = next(row for row in mapped['recognised_symptoms'] if row['code'] == 'muscle_aches')
    assert aches['status'] == 'present' and aches['features'] == ['E_144']


def test_actual_informative_primary_stops_questions_after_safety_and_context(v3_flow):
    from tests.test_kenya_patient_experience import assert_single_primary_contract
    data, answers, asked = finish(v3_flow, payload(v3_flow,
        'I have intense coughing fits and vomiting after coughing for 5 days.'))
    assert_single_primary_contract(data)
    assert data['status'] == 'prediction_complete'
    assert data['primary_prediction']['condition'] == 'Whooping cough'
    assert asked == ['breathing_difficulty']
    assert answers == [{'question_id': 'breathing_difficulty', 'answer': 'no'}]
    assert data['care_level'] == 'professional_review'


def test_missing_selection_policy_is_service_unavailable_not_a_patient_error(v3_flow, monkeypatch):
    import app.ml.primary_selection as selector
    def missing(*args, **kwargs):
        raise FileNotFoundError('Missing frozen decision policy')
    monkeypatch.setattr(selector, 'classify_primary', missing)
    body = payload(v3_flow, 'I have cough for two days but no difficulty breathing')
    response = v3_flow.client.post('/predict', json=body)
    assert response.status_code == 503
    assert v3_flow.saved == []


@pytest.mark.parametrize('version', ['v3_partial_evidence', '1.0'])
def test_fever_disclosed_during_infant_followup_stops_even_stale_trailing_replies(v3_flow, version):
    v3_flow.version.version = version
    body = payload(v3_flow, 'I feel tired', age=0)
    answers = []
    for _ in range(5):
        response = v3_flow.client.post('/predict', json={**body, 'follow_up_answers': answers})
        assert response.status_code == 200, response.text
        question = response.json()['follow_up_question']
        qid = question['id']
        values = {row['value'] for row in question['options']}
        if qid == 'fever':
            answers.append({'question_id': qid, 'answer': 'yes'})
            break
        answers.append({'question_id': qid, 'answer': 'no' if 'no' in values else 'unknown'})
    else:
        pytest.fail('Associated fever was not clarified')
    response = v3_flow.client.post('/predict', json={**body, 'follow_up_answers': answers + [
        {'question_id': 'cough', 'answer': 'no'}]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['status'] == 'urgent_review'
    assert result['primary_prediction'] is None and result['predictions'] == []
    assert result.get('follow_up_question') is None
    assert result['red_flag_symptoms'][0]['code'] == 'infant_fever'
    assert result['assessment_context']['follow_up_answers'] == answers
    assert 'baby' in result['health_guidance']
