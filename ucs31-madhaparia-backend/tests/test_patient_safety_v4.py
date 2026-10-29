"""Synthetic behaviour checks, not clinical reference cases or validation."""
import pytest

from app.services.assessment_safety import detect_safety_signs, safety_guidance
from app.services.consultation import next_consultation_question
from app.services.consultation_guidance import consultation_guidance
from app.services.primary_assessment import build_primary_assessment
from app.services.v3_prediction import predict_partial_evidence
from tests.test_v3_consultation import v3_flow, payload


def complete(flow, body):
    answers = []
    for _ in range(6):
        response = flow.client.post('/predict', json={**body, 'follow_up_answers': answers})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['predictions'] == ([] if data['primary_prediction'] is None else [data['primary_prediction']])
        assert len(data['predictions']) <= 1
        if data['status'] != 'needs_follow_up':
            return data, answers
        q = data['follow_up_question']
        answer = ('no' if q['id'] in {'breathing_difficulty', 'severe_chest_pain', 'fever'} else
                  'under_3_days' if q['id'] in {'general_duration', 'symptom_duration'} else 'unknown')
        answers.append({'question_id': q['id'], 'answer': answer})
    pytest.fail('More than five questions')


# All named results stay withheld while independent gap validation is missing.
JOURNEYS = [
    ('headache-fatigue', 'I have headache and fatigue', None, 24),
    ('cough', 'Nina kikohozi', None, 24),
    ('fever-cough-2d', 'I have fever na kikohozi for two days', None, 24),
    ('viral-2d', 'I have fever, cough and tiredness for two days', None, 24),
    ('prolonged-weight', 'I have cough for three weeks and unintentional weight loss', None, 24),
    ('cannot-breathe-en', "I can't breathe", 'emergency', 24),
    ('cannot-breathe-sw', 'Siwezi kupumua', 'emergency', 24),
    ('exertion', 'I have difficulty breathing when I walk, but I can speak fine', 'urgent_same_day', 24),
    ('difficulty-sw', 'Napumua kwa shida', 'urgent_same_day', 24),
    ('negative-breathing', 'I can breathe fine and have a cough', None, 24),
    ('smell', 'I have loss of smell', None, 24),
    ('smell-viral', 'I have loss of smell, cough and fever', None, 24),
    ('taste', 'I have loss of taste and fever', None, 24),
    ('chest-pain', 'I have severe chest pain', 'emergency', 24),
    ('fainting', 'I fainted', 'emergency', 24),
    ('blue-lips', 'My lips are turning blue', 'emergency', 24),
    ('blood', 'I am coughing a lot of blood', 'emergency', 24),
    ('confusion', 'I have confusion', 'emergency', 24),
    ('baby-fever', 'I have fever', 'emergency', 0),
    ('stiff-neck', 'I have headache, fever and stiff neck', 'emergency', 24),
    ('generic', 'I have fever, pain and fatigue', None, 24),
    ('severe-viral', 'I have severe fever, cough and body aches for two days', None, 24),
    ('overlap', 'I have cough, sore throat, fever and muscle aches', None, 24),
    ('sw-mixed', 'Nina homa na cough kwa siku mbili', None, 24),
]


@pytest.mark.parametrize('name,text,urgency,age', JOURNEYS, ids=[row[0] for row in JOURNEYS])
def test_required_api_journeys(v3_flow, name, text, urgency, age):
    data, answers = complete(v3_flow, payload(v3_flow, text, age=age))
    assert data['primary_prediction'] is None
    assert not data['predictions']
    assert 'COVID' not in str(data['primary_prediction'])
    assert 'disclaimer' in data
    if urgency:
        assert data['status'] == 'urgent_review'
        assert data['urgency'] == urgency
        assert not answers and data.get('follow_up_question') is None
        if urgency == 'emergency':
            assert data.get('safety_question') is None
    else:
        assert data['status'] in {'assessment_uncertain', 'insufficient_evidence'}
        assert ('nothing is ruled out' in data['uncertainty_message'] or
                'hakuna ugonjwa ulioondolewa' in data['uncertainty_message'])
        assert '24-48' in data['uncertainty_message']
        assert data['covid_scope_message']
        assert len(answers) <= 5


