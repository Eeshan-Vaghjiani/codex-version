"""Everyday-language and bounded care-conversation regressions; not clinical validation."""
import pytest

from app.nlp.symptom_mapper import build_confirmation_output
from tests.test_v3_consultation import v3_flow, payload


@pytest.mark.parametrize('text', [
    'i feel tired and have weaknes for 3 days',
    'I feel tired and have weakness for 3 days',
    'Ninahisi uchovu na sina nguvu kwa siku tatu',
    'Nina uchovu na weakness kwa siku tatu',
])
def test_weakness_and_tiredness_are_understood_without_invented_features(v3_flow, text):
    result = build_confirmation_output(text, v3_flow.db)
    symptoms = {item['code']: item for item in result['recognised_symptoms']}
    assert set(symptoms) == {'tiredness', 'weakness'}
    assert result['unmatched_wording'] == []
    for item in symptoms.values():
        assert item['status'] == 'present' and item['duration_min_days'] == 3
        assert item['features'] == []
    assert symptoms['tiredness']['display_name'] == 'Tiredness'


@pytest.mark.parametrize('text', ['I have no weakness', 'I am not feeling weak', 'My brother has weakness'])
def test_denied_or_other_person_weakness_is_not_patient_evidence(v3_flow, text):
    mapped = build_confirmation_output(text, v3_flow.db)
    assert not [item for item in mapped['recognised_symptoms'] if item['status'] == 'present' and item['reported_subject'] != 'other_person']


def advance(flow, body, choices):
    answers, asked = [], []
    for _ in range(6):
        response = flow.client.post('/predict', json={**body, 'follow_up_answers': answers})
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data['predictions']) <= 1
        if data['status'] != 'needs_follow_up':
            return data, asked
        question = data['follow_up_question']['id']
        asked.append(question)
        answer = choices.get(question, 'no')
        answers.append({'question_id': question, 'answer': answer})
    pytest.fail('Conversation exceeded five questions')


@pytest.mark.parametrize('text', ['i feel tired and have weaknes for 3 days',
                                 'Ninahisi uchovu na sina nguvu kwa siku tatu'])
def test_exact_example_gets_clarification_and_neutral_advice(v3_flow, text):
    data, asked = advance(v3_flow, payload(v3_flow, text), {
        'weakness_meaning': 'general_low_energy', 'symptom_severity': 'mild'})
    assert asked == ['breathing_difficulty', 'severe_chest_pain', 'fever', 'weakness_meaning', 'symptom_severity']
    assert data['primary_prediction'] is None and data['predictions'] == []
    assert not data['model_features']
    assert data['assessment_context']['duration']['min_days'] == 3
    assert data['assessment_context']['weakness_meaning'] == 'general_low_energy'
    assert data['assessment_context']['symptom_labels']['weakness']
    advice = ' '.join(data['next_steps']).lower()
    assert not any(word in advice for word in ('influenza', 'pneumonia', 'covid', 'bronchitis', 'malaria'))
    assert '24-48' in data['uncertainty_message']


@pytest.mark.parametrize('answer,expected', [('sudden_one_sided', 'urgent_review'),
                                           ('other_weakness', 'assessment_uncertain'), ('unknown', 'assessment_uncertain')])
def test_weakness_clarification_changes_care_not_disease_score(v3_flow, answer, expected):
    data, asked = advance(v3_flow, payload(v3_flow, 'I feel weak for three days'), {'weakness_meaning': answer})
    assert data['status'] == expected and data['primary_prediction'] is None
    assert asked[-1] == 'weakness_meaning' and len(asked) <= 5
    if answer == 'sudden_one_sided':
        assert data['urgency'] == 'emergency' and data.get('safety_question') is None
    else:
        assert data['care_level'] == 'professional_review'
        assert 'do not wait 24-48' in data['uncertainty_message']


@pytest.mark.parametrize('text', ['I have sudden one-sided weakness', 'My face is drooping',
    'I have slurred speech', 'Nina udhaifu wa ghafla upande mmoja'])
def test_reported_focal_warning_never_enters_model_questions(v3_flow, monkeypatch, text):
    import app.main as main
    def forbidden(*args, **kwargs):
        raise AssertionError('Danger sign must precede routine model/catalogue access')
    monkeypatch.setattr(main, 'get_active_model_version', forbidden)
    monkeypatch.setattr(main, 'confirm_symptoms', forbidden)
    result = v3_flow.client.post('/predict', json={'text': text, 'age': 24, 'sex': 'F', 'confirmed_codes': []})
    assert result.status_code == 200
    data = result.json()
    assert data['urgency'] == 'emergency' and data['primary_prediction'] is None
    assert data.get('follow_up_question') is None


