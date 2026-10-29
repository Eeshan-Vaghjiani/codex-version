"""Expanded question pool contracts; software checks, not clinical validation."""
from sqlalchemy import select

from app.db.models import Symptom
from app.services.consultation import POOL, consultation_question
from app.services.v3_prediction import get_v3_bundle
from tests.test_v3_consultation import v3_flow, payload


def test_expanded_pool_uses_only_catalogued_trained_features(v3_flow):
    catalogue = {row.code: row for row in v3_flow.db.scalars(select(Symptom)).all()}
    supported = set(get_v3_bundle()['features'])
    assert len(POOL) == len(set(POOL)) == 24
    for code in POOL:
        assert catalogue[code].features
        assert set(catalogue[code].features) <= supported
        for language in ('en', 'sw'):
            question = consultation_question(code, language)
            assert question['text'] and question['rationale']
            assert {option['value'] for option in question['options']} == {'yes', 'no', 'unknown'}


def test_night_breathlessness_answer_stops_before_stale_trailing_answers(v3_flow, monkeypatch):
    import app.services.consultation as service
    # Isolate the newly added warning-sign answer from model question ranking.
    monkeypatch.setattr(service, 'next_consultation_question', lambda *args: 'night_breathlessness')
    body = payload(v3_flow, 'I have cough for two days', answers=[
        {'question_id': 'night_breathlessness', 'answer': 'yes'},
        {'question_id': 'fever', 'answer': 'no'},
    ])
    response = v3_flow.client.post('/predict', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['status'] == 'urgent_review'
    assert data['primary_prediction'] is None and data['predictions'] == []
    assert data['assessment_context']['follow_up_answers'] == body['follow_up_answers'][:1]
    assert not data.get('follow_up_question')
