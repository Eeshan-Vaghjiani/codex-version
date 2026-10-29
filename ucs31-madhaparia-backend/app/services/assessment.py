"""Bounded follow-ups replayed against original evidence, never client profile.

Duration/severity inform guidance only; neither saved model learned them.
"""
import re
from copy import deepcopy
from sqlalchemy import select
from app.db.models import Symptom
from app.services.symptom_confirmation import absent_features

MAX_FOLLOW_UPS = 3
# Research-display guard, not a medically validated sufficiency cutoff.
MIN_RESEARCH_PRESENT_FEATURES = 3


def assessment_language(text, requested=None):
    if requested:
        return requested
    return 'sw' if re.search(r'\b(nina|sina|kikohozi|homa|kupumua|napumua|ninapumua|siwezi|nashindwa|ninashindwa|kifua|lakini)\b', text.lower()) else 'en'


QUESTIONS = {
    'breathing_difficulty': (
        'Are you having difficulty breathing now?', 'Je, una shida ya kupumua sasa?',
        [('yes', 'Yes', 'Ndiyo'), ('no', 'No', 'Hapana'), ('unknown', 'Not sure', 'Sina uhakika')],
        'Checks a warning sign before routine assessment.', 'Hukagua dalili ya hatari kabla ya tathmini ya kawaida.'),
    'symptom_duration': (
        'How long have you had the cough?', 'Umekuwa na kikohozi kwa muda gani?',
        [('under_3_days', 'Less than 3 days', 'Chini ya siku 3'),
         ('3_to_14_days', '3 to 14 days', 'Siku 3 hadi 14'),
         ('over_14_days', 'More than 14 days', 'Zaidi ya siku 14'),
         ('unknown', 'Not sure', 'Sina uhakika')],
        'Duration informs advice; it is not a trained model feature.',
        'Muda husaidia kutoa ushauri; modeli haijafunzwa kutumia muda huu.'),
    'fever': ('Do you have a fever?', 'Je, una homa?',
        [('yes', 'Yes', 'Ndiyo'), ('no', 'No', 'Hapana'), ('unknown', 'Not sure', 'Sina uhakika')],
        'Clarifies a missing or uncertain symptom.', 'Hufafanua dalili ambayo haijulikani.'),
    'cough': ('Do you have a cough?', 'Je, una kikohozi?',
        [('yes', 'Yes', 'Ndiyo'), ('no', 'No', 'Hapana'), ('unknown', 'Not sure', 'Sina uhakika')],
        'Clarifies a missing or uncertain symptom.', 'Hufafanua dalili ambayo haijulikani.'),
    'unexplained_weight_loss': ('Have you lost weight without trying?', 'Je, umepungua uzito bila kukusudia?',
        [('yes', 'Yes', 'Ndiyo'), ('no', 'No', 'Hapana'), ('unknown', 'Not sure', 'Sina uhakika')],
        'Clarifies an associated symptom when the cough has lasted weeks.',
        'Hufafanua dalili inayohusiana na kikohozi cha wiki kadhaa.'),
}
QUESTION_CODES = {'breathing_difficulty': 'shortness_of_breath', 'cough': 'cough',
                  'fever': 'fever', 'unexplained_weight_loss': 'weight_loss'}


def question_payload(question_id, language):
    en, sw, options, reason_en, reason_sw = QUESTIONS[question_id]
    is_sw = language == 'sw'
    return {'id': question_id, 'text': sw if is_sw else en,
            'options': [{'value': value, 'label': f'{index}. {sw_label if is_sw else label}'}
                        for index, (value, label, sw_label) in enumerate(options, 1)],
            'rationale': reason_sw if is_sw else reason_en}


def _next_question(states, duration, asked):
    present = {code for code, state in states.items() if state == 'present'}
    if not present or len(asked) >= MAX_FOLLOW_UPS:
        return None
    if states.get('shortness_of_breath', 'unmentioned') in {'unmentioned', 'unknown'} and 'breathing_difficulty' not in asked:
        return 'breathing_difficulty'
    if 'cough' in present and not duration and 'symptom_duration' not in asked:
        return 'symptom_duration'
    duration_text = str(duration.get('text', '')) if duration else ''
    prolonged = duration and ((duration.get('min_days') or 0) > 14 or
                              re.search(r'weeks|months|wiki|miezi', duration_text))
    if 'cough' in present and prolonged and states.get('weight_loss', 'unmentioned') in {'unmentioned', 'unknown'} and 'unexplained_weight_loss' not in asked:
        return 'unexplained_weight_loss'
    for question_id in ('cough', 'fever'):
        if states.get(question_id, 'unmentioned') in {'unmentioned', 'unknown'} and question_id not in asked:
            return question_id
    return None