def test_unknown_wording_cannot_erase_dangerous_alternative_review(v3_flow, monkeypatch):
    import app.services.primary_assessment as service
    monkeypatch.setattr(service, 'select_primary_evidence', lambda *args: {
        'status': 'uncertain', 'primary_prediction': None, 'diagnostics': {},
        'reasons': ['dangerous_alternative_requires_review']})
    result = service.build_primary_assessment({'model_features': ['E_201'], 'unmatched_wording': ['rash'],
        'assessment_context': {'symptom_states': {'cough': 'present'}}}, 24, 'F')
    assert result['urgency'] == 'urgent_same_day' and result['primary_prediction'] is None
    assert 'unsupported_information' in result['decision']['reasons']


def test_richer_supported_pattern_can_show_one_honest_match(v3_flow):
    text = 'I have fever, cough, sore throat, muscle aches, constant tiredness and runny nose for two days'
    data, asked = advance(v3_flow, payload(v3_flow, text), {})
    assert data['status'] == 'prediction_complete'
    assert data['predictions'] == [data['primary_prediction']]
    primary = data['primary_prediction']
    assert primary['condition'] == 'Influenza'
    assert type(primary['model_match_percent']) is int and 60 <= primary['model_match_percent'] <= 100
    assert primary['score_kind'] == 'v3_relative_model_match'
    assert len(asked) <= 5


@pytest.mark.parametrize('text', ['i feel cold, and my throat pains, and i have running nose',
    'I feel cold, my throat pains and I have running nose'])
def test_common_cold_pattern_is_understood_without_unmatched(v3_flow, text):
    mapped = build_confirmation_output(text, v3_flow.db)
    codes = {item['code'] for item in mapped['recognised_symptoms']}
    assert {'chills', 'sore_throat', 'runny_blocked_nose'} <= codes
    assert mapped['unmatched_wording'] == []


def test_common_cold_gets_actionable_guidance_not_a_respiratory_disease_list(v3_flow):
    text = 'i feel cold, and my throat pains, and i have running nose'
    data, asked = advance(v3_flow, payload(v3_flow, text), {
        'general_duration': 'under_3_days', 'symptom_severity': 'mild'})
    assert data['primary_prediction'] is None and data['predictions'] == []
    states = data['assessment_context']['symptom_states']
    assert states.get('chills') == 'present' and states.get('sore_throat') == 'present'
    assert states.get('runny_blocked_nose') == 'present'
    advice = ' '.join(data['next_steps']).lower()
    assert 'viral cold' in advice and 'covid' in advice
    assert not any(word in advice for word in ('pneumonia', 'tuberculosis', 'bronchitis', 'whooping cough'))
    assert 'viral cold' in data['assessment_summary'].lower()


def test_loss_of_taste_is_recognised_and_points_to_covid_testing(v3_flow):
    mapped = build_confirmation_output('I have loss of taste', v3_flow.db)
    assert any(item['code'] == 'loss_of_taste' and item['status'] == 'present'
               for item in mapped['recognised_symptoms'])
    assert mapped['unmatched_wording'] == []


def test_cold_or_flu_claim_is_context_not_model_evidence(v3_flow):
    for text in ('I have a cold', 'niko na cold', 'I have flu', 'nina flu'):
        mapped = build_confirmation_output(text, v3_flow.db)
        assert not mapped['unmatched_wording'], (text, mapped['unmatched_wording'])
        assert all(item['features'] == [] for item in mapped['recognised_symptoms'])


@pytest.mark.parametrize('text,keywords', [
    ('I have a cold', ('viral cold', 'mafua ya virusi')),
    ('niko na cold', ('viral cold', 'mafua ya virusi')),
    ('I have flu', ('flu-like', 'mafua ya ndege')),
    ('nina flu', ('flu-like', 'mafua ya ndege')),
])
def test_cold_and_flu_claims_get_actionable_guidance(v3_flow, text, keywords):
    data, asked = advance(v3_flow, payload(v3_flow, text), {
        'general_duration': 'under_3_days', 'symptom_severity': 'mild'})
    assert data['primary_prediction'] is None
    advice = ' '.join(data['next_steps']).lower()
    assert any(keyword in advice for keyword in keywords), (text, advice)


def test_unresolved_safety_does_not_name_even_an_eligible_pattern(monkeypatch):
    import app.services.primary_assessment as service
    monkeypatch.setattr(service, 'select_primary_evidence', lambda *args: {
        'status': 'eligible', 'primary_prediction': {'condition': 'Influenza'},
        'diagnostics': {'source_relative_top_score': .99}, 'reasons': []})
    result = service.build_primary_assessment({'model_features': ['E_201'], 'assessment_context': {
        'symptom_states': {'cough': 'present'}, 'follow_up_answers': [
            {'question_id': 'breathing_difficulty', 'answer': 'unknown'},
            {'question_id': 'severe_chest_pain', 'answer': 'unknown'}]}}, 24, 'F')
    assert result['primary_prediction'] is None
    assert {'safety_screen_incomplete', 'answers_remain_uncertain'} <= set(result['decision']['reasons'])
