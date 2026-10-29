"""Everyday-language and bounded care-conversation regressions; not clinical validation."""
import pytest

from app.nlp.symptom_mapper import build_confirmation_output
from app.services.consultation import MAX_CONSULTATION_QUESTIONS
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
    for _ in range(21):
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
    pytest.fail('Conversation exceeded the hard question ceiling')


@pytest.mark.parametrize('text', ['i feel tired and have weaknes for 3 days',
                                 'Ninahisi uchovu na sina nguvu kwa siku tatu'])
def test_exact_example_gets_clarification_and_neutral_advice(v3_flow, text):
    data, asked = advance(v3_flow, payload(v3_flow, text), {
        'weakness_meaning': 'general_low_energy', 'symptom_severity': 'mild'})
    # Uncapped gathering asks the still-unknown respiratory discriminators
    # (breathing, sore throat, runny nose) after the non-specific questions,
    # so a "yes" can move the case into respiratory scope.
    assert asked == ['severe_chest_pain', 'fever', 'weakness_meaning', 'symptom_severity', 'cough',
                     'breathing_difficulty', 'sore_throat', 'runny_blocked_nose']
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
    # Uncapped gathering adds activity-fatigue and chills (answered no), which
    # shifts the clear top from Influenza to the same viral URI family (URTI).
    assert primary['condition'] == 'URTI'
    assert type(primary['model_match_percent']) is int and 60 <= primary['model_match_percent'] <= 100
    assert primary['score_kind'] == 'v3_relative_model_match'
    assert len(asked) <= MAX_CONSULTATION_QUESTIONS


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
    ('I have flu', ('flu-like', 'dalili kama mafua')),
    ('nina flu', ('flu-like', 'dalili kama mafua')),
])
def test_cold_and_flu_claims_get_actionable_guidance(v3_flow, text, keywords):
    data, asked = advance(v3_flow, payload(v3_flow, text), {
        'general_duration': 'under_3_days', 'symptom_severity': 'mild'})
    assert data['primary_prediction'] is None
    advice = ' '.join(data['next_steps']).lower()
    assert any(keyword in advice for keyword in keywords), (text, advice)
    assert 'mafua ya ndege' not in advice


def test_symptom_aware_guidance_for_withheld_sparse_case(v3_flow):
    """The exact user case: tiredness + headache + fever, under 3 days, moderate.
    Stays withheld (no name), but the guidance is tailored to what was reported."""
    data, asked = advance(v3_flow, payload(v3_flow, 'I have tiredness, headache and fever'), {
        'general_duration': 'under_3_days', 'symptom_severity': 'mild',
        'fatigue_pattern': 'transient'})
    assert data['primary_prediction'] is None and data['predictions'] == []
    advice = ' '.join(data['next_steps']).lower()
    assert 'stiff neck' in advice, advice          # headache + fever red-flag line
    assert 'unusual tiredness' in advice, advice   # tiredness line
    assert 'malaria' in advice, advice             # fever in Kenya line
    assert not any(word in advice for word in ('influenza', 'pneumonia', 'covid', 'bronchitis'))


def test_withheld_result_is_never_blank_and_offers_discriminators(v3_flow):
    """A withheld result must never be a blank screen: title + explanation +
    care guidance, plus discriminator questions for the symptoms still unknown.
    Uncapped gathering asks the respiratory discriminators itself, so the taps
    that remain are only the truly-unasked ones; breathing is still surfaced."""
    data, asked = advance(v3_flow, payload(v3_flow, 'I have tiredness, headache and fever'), {
        'general_duration': 'under_3_days', 'symptom_severity': 'mild',
        'fatigue_pattern': 'transient'})
    assert data['primary_prediction'] is None and data['status'] == 'assessment_uncertain'
    assert data['withheld_title']
    assert data['non_specific_explanation']
    assert data['next_steps']
    codes = [q['code'] for q in data['discriminator_questions']]
    # The flow asked the respiratory discriminators (breathing, sore throat,
    # runny nose) as part of gathering, so none are left to tap.
    assert codes == []
    assert 'breathing_difficulty' in asked and 'sore_throat' in asked and 'runny_blocked_nose' in asked