@pytest.mark.parametrize('text', ["I can't breathe", 'siwezi kupumua', 'gasping',
    'I cannot speak a full sentence', 'I have difficulty breathing at rest', 'nimeishiwa na pumzi'])
def test_extreme_breathing_never_asks_another_question(text):
    flags = detect_safety_signs(text)
    assert flags
    guidance = safety_guidance(flags)
    assert guidance['urgency'] == 'emergency'
    assert guidance['safety_question'] is None
    assert 'nearest hospital casualty' in guidance['health_guidance']


def test_one_breathing_check_and_no_downgrade_of_explicit_emergency(v3_flow):
    body = {'text': 'Napumua kwa shida'}
    first = v3_flow.client.post('/nlp/map', json=body).json()
    assert first['safety_question']['id'] == 'breathing_severity'
    for answer, urgency in [('at_rest_or_cannot_speak', 'emergency'),
                            ('exertion_full_sentence', 'urgent_same_day'), ('unknown', 'urgent_same_day')]:
        second = v3_flow.client.post('/nlp/map', json={**body, 'breathing_check': answer}).json()
        assert second['urgency'] == urgency and second['safety_question'] is None
    extreme = v3_flow.client.post('/nlp/map', json={
        'text': 'Siwezi kupumua', 'breathing_check': 'exertion_full_sentence'}).json()
    assert extreme['urgency'] == 'emergency'


@pytest.mark.parametrize('text', ['I can breathe fine', 'my brother has a cough', 'unmatched flibbertigibbet'])
def test_negatives_subject_and_unmatched_do_not_invent_present_symptoms(v3_flow, text):
    from app.nlp.symptom_mapper import build_confirmation_output
    result = build_confirmation_output(text, v3_flow.db)
    assert not detect_safety_signs(text)
    assert not [s for s in result['recognised_symptoms'] if s['status'] == 'present' and s['reported_subject'] != 'other_person']


@pytest.mark.parametrize('score,percent,band', [(.594, 59, 'low'), (.596, 60, 'moderate'), (.714, 71, 'moderate'), (.9675, 97, 'strong')])
def test_selected_v3_match_is_whole_percent_not_probability(monkeypatch, score, percent, band):
    import app.services.primary_assessment as service
    monkeypatch.setattr(service, 'select_primary_evidence', lambda *args: {
        'status': 'eligible', 'primary_prediction': {'condition': 'Bronchitis'},
        'diagnostics': {'source_relative_top_score': score}, 'reasons': []})
    result = build_primary_assessment({'model_features': ['E_201'],
        'assessment_context': {'language': 'en', 'symptom_states': {'cough': 'present'}}}, 24, 'F')
    primary = result['primary_prediction']
    assert primary['model_match_percent'] == percent and type(primary['model_match_percent']) is int
    assert primary['match_band'] == band
    assert primary['score_kind'] == 'v3_relative_model_match'
    assert 'chest infection' in primary['display_name'].lower()
    assert 'probability' not in primary and 'raw_relative_score' not in primary


def test_gap_withholds_even_when_bucket_score_passes_and_refers_dangerous_second(monkeypatch):
    import app.ml.primary_selection as selection
    monkeypatch.setattr(selection, 'load_gap_policy', lambda: {
        'minimum_relative_gap': .12, 'minimum_relative_score': .5, 'minimum_present_count': 2,
        'buckets': {'2:0': {'enabled': True}}})  # Hypothetical fixture, NOT a validated cutoff.
    monkeypatch.setattr(selection, 'load_primary_policy', lambda: {'buckets': {'2:0': {
        'enabled': True, 'minimum_relative_score': .50, 'reason': 'test-only'}}})
    monkeypatch.setattr(selection, 'load_primary_scope', lambda: {'disabled_buckets': {}})
    def ranked(second):
        return {'predictions': [dict(condition='Bronchitis', raw_relative_score=.52, supporting_features=['E_201'], supporting_absent_features=[]),
                               dict(condition=second, raw_relative_score=.48)]}
    monkeypatch.setattr(selection, 'predict_v3', lambda *args, **kwargs: ranked('Influenza'))
    decision = selection.classify_primary(['E_201', 'E_97'], [], 24, 'F')
    assert decision['primary_prediction'] is None and decision['reasons'] == ['close_model_rank']
    monkeypatch.setattr(selection, 'predict_v3', lambda *args, **kwargs: ranked('Pneumonia'))
    decision = selection.classify_primary(['E_201', 'E_97'], [], 24, 'F')
    assert 'dangerous_alternative_requires_review' in decision['reasons']
    from app.services.primary_assessment import patient_guidance
    guidance = patient_guidance({'_decision_reasons': decision['reasons']}, 24)
    assert guidance['care_level'] == 'urgent_review' and guidance['urgency'] == 'urgent_same_day'


