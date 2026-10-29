"""Regression inputs retained from the frozen 10k audit, not clinical cases."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.nlp.symptom_mapper import build_confirmation_output
from tests.test_v3_consultation import v3_flow

CRITICAL_CASES = json.loads((Path(__file__).resolve().parents[2] /
    'audit-artifacts/unique-10000-2026-10-29/critical-failures.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case', CRITICAL_CASES, ids=lambda c: str(c['case_id']))
def test_recorded_infant_fever_cases_bypass_mapping_and_questions(v3_flow, monkeypatch, case):
    import app.main as main
    def routine_mapping_must_not_run(*args, **kwargs):
        raise AssertionError('Infant fever must be detected before routine mapping')
    monkeypatch.setattr(main, 'confirm_symptoms', routine_mapping_must_not_run)
    response = v3_flow.client.post('/predict', json={
        'text': case['text'], 'age': case['age'], 'sex': case['sex'],
        'language': case['language'], 'confirmed_codes': [], 'follow_up_answers': []})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['status'] == 'urgent_review' and data['urgency'] == 'emergency'
    assert data['primary_prediction'] is None and data['predictions'] == []
    assert data['assessment_context']['follow_up_answers'] == []
    assert not data.get('follow_up_question')
    assert any(flag['code'] == 'infant_fever' for flag in data['red_flag_symptoms'])

    from app.services.primary_assessment import history_patient_projection
    old = SimpleNamespace(id='old-audit-case', age=case['age'], sex=case['sex'],
        input_text=case['text'], confirmed_codes=[], created_at=None, model_features=[],
        status='assessment_uncertain', has_red_flag=False,
        assessment_context={'language': case['language'], 'symptom_states': {'fever': 'absent'},
                            'patient_decision': {'policy_version': 'kenya_single_primary_v4_family_gathering'}})
    saved = history_patient_projection(old)
    assert saved['status'] == 'urgent_review' and saved['has_red_flag'] is True
    assert saved['urgency'] == 'emergency'
    assert saved['primary_prediction'] is None and saved['predictions'] == []


@pytest.mark.parametrize('text,code', [
    ('I have voice changes', 'hoarse_voice'),
    ('Nina sauti kukwaruza', 'hoarse_voice'),
    ('I have a whistling sound when breathing out', 'wheezing'),
    ('My eyes are itching', 'itchy_eyes'),
    ('I have a runny or blocked nose', 'runny_blocked_nose'),
    ('Nina mafua au pua imeziba', 'runny_blocked_nose'),
])
def test_audited_everyday_phrases_map_without_unmatched_wording(v3_flow, text, code):
    mapped = build_confirmation_output(text, v3_flow.db)
    assert not mapped['unmatched_wording']
    assert {s['code']: s['status'] for s in mapped['recognised_symptoms']} == {code: 'present'}