def prepare_assessment(confirmation, answers, language, db, age=None):
    profile = deepcopy(confirmation)
    symptoms = profile.get('recognised_symptoms', profile.get('confirmed_symptoms', []))
    selected = set(profile['confirmed_codes'])
    states, details, duration = {}, {}, None
    duration_target = 'cough' if 'cough' in selected else next(iter(sorted(selected)), None)
    symptom_durations = {}
    for item in symptoms:
        if item.get('reported_subject') == 'other_person':
            continue
        code, state = item['code'], item.get('status', 'present')
        if state == 'present' and code not in selected:
            state = 'unmentioned'  # Rejected suggestion is not an explicit no.
        states[code], details[code] = state, item
        if state == 'present' and (item.get('duration_text') or item.get('duration_min_days') is not None):
            symptom_durations[code] = {'text': item.get('duration_text'), 'min_days': item.get('duration_min_days'),
                        'max_days': item.get('duration_max_days'), 'symptom_code': code}
            if code == duration_target:
                duration = symptom_durations[code]
    for code in selected:
        states.setdefault(code, 'present')
    asked, urgent, urgent_signs = [], False, []
    for response in answers:
        question_id = response['question_id']
        if question_id != _next_question(states, duration, asked) or urgent:
            raise ValueError('Follow-up answers must match the next question, without duplicates or skipped questions.')
        answer = response['answer']
        if answer not in {option[0] for option in QUESTIONS[question_id][2]}:
            raise ValueError(f'Invalid answer for follow-up question {question_id}.')
        asked.append(question_id)
        if question_id == 'symptom_duration':
            low, high = {'under_3_days': (0, 2), '3_to_14_days': (3, 14),
                         'over_14_days': (15, None), 'unknown': (None, None)}[answer]
            duration = {'text': answer, 'min_days': low, 'max_days': high, 'source': 'follow_up', 'symptom_code': 'cough'}
            symptom_durations['cough'] = duration
        else:
            code = QUESTION_CODES[question_id]
            states[code] = {'yes': 'present', 'no': 'absent', 'unknown': 'unknown'}[answer]
            row = db.scalar(select(Symptom).where(Symptom.code == code))
            if row is None:
                raise ValueError(f'Follow-up symptom is missing from the catalogue: {code}')
            details[code] = {'code': code, 'features': row.features,
                             'is_red_flag': row.is_red_flag, 'status': states[code]}
            if question_id == 'breathing_difficulty' and answer == 'yes':
                urgent = True
                urgent_signs = [details['shortness_of_breath']]
                break  # Accepted warning evidence takes priority over stale trailing answers.
            if question_id == 'fever' and answer == 'yes' and age == 0:
                from app.services.assessment_safety import detect_safety_signs
                urgent = True
                urgent_signs = detect_safety_signs('fever', age=0)
                break
    profile['confirmed_codes'] = [code for code, state in states.items() if state == 'present']
    profile['model_features'] = list(dict.fromkeys(feature for code, item in details.items()
        if states.get(code) == 'present' for feature in item.get('features', []))) or (profile['model_features'] if not details else [])
    profile['explicitly_absent_features'] = absent_features([
        item for code, item in details.items() if states.get(code) == 'absent'
    ])
    overlap = set(profile['model_features']) & set(profile['explicitly_absent_features'])
    if overlap:
        # Shared coarse evidence must not encode contradictory states.
        profile['explicitly_absent_features'] = [feature for feature in
            profile['explicitly_absent_features'] if feature not in overlap]
    profile['has_red_flag'] = profile.get('has_red_flag', False) or urgent
    if urgent:
        profile['red_flag_symptoms'] = urgent_signs
    next_id = None if profile['has_red_flag'] else _next_question(states, duration, asked)
    profile['follow_up_question'] = question_payload(next_id, language) if next_id else None
    profile['assessment_context'] = {
        'language': language, 'symptom_states': states, 'duration': duration,
        'symptom_durations': symptom_durations,
        'severity': {code: item['severity'] for code, item in details.items() if item.get('severity')},
        'follow_up_answers': answers[:len(asked)], 'questions_asked': asked,
        'context_note': ('Duration and severity are retained for guidance, not used by the model. '
            'V1 has no negative-evidence encoding; V2 has absence columns but was not trained on negative evidence. '
            'A no answer is recorded; it does not supply learned negative evidence to either saved model.'),
        'lossy_feature_note': 'Location-specific pain cannot be fully represented by the V2 model.' if any(code in states for code in ('headache', 'chest_pain')) else None}
    if language == 'sw':
        profile['assessment_context']['context_note'] = (
            'Muda na ukali wa dalili huhifadhiwa kwa ushauri; modeli hazitumii taarifa hizi. '
            'Modeli hizi hazijafunzwa kutumia ushahidi wa kutokuwepo kwa dalili. '
            'Jibu la hapana huhifadhiwa lakini halitoi ushahidi hasi uliofunzwa kwa modeli.')
    return profile
