"""Confirm positive suggestions without converting negation into evidence."""
from sqlalchemy.orm import Session
from app.nlp.symptom_mapper import build_confirmation_output, detect_safety_signs


def absent_features(symptoms):
    # A location-specific pain denial is not a denial of all pain. E_53
    # is shared by headache/chest pain; retain their location information.
    return list(dict.fromkeys(feature for item in symptoms
        for feature in item.get('features', [])
        if not (feature == 'E_53' and item['code'] in {'headache', 'chest_pain', 'forehead_pain', 'upper_chest_pain'})))


def confirm_symptoms(text: str, confirmed_codes: list[str], db: Session):
    mapping = build_confirmation_output(text, db)
    recognised = mapping['recognised_symptoms']
    present = {item['code']: item for item in recognised
               if item.get('status', 'present') == 'present'
               and item.get('reported_subject') != 'other_person'}
    if len(confirmed_codes) != len(set(confirmed_codes)):
        raise ValueError('Duplicate confirmed symptom codes are not allowed.')
    invalid = set(confirmed_codes) - present.keys()
    if invalid:
        raise ValueError('The following symptom codes were not recognised as present '
                         f'from the submitted text: {sorted(invalid)}')
    selected = set(confirmed_codes)
    updated = [dict(item, confirmed=item['code'] in selected) for item in recognised]
    confirmed = [item for item in updated if item['confirmed']]
    absent = [item for item in updated if item.get('status') == 'absent'
              and item.get('reported_subject') != 'other_person']
    red_flags = detect_safety_signs(text)
    red_flags += [item for item in confirmed if item.get('is_red_flag')
                  and item['code'] not in {flag['code'] for flag in red_flags}]
    return {
        **mapping, 'recognised_symptoms': updated, 'confirmed_symptoms': confirmed,
        'rejected_symptoms': [item for item in updated if item['code'] in present and not item['confirmed']],
        'absent_symptoms': absent,
        'uncertain_symptoms': [item for item in updated if item.get('status') == 'unknown'],
        'confirmed_codes': [item['code'] for item in confirmed],
        'model_features': list(dict.fromkeys(feature for item in confirmed for feature in item.get('features', []))),
        'explicitly_absent_features': absent_features(absent),
        'has_red_flag': bool(red_flags), 'red_flag_symptoms': red_flags,
        'safety_status': 'urgent_review' if red_flags else 'continue', 'requires_confirmation': False,
    }