def test_non_respiratory_report_does_not_open_with_breathing(v3_flow):
    """A non-respiratory report is not opened with 'breathing': severe chest
    pain is asked first, and breathing is a later discriminator (a warning
    sign, still surfaced)."""
    data, asked = advance(v3_flow, payload(v3_flow, 'I feel dizzy'), {
        'general_duration': 'under_3_days'})
    assert asked[0] != 'breathing_difficulty', asked
    assert 'breathing_difficulty' in asked or any(
        q['code'] == 'shortness_of_breath' for q in data.get('discriminator_questions', [])), asked


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


@pytest.mark.parametrize('text', [
    'I have cough, sore throat, runny nose and headache',
    'I have a headache, sore throat, cough and runny nose for 2 days',
])
def test_common_cluster_gets_a_family_answer_not_a_diagnosis(v3_flow, text):
    data, asked = advance(v3_flow, payload(v3_flow, text), {'symptom_duration': 'under_3_days'})
    primary = data['primary_prediction']
    assert primary is not None
    assert primary['condition'] == 'Flu-like illness / common cold'
    assert primary['is_family_answer'] is True
    assert primary['score_kind'] == 'family_answer'
    # A family answer never claims a specific virus or carries a model match %.
    assert primary.get('model_match_percent') is None
    assert 'family_top_condition' not in primary
    assert data['status'] == 'prediction_complete'
    summary = data['assessment_summary'].lower()
    assert 'viral upper-respiratory' in summary
    # It is not a confirmed diagnosis: exactly one family answer, no disease list.
    assert [p['condition'] for p in data['predictions']] == ['Flu-like illness / common cold']

    # History must preserve the family snapshot, not look it up as a model class.
    from types import SimpleNamespace
    from app.services.primary_assessment import history_patient_projection
    session = SimpleNamespace(id='family-test', age=21, sex='M', input_text=text,
        confirmed_codes=data['confirmed_codes'], created_at=None, has_red_flag=False,
        status=data['status'], model_features=data['model_features'],
        assessment_context={**data['assessment_context'], 'patient_decision': data['decision'],
                            '_patient_primary': primary})
    saved = history_patient_projection(session)
    assert saved['primary_prediction'] == primary
    assert saved['predictions'] == [primary]


def test_family_answer_guidance_is_actionable_and_never_antibiotics(v3_flow):
    data, _ = advance(v3_flow, payload(v3_flow, 'I have cough, sore throat, runny nose and headache'),
                      {'symptom_duration': 'under_3_days'})
    advice = ' '.join(data['next_steps']).lower()
    # It explains antibiotics do not help a viral infection; it never advises them.
    assert 'antibiotics do not help' in advice
    assert 'paracetamol' in advice or 'fluids' in advice or 'rest' in advice
    # It only ever names the viral family as a possible cause, never a single diagnosis.
    assert 'pneumonia' not in advice and 'tuberculosis' not in advice


def test_sparse_serious_guard_never_names_serious_on_vague_input():
    from app.ml.primary_selection import sparse_serious_guard
    # Neoplasm on <=3 non-specific features is always withheld.
    assert sparse_serious_guard('Pulmonary neoplasm', {'E_97', 'E_181', 'E_53'}, 0.95, 0.4) is True
    # A specific supporting feature (coughing blood E_45) unlocks it.
    assert sparse_serious_guard('Pulmonary neoplasm', {'E_97', 'E_181', 'E_45'}, 0.95, 0.4) is False
    # Four present features are no longer sparse.
    assert sparse_serious_guard('Pulmonary neoplasm', {'E_97', 'E_181', 'E_53', 'E_201'}, 0.95, 0.4) is False
    # TB as a clear strong match on vague input is withheld; moderate is allowed.
    assert sparse_serious_guard('Tuberculosis', {'E_97', 'E_181', 'E_53'}, 0.85, 0.30) is True
    assert sparse_serious_guard('Tuberculosis', {'E_97', 'E_181', 'E_53'}, 0.70, 0.10) is False
