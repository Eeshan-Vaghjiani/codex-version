import pytest
from nlp.symptom_mapper import build_confirmation_output


@pytest.mark.parametrize('text', ['i feel tired and have weaknes for 3 days',
    'I feel tired and have weakness for 3 days', 'Ninahisi uchovu na sina nguvu kwa siku tatu'])
def test_general_weakness_is_context_not_constant_fatigue_or_a_new_model_feature(text):
    result = build_confirmation_output(text)
    symptoms = {item['code']: item for item in result['recognised_symptoms']}
    assert set(symptoms) == {'weakness', 'tiredness'} and not result['unmatched_wording']
    assert all(item['features'] == [] and item['status'] == 'present' and item['duration_min_days'] == 3 for item in symptoms.values())
    assert symptoms['tiredness']['display_name'] == 'Tiredness'


@pytest.mark.parametrize('text', ['I do not have weakness', 'My brother feels weak'])
def test_weakness_negative_and_subject_are_preserved(text):
    result = build_confirmation_output(text)
    assert not [s for s in result['recognised_symptoms'] if s['status'] == 'present' and s['reported_subject'] != 'other_person']


@pytest.mark.parametrize('text,expected', [
    ('i feel cold, and my throat pains, and i have running nose', {'chills', 'sore_throat', 'runny_blocked_nose'}),
    ('I feel cold, my throat pains and I have running nose', {'chills', 'sore_throat', 'runny_blocked_nose'}),
    ('I have loss of taste', {'loss_of_taste'}),
])
def test_everyday_cold_and_taste_are_understood(text, expected):
    result = build_confirmation_output(text)
    assert {item['code'] for item in result['recognised_symptoms']} == expected
    assert not result['unmatched_wording']