def test_pending_gap_never_names_even_an_informative_pattern(monkeypatch):
    import app.ml.primary_selection as selection
    from app.ml.primary_selection import classify_primary
    monkeypatch.setattr(selection, 'load_gap_policy', lambda: None)
    decision = classify_primary(['E_203', 'E_166'], [], 24, 'F')
    assert decision['primary_prediction'] is None
    assert 'gap_validation_pending' in decision['reasons']


def test_two_unknown_answers_stop_and_safety_screen_is_first(v3_flow):
    body = payload(v3_flow, 'I have cough')
    answers = []
    for expected in ['breathing_difficulty', 'severe_chest_pain']:
        data = v3_flow.client.post('/predict', json={**body, 'follow_up_answers': answers}).json()
        assert data['follow_up_question']['id'] == expected
        answers.append({'question_id': expected, 'answer': 'unknown'})
    data = v3_flow.client.post('/predict', json={**body, 'follow_up_answers': answers}).json()
    assert data['status'] != 'needs_follow_up' and data.get('follow_up_question') is None
    assert all(value != 'absent' for value in data['assessment_context']['symptom_states'].values())


def test_no_change_to_advice_stops_even_with_high_information_gain(v3_flow, monkeypatch):
    import app.services.primary_assessment as primary
    import app.services.v3_prediction as model
    monkeypatch.setattr(primary, 'select_primary_evidence', lambda *args: {
        'status': 'uncertain', 'primary_prediction': None, 'reasons': [], 'diagnostics': {}})
    monkeypatch.setattr(model, 'rank_follow_up_features', lambda *args: [{'feature': 'E_144', 'information_gain': .9}])
    data = v3_flow.client.post('/predict', json=payload(v3_flow,
        'I have cough and fever for two days but no difficulty breathing', answers=[
            {'question_id': 'severe_chest_pain', 'answer': 'no'}])).json()
    assert data['status'] == 'assessment_uncertain'


def test_question_cap_is_five():
    assert next_consultation_question({'cough': 'present'}, {}, {}, ['a', 'b', 'c', 'd', 'e'], {}, 24, 'F') is None


@pytest.mark.parametrize('days', [2, 3, 14, 15, 21])
def test_duration_changes_advice_not_score(days):
    context = {'language': 'en', 'symptom_states': {'cough': 'present', 'fever': 'present'},
               'duration': {'min_days': days}}
    before = predict_partial_evidence(['E_201', 'E_91'], [], 24, 'F')
    advice = consultation_guidance(context, 24)
    after = predict_partial_evidence(['E_201', 'E_91'], [], 24, 'F')
    assert before == after
    assert advice['duration_advice']
    if days >= 14:
        assert 'TB, asthma, COPD' in advice['duration_advice']
        assert advice['care_level'] == 'professional_review'
    elif days <= 3:
        assert 'malaria test' in advice['duration_advice']


def test_terminology_and_covid_scope():
    from app.services.patient_terminology import patient_term, terminology
    assert 'chest infection' in patient_term('Bronchitis')['display_name'].lower()
    assert patient_term('Tuberculosis')['display_name'] == 'TB (tuberculosis)'
    assert patient_term('Pneumonia')['display_name'] == 'Lung infection (pneumonia)'
    assert patient_term('Influenza', 'sw')['display_name'] != 'mafua'
    assert 'bare' in terminology()['conditions']['Influenza']['terminology_note']
    assert 'COVID is not one' in terminology()['covid_scope_message']['en']
    assert 'pending' in terminology()['review_status']


