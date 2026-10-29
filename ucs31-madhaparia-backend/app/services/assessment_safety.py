"""Evidence-informed warning checks, independent of prediction and storage.

These limited software safeguards cannot rule out an emergency. See the linked
Kenya research report for clinical sources and remaining review requirements.
"""
import re
from app.nlp.breathing_tier import classify_breathing_tier
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
    tier = classify_breathing_tier(text)
    if tier:
        for flag in flags:
            if flag.get("code") == "shortness_of_breath":
                flag["breathing_tier"] = tier
    headache = _reported(text, ('headache', 'head pain', 'kichwa kuuma', 'maumivu ya kichwa'))
    fever = _reported(text, ('fever', 'feverish', 'homa', 'high temperature'))
    neck = _reported(text, ('stiff neck', 'neck stiffness', 'shingo kukakamaa', 'shingo ngumu'))
    sudden = _reported(text, ('sudden severe headache', 'severe sudden headache', 'sudden worst headache', 'worst headache of my life',
                              'thunderclap headache', 'kichwa kuuma ghafla sana'))
    pressure = _reported(text, ('crushing chest pain', 'severe chest pain', 'severe chest pressure', 'crushing chest pressure',
                                'sudden severe chest pain', 'maumivu makali ya kifua ghafla'))
    if neck and (headache or fever):
        flags.append(_flag('headache_fever_stiff_neck', 'Headache or fever with neck stiffness', neck))
    if sudden:
        flags.append(_flag('sudden_severe_headache', 'Sudden unusually severe headache', sudden))
    if pressure:
        flags.append(_flag('severe_chest_pressure', 'Severe or crushing chest pressure', pressure))
    # Integer age 0 cannot distinguish a newborn from an older infant. Do not
    # silently assume the child is over three months or delay clinical review.
    if age == 0 and fever:
        flags.append(_flag('infant_fever', 'Fever in a baby: prompt clinical assessment needed', fever))
    return list({item['code']: item for item in flags}.values())
