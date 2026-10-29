"""Evidence-informed warning checks, independent of prediction and storage.

These limited software safeguards cannot rule out an emergency. See the linked
Kenya research report for clinical sources and remaining review requirements.
"""
import re
from app.nlp.symptom_mapper import (
    detect_safety_signs as respiratory_warning_signs,
    infer_repeated_symptom_context,
    normalize_text,
)


def _reported(text, aliases):
    normalized = normalize_text(text)
    for alias in aliases:
        if not re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', normalized):
            continue
        status, subject = infer_repeated_symptom_context(normalized, alias)
        if status != 'absent' and subject != 'other_person':
            return alias
    return None


def _flag(code, description, phrase):
    return {'code': code, 'display_name': description, 'features': [], 'kind': 'safety',
            'is_red_flag': True, 'matched_text': phrase, 'status': 'present',
            'reported_subject': 'patient_or_unspecified', 'confirmed': False}


def detect_safety_signs(text, age=None):
    flags = respiratory_warning_signs(text)
    headache = _reported(text, ('headache', 'head pain', 'kichwa kuuma', 'maumivu ya kichwa'))
    fever = _reported(text, ('fever', 'feverish', 'homa', 'high temperature'))
    neck = _reported(text, ('stiff neck', 'neck stiffness', 'shingo kukakamaa', 'shingo ngumu'))
    sudden = _reported(text, ('sudden severe headache', 'severe sudden headache', 'sudden worst headache', 'worst headache of my life',
                              'thunderclap headache', 'kichwa kuuma ghafla sana'))
    pressure = _reported(text, ('severe chest pain', 'crushing chest pain', 'severe chest pressure', 'crushing chest pressure',
                                'sudden severe chest pain', 'maumivu makali ya kifua', 'maumivu makali ya kifua ghafla'))
    if neck and (headache or fever):
        flags.append(_flag('headache_fever_stiff_neck', 'Headache or fever with neck stiffness', neck))
    if sudden:
        flags.append(_flag('sudden_severe_headache', 'Sudden unusually severe headache', sudden))
    if pressure:
        flags.append(_flag('severe_chest_pressure', 'Severe or crushing chest pressure', pressure))
    focal = _reported(text, ('sudden one-sided weakness', 'sudden weakness on one side',
        'sudden weakness in one arm', 'sudden weakness in one leg', 'face drooping',
        'my face is drooping', 'slurred speech', 'udhaifu wa ghafla upande mmoja', 'uso umepinda'))
    if focal:
        flags.append(_flag('sudden_neurological_change', 'Sudden weakness, facial or speech change', focal))
    # Integer age 0 cannot distinguish a newborn from an older infant. Do not
    # silently assume the child is over three months or delay clinical review.
    if age == 0 and fever:
        flags.append(_flag('infant_fever', 'Fever in a baby: prompt clinical assessment needed', fever))
    return list({item['code']: item for item in flags}.values())


def safety_guidance(flags, language='en', breathing_check=None):
    """Safety routing never depends on model scores, catalogue or database access."""
    from app.services.health_guidance import get_urgent_guidance
    sw = language == 'sw'
    tiers = [flag.get('breathing_tier', 'emergency') or 'emergency' for flag in flags]
    emergency = 'emergency' in tiers
    check = not emergency and 'severity_check' in tiers and breathing_check is None
    if not emergency and breathing_check == 'at_rest_or_cannot_speak':
        emergency = True
    urgency = 'emergency' if emergency else 'urgent_same_day'
    message = (
        'Tafuta matibabu mara moja. Nenda idara ya dharura (casualty) ya hospitali iliyo karibu. Usisubiri maswali au utabiri.' if sw else
        'Seek medical attention immediately. Go to the nearest hospital casualty / emergency department. Do not wait for questions or a prediction.'
    ) if emergency else (
        'Tafuta huduma ya matibabu leo. Ukipata shida ya kupumua ukiwa umepumzika au huwezi kusema sentensi kamili, nenda hospitali kwa dharura sasa.' if sw else
        'Seek urgent same-day care. If breathing is difficult at rest or you cannot speak a full sentence, go to hospital casualty immediately.')
    question = None
    if check:
        question = {
            'id': 'breathing_severity',
            'text': ('Shida ya kupumua ni ukiwa umepumzika au wakati wa kutembea tu, na unaweza kusema sentensi kamili?' if sw else
                     'Is breathing difficult at rest or only on exertion, and can you speak a full sentence?'),
            'options': [
                {'value': 'at_rest_or_cannot_speak', 'label': 'Ukiwa umepumzika / siwezi kusema sentensi kamili' if sw else 'At rest or cannot speak a full sentence'},
                {'value': 'exertion_full_sentence', 'label': 'Wakati wa kutembea tu; naweza kusema sentensi kamili' if sw else 'Only on exertion; can speak a full sentence'},
                {'value': 'unknown', 'label': 'Sina uhakika — tafuta huduma leo' if sw else 'Not sure — seek same-day care'},
            ],
        }
    return {**get_urgent_guidance(language), 'health_guidance': message,
            'urgency': urgency, 'care_level': 'urgent_review', 'safety_question': question}