def test_every_model_class_has_dual_simple_and_medical_name():
    # Dual naming is enforced for all 21 classes: simple name first, medical
    # name in parentheses, never one alone. No class is exempt.
    from app.services.patient_terminology import patient_term, terminology
    for condition in terminology()['conditions']:
        for language in ('en', 'sw'):
            term = patient_term(condition, language)
            display = term['display_name']
            assert display == term['dual_name']
            assert '(' in display and display.endswith(')')
            simple = display.rsplit(' (', 1)[0]
            assert simple == term['simple_name']
            assert term['medical_name'] and not simple.endswith(')')


@pytest.mark.parametrize('band,low,high', [('under_3_days', 0, 2), ('3_to_14_days', 3, 14), ('over_14_days', 15, None)])
def test_api_duration_bands_preserve_evidence_and_model_scores(v3_flow, band, low, high):
    body = payload(v3_flow, 'I have cough and fever but no difficulty breathing', answers=[
        {'question_id': 'severe_chest_pain', 'answer': 'no'},
        {'question_id': 'symptom_duration', 'answer': band}])
    response = v3_flow.client.post('/predict', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    duration = data['assessment_context']['duration']
    assert (duration['min_days'], duration['max_days']) == (low, high)
    assert set(data['model_features']) == {'E_201', 'E_91'}
    assert data['explicitly_absent_features'] == ['E_66']
    assert predict_partial_evidence(data['model_features'], data['explicitly_absent_features'], 21, 'M') == predict_partial_evidence(['E_201', 'E_91'], ['E_66'], 21, 'M')
    if band == 'over_14_days':
        assert data['follow_up_question']['id'] == 'weight_loss'


def test_dangerous_overlap_reaches_patient_without_naming(v3_flow, monkeypatch):
    import app.services.primary_assessment as primary
    monkeypatch.setattr(primary, 'select_primary_evidence', lambda *args: {
        'status': 'uncertain', 'primary_prediction': None, 'diagnostics': {},
        'reasons': ['close_model_rank', 'dangerous_alternative_requires_review']})
    data, answers = complete(v3_flow, payload(v3_flow, 'I have cough and fever for two days'))
    assert data['primary_prediction'] is None and data['predictions'] == []
    assert data['urgency'] == 'urgent_same_day'
    assert 'same-day' in data['health_guidance']


def test_live_model_identity_and_pending_gate_are_explicit(v3_flow):
    data = v3_flow.client.get('/model/status').json()
    assert data['model_version'] == 'v3_partial_evidence'
    assert (data['class_count'], data['feature_count']) == (21, 34)
    assert data['training_data'] == 'simulated DDXPlus only'
    assert data['clinical_validation'] is False and data['covid_in_scope'] is False
    from app.ml.primary_selection import load_gap_policy
    gate = load_gap_policy()
    assert data['patient_naming_enabled'] == bool(gate and any(row['enabled'] for row in gate['buckets'].values()))
    assert data['gap_validation'] == ('source_validation_checked' if gate else 'pending_fresh_fold')


@pytest.mark.parametrize('score', [True, None, float('nan'), float('inf'), -1, 1.01])
def test_invalid_selected_scores_fail_closed(monkeypatch, score):
    import app.services.primary_assessment as service
    from app.core.errors import ServiceNotReadyError
    monkeypatch.setattr(service, 'select_primary_evidence', lambda *args: {
        'status': 'eligible', 'primary_prediction': {'condition': 'Influenza'},
        'diagnostics': {'source_relative_top_score': score}, 'reasons': []})
    with pytest.raises(ServiceNotReadyError):
        build_primary_assessment({'model_features': ['E_201'], 'assessment_context': {}}, 24, 'F')


def test_saved_followup_breathing_urgency_does_not_escalate_or_restore_a_name():
    from types import SimpleNamespace
    import uuid
    from app.services.primary_assessment import history_patient_projection
    session = SimpleNamespace(id=uuid.uuid4(), age=24, sex='F', input_text='I have cough',
        confirmed_codes=['cough'], created_at=None, has_red_flag=True, status='urgent_review',
        assessment_context={'urgency': 'urgent_same_day'})
    result = history_patient_projection(session)
    assert result['urgency'] == 'urgent_same_day'
    assert result['primary_prediction'] is None and not result['predictions']
    assert result['safety_question'] is None
