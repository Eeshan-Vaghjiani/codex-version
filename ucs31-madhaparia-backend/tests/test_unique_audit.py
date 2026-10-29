"""The audit harness must not inflate its case count or hide contract failures."""
from scripts.audit_unique_10000 import contract_errors, generate_cases


def test_generator_produces_ten_thousand_distinct_descriptions_reproducibly():
    cases = generate_cases()
    assert len(cases) == len({' '.join(c['text'].casefold().split()) for c in cases}) == 10000
    assert cases == generate_cases()
    assert len({c['category'] for c in cases}) == 8
    assert all(len(c['text']) < 2000 and type(c['age']) is int for c in cases)


def test_contract_checks_reject_a_family_score_and_an_urgent_name():
    primary = {'condition': 'Flu-like illness / common cold', 'is_family_answer': True,
               'model_match_percent': 95}
    errors = contract_errors({'status': 'urgent_review', 'clinical_validation': False,
        'health_guidance': 'Seek care', 'next_steps': ['Seek care'],
        'primary_prediction': primary, 'predictions': [primary]})
    assert {'urgent_named', 'family_leaks_specific_class_or_score'} <= set(errors)
    assert 'blank_guidance' in contract_errors({})


def test_urgent_contract_accepts_immediate_guidance_without_routine_next_steps():
    assert not contract_errors({'status': 'urgent_review', 'clinical_validation': False,
        'health_guidance': 'Seek emergency care now', 'primary_prediction': None,
        'predictions': []})


def test_unfamiliar_cases_are_new_unique_and_cover_each_novelty_group():
    from scripts.audit_unfamiliar import generate_unfamiliar
    original = {c['text'].casefold() for c in generate_cases()}
    cases = generate_unfamiliar()
    texts = {c['text'].casefold() for c in cases}
    assert len(cases) == len(texts) == 1000
    assert not texts & original
    assert len({c['novel_kind'] for c in cases}) == 5
    assert all(c['category'] == 'unsupported' and c['answers'] == 'all_no' for c in cases)
