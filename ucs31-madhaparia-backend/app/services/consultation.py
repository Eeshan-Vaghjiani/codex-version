"""Research consultation using a model trained for partially observed evidence.

Questions collect usable evidence; they do not simulate a physical examination.
Duration and onset guide safety/advice, not disease likelihoods unsupported by data.
"""
from copy import deepcopy
import re
from sqlalchemy import select
from app.db.models import Symptom
from app.services.assessment import QUESTIONS as LEGACY_QUESTIONS, question_payload
from app.services.symptom_confirmation import absent_features

V3_MODEL_VERSION = 'v3_partial_evidence'
# Symptom gathering is NOT capped at a small number for accuracy's sake
# (authorised 2026-10-29): 5 is now a soft guide, not a cutoff. The hard
# ceiling (20) exists only to prevent an endless loop; in practice the
# information-gain stop, the eligible stop, the 2x unknown stop and the
# red-flag stop end the consultation much earlier. A case that was
# withheld for too little information may therefore ask for the missing
# discriminators and then resolve, instead of stopping at 5 and withholding.
SOFT_QUESTION_GUIDE = 5
MAX_CONSULTATION_QUESTIONS = 20
# Engineering stop policy selected on validation question rollouts; this is
# expected entropy utility in nats, never a clinical certainty threshold.
MIN_QUESTION_INFORMATION_GAIN = 0.02
MAX_UNKNOWN_ANSWERS = 2  # Checklist stop: 'I don't know' twice ends follow-ups.

# Wording tracks the actual evidence definition, including qualified sputum.
CONSULTATION_QUESTIONS = {
    **LEGACY_QUESTIONS,
    'runny_blocked_nose': ('Is your nose runny or blocked?', 'Je, una mafua au pua imeziba?'),
    'sore_throat': ('Is your throat sore?', 'Je, koo lako linauma?'),
    'muscle_aches': ('Do your muscles ache across your body?', 'Je, una maumivu ya misuli mwili mzima?'),
    'wheezing': ('Do you hear a whistling sound when breathing out?', 'Je, unasikia sauti ya mluzi unapotoa pumzi?'),
    'productive_cough': ('Are you coughing up coloured phlegm, or more phlegm than usual?',
                         'Je, unakohoa makohozi yenye rangi, au mengi kuliko kawaida?'),
    'heavy_sweating': ('Are you sweating much more than usual, including at night?',
                       'Je, unatoka jasho jingi kuliko kawaida, hasa usiku?'),
    'weight_loss': ('Have you lost weight without trying?', 'Je, umepungua uzito bila kukusudia?'),
    'weight_loss_intent': ('Was the weight loss unintentional?', 'Je, ulipungua uzito bila kukusudia?'),
    'general_duration': ('How long have you had these symptoms?', 'Umekuwa na dalili hizi kwa muda gani?'),
    'symptom_severity': ('How much are these symptoms affecting your usual activities?', 'Dalili hizi zinaathiri shughuli zako za kawaida kwa kiasi gani?'),
    'fatigue_pattern': ('Is the tiredness constant, or do you wake feeling unrefreshed?', 'Je, uchovu ni wa kila wakati, au unaamka bila kujisikia umepumzika?'),
    # Expanded discriminator pool: every code below already exists in the
    # repo symptom catalogue with a trained V3 feature. No new disease,
    # code or feature is invented here; these are questions the system
    # already knows how to use, now actually asked when they would help.
    'chills': ('Do you have chills or shivering?', 'Je, unatetemeka au unahisi baridi kali?'),
    'intense_coughing_fits': ('Do you have intense coughing fits that you cannot stop?', 'Je, unakohoa kwa mashambulizi makali ambayo huwezi kuyazuia?'),
    'vomiting_after_coughing': ('Do you vomit after coughing?', 'Je, unatapika baada ya kukohoa?'),
    'night_breathlessness': ('Do you wake up at night breathless or choking?', 'Je, unaamka usiku ukikosa pumzi au ukibanwa?'),
    'wheeze_after_coughing': ('Do you wheeze or breathe noisily after coughing?', 'Je, unapumua kwa mluzi baada ya kukohoa?'),
    'difficulty_swallowing': ('Do you have difficulty swallowing?', 'Je, una shida ya kumeza?'),
    'hoarse_voice': ('Is your voice hoarse or changed?', 'Je, sauti yako imekauka au imebadilika?'),
    'nasal_discharge': ('Do you have green or yellow discharge from your nose?', 'Je, una kamasi za kijani au za manjano kutoka puani?'),
    'loss_of_smell': ('Have you lost your sense of smell?', 'Je, umepoteza uwezo wa kunusa?'),
    'itchy_nose_throat': ('Is your nose or throat itchy?', 'Je, pua au koo lako linawasha?'),
    'itchy_eyes': ('Are your eyes itchy?', 'Je, macho yako yanawasha?'),
    # Chest pain and pain on deep breathing are deliberately NOT in the
    # routine pool: a "yes" to either needs clinical assessment, not a
    # model-guided question, and they remain mappable from free text.
    'worse_lying_down': ('Are your symptoms worse when you lie down?', 'Je, dalili zako zinazidi unapolala chini?'),
    'worse_with_exertion': ('Are your symptoms worse with exertion or activity?', 'Je, dalili zako zinazidi unapofanya shughuli?'),
    'activity_fatigue': ('Are you too tired for your usual activities?', 'Je, umechoka sana kufanya shughuli zako za kawaida?'),
    'loss_of_appetite': ('Have you lost your appetite?', 'Je, umepoteza hamu ya kula?'),
}
POOL = ('runny_blocked_nose', 'sore_throat', 'muscle_aches', 'wheezing',
        'productive_cough', 'heavy_sweating', 'weight_loss', 'cough', 'fever',
        'chills', 'intense_coughing_fits', 'vomiting_after_coughing',
        'night_breathlessness', 'wheeze_after_coughing', 'difficulty_swallowing',
        'hoarse_voice', 'nasal_discharge', 'loss_of_smell', 'itchy_nose_throat',
        'itchy_eyes', 'worse_lying_down',
        'worse_with_exertion', 'activity_fatigue', 'loss_of_appetite')
QUESTION_TO_CODE = {'breathing_difficulty': 'shortness_of_breath', 'unexplained_weight_loss': 'weight_loss'}
YES_NO = [('yes', 'Yes', 'Ndiyo'), ('no', 'No', 'Hapana'), ('unknown', 'Not sure', 'Sina uhakika')]


def consultation_question(question_id, language):
    if question_id in LEGACY_QUESTIONS and question_id != 'unexplained_weight_loss':
        result = question_payload(question_id, language)
    else:
        en, sw = CONSULTATION_QUESTIONS[question_id][:2]
        options = ( [('unintentional', 'Without trying to lose weight', 'Bila kukusudia'),
                     ('intentional', 'I was trying to lose weight', 'Nilikuwa nikijaribu kupunguza uzito'),
                     ('unknown', 'Not sure', 'Sina uhakika')]
                    if question_id == 'weight_loss_intent' else YES_NO )
        if question_id == 'general_duration':
            options = [('under_3_days', 'Less than 3 days', 'Chini ya siku 3'),
                       ('3_to_14_days', '3 to 14 days', 'Siku 3 hadi 14'),
                       ('over_14_days', 'More than 14 days', 'Zaidi ya siku 14'),
                       ('unknown', 'Not sure', 'Sina uhakika')]
        elif question_id == 'symptom_severity':
            options = [('mild', 'Mild: usual activities possible', 'Kidogo: naweza kufanya shughuli za kawaida'),
                       ('moderate', 'Moderate: some activities affected', 'Wastani: baadhi ya shughuli zimeathirika'),
                       ('severe', 'Severe: unable to do usual activities', 'Kali: siwezi kufanya shughuli za kawaida'),
                       ('unknown', 'Not sure', 'Sina uhakika')]
        elif question_id == 'fatigue_pattern':
            options = [('persistent', 'Tired constantly', 'Uchovu wa kila wakati'),
                       ('unrefreshing', 'Sleep does not feel refreshing', 'Usingizi haunipumzishi'),
                       ('transient', 'Temporary tiredness', 'Uchovu wa muda mfupi'),
                       ('unknown', 'Not sure', 'Sina uhakika')]
        result = {
            'id': question_id, 'text': sw if language == 'sw' else en,
            'options': [{'value': value, 'label': f'{i}. {sw_label if language == "sw" else label}'}
                        for i, (value, label, sw_label) in enumerate(options, 1)],
        }
    result['rationale'] = (
        'Jibu hili husaidia kutofautisha hali zinazowezekana; si uchunguzi wa daktari.'
        if language == 'sw' else
        'This answer can help distinguish the possible patterns; it does not replace an examination.'
    )
    if question_id in {'symptom_duration', 'general_duration'}:
        result['rationale'] = ('Muda husaidia kuchagua maswali na ushauri; haujafunzwa kama kipengele cha modeli.'
                               if language == 'sw' else
                               'Duration guides questions and advice; it is not a trained disease-model feature.')
    return result


def _features(states, details):
    present = list(dict.fromkeys(feature for code, item in details.items()
        if states.get(code) == 'present' for feature in item.get('features', [])))
    absent = absent_features([item for code, item in details.items() if states.get(code) == 'absent'])
    # Qualified symptom denial must not contradict a separate generic positive.
    return present, [feature for feature in absent if feature not in present]


def _prolonged(duration):
    if not duration:
        return False
    if duration.get('min_days') is not None:
        return duration['min_days'] >= 14
    return bool(re.search(r'weeks|months|wiki|miezi', str(duration.get('text', '')), re.I))


def next_consultation_question(states, details, durations, asked, catalogue, age, sex):
    if len(asked) >= MAX_CONSULTATION_QUESTIONS:
        return None
    reported = {code for code, state in states.items() if state == 'present'}
    if not reported:
        return None
    from app.services.primary_assessment import has_respiratory_scope
    present_features, _ = _features(states, details)
    severe = any(item.get('severity') == 'severe' for item in details.values())
    if not has_respiratory_scope(present_features):
        if severe:
            return None
        known_durations = [value for key, value in durations.items() if key != '_general']
        if not known_durations and not durations.get('_general') and 'general_duration' not in asked:
            return 'general_duration'
        if 'headache' in reported and not details.get('headache', {}).get('severity') and 'symptom_severity' not in asked:
            return 'symptom_severity'
        if states.get('fever', 'unmentioned') in {'unknown', 'unmentioned'} and 'fever' not in asked:
            return 'fever'
        if states.get('cough', 'unmentioned') in {'unknown', 'unmentioned'} and 'cough' not in asked:
            return 'cough'
        return None
    # Safety always precedes model-guided questions for respiratory reports.
    if states.get('shortness_of_breath', 'unmentioned') in {'unknown', 'unmentioned'} and 'breathing_difficulty' not in asked:
        return 'breathing_difficulty'
    if severe:
        return None
    if 'tiredness' in reported and details.get('tiredness', {}).get('fatigue_pattern') == 'unspecified' and 'fatigue_pattern' not in asked:
        return 'fatigue_pattern'
    if 'cough' in reported and not durations.get('cough') and 'symptom_duration' not in asked:
        return 'symptom_duration'
    if states.get('weight_loss') == 'present' and details.get('weight_loss', {}).get('weight_loss_intent') == 'unspecified' and 'weight_loss_intent' not in asked:
        return 'weight_loss_intent'
    if 'cough' in reported and _prolonged(durations.get('cough')) and states.get('weight_loss', 'unmentioned') in {'unknown', 'unmentioned'} and 'weight_loss' not in asked and 'weight_loss_intent' not in asked:
        return 'weight_loss'
    present, absent = _features(states, details)
    from app.services.primary_assessment import select_primary_evidence
    if select_primary_evidence(present, absent, age, sex)['status'] == 'eligible':
        return None
    available = {}
    for code in POOL:
        if code in asked or states.get(code, 'unmentioned') not in {'unknown', 'unmentioned'}:
            continue
        # Sputum qualification is meaningful only when a cough was reported.
        if code == 'productive_cough' and 'cough' not in reported:
            continue
        if code == 'weight_loss' and ('weight_loss_intent' in asked or not _prolonged(durations.get('cough'))):
            continue
        row = catalogue.get(code)
        if row:
            for feature in row.features:
                available.setdefault(feature, code)
    if not available:
        return None
    from app.services.v3_prediction import rank_follow_up_features
    ranked = rank_follow_up_features(present, absent, age, sex, list(available))
    # Stop when another model question has little expected benefit.
    for item in ranked:
        feature = item['feature']
        if item['information_gain'] >= MIN_QUESTION_INFORMATION_GAIN and feature in available:
            return available[feature]
    return None


def prepare_consultation(confirmation, answers, language, db, age, sex):
    profile = deepcopy(confirmation)
    catalogue = {row.code: row for row in db.scalars(select(Symptom)).all()}
    states, details, durations, asked = {}, {}, {}, []
    selected = set(profile['confirmed_codes'])
    for item in profile.get('recognised_symptoms', []):
        if item.get('reported_subject') == 'other_person':
            continue
        code, state = item['code'], item.get('status', 'present')
        if state == 'present' and code not in selected:
            state = 'unmentioned'
        states[code], details[code] = state, item
        if state == 'present' and (item.get('duration_text') or item.get('duration_min_days') is not None):
            durations[code] = {'text': item.get('duration_text'), 'min_days': item.get('duration_min_days'),
                               'max_days': item.get('duration_max_days'), 'symptom_code': code}
    for response in answers:
        question_id = response['question_id']
        expected = next_consultation_question(states, details, durations, asked, catalogue, age, sex)
        if question_id != expected:
            raise ValueError('Follow-up answers must match the next question without duplicates or skipped questions.')
        payload = consultation_question(question_id, language)
        answer = response['answer']
        if answer not in {item['value'] for item in payload['options']}:
            raise ValueError(f'Invalid answer for follow-up question {question_id}.')
        asked.append(question_id)
        if question_id in {'symptom_duration', 'general_duration'}:
            low, high = {'under_3_days': (0, 2), '3_to_14_days': (3, 14),
                         'over_14_days': (15, None), 'unknown': (None, None)}[answer]
            duration_code = 'cough' if question_id == 'symptom_duration' else '_general'
            durations[duration_code] = {'text': answer, 'min_days': low, 'max_days': high,
                                      'source': 'follow_up', 'symptom_code': duration_code}
        elif question_id == 'symptom_severity':
            target = 'headache' if states.get('headache') == 'present' else next((c for c in details if states.get(c) == 'present'), None)
            if target and answer != 'unknown':
                details[target]['severity'] = answer
        elif question_id == 'fatigue_pattern':
            details['tiredness']['fatigue_pattern'] = answer
            details['tiredness']['features'] = catalogue['tiredness'].features if answer in {'persistent', 'unrefreshing'} else []
        else:
            code = QUESTION_TO_CODE.get(question_id, question_id)
            if question_id == 'weight_loss_intent':
                code = 'weight_loss'
                states[code] = 'present' if answer == 'unintentional' else 'unknown'
                details[code]['weight_loss_intent'] = answer
                details[code]['features'] = catalogue[code].features if answer == 'unintentional' else []
            else:
                row = catalogue.get(code)
                if row is None:
                    raise ValueError(f'Follow-up symptom is missing from the catalogue: {code}')
                states[code] = {'yes': 'present', 'no': 'absent', 'unknown': 'unknown'}[answer]
                details[code] = {'code': code, 'display_name': row.display_name,
                    'features': row.features, 'status': states[code], 'source': 'follow_up'}
            if question_id == 'breathing_difficulty' and answer == 'yes':
                profile['has_red_flag'] = True
                profile['red_flag_symptoms'] = [details['shortness_of_breath']]
                break
            if question_id == 'night_breathlessness' and answer == 'yes':
                # Waking breathless or choking is a breathing warning sign:
                # urgent review, not a routine model answer.
                profile['has_red_flag'] = True
                profile['red_flag_symptoms'] = [details['night_breathlessness']]
                break
            if question_id == 'fever' and answer == 'yes' and age == 0:
                from app.services.assessment_safety import detect_safety_signs
                profile['has_red_flag'] = True
                profile['red_flag_symptoms'] = detect_safety_signs('fever', age=0)
                break  # Newly disclosed infant fever also precedes more questions.
    present, absent = _features(states, details)
    unknown_count = sum(1 for a in answers[:len(asked)] if a.get('answer') == 'unknown')
    next_id = None if profile['has_red_flag'] else next_consultation_question(
        states, details, durations, asked, catalogue, age, sex)
    if unknown_count >= MAX_UNKNOWN_ANSWERS:
        # Checklist stop: not knowing is also an answer. Do not keep asking.
        next_id = None
    profile['_symptom_details'] = details
    profile.update({
        'confirmed_codes': [code for code, state in states.items() if state == 'present'],
        'model_features': present, 'explicitly_absent_features': absent,
        'follow_up_question': consultation_question(next_id, language) if next_id else None,
        'assessment_context': {
            'language': language, 'symptom_states': states, 'symptom_durations': durations,
            'duration': durations.get('cough') or durations.get('_general') or next(iter(durations.values()), None),
            'severity': {code: item['severity'] for code, item in details.items() if item.get('severity')},
            'cough_type': details.get('cough', {}).get('cough_type'),
            'onset_text': details.get('cough', {}).get('onset_text'),
            'weight_loss_intent': details.get('weight_loss', {}).get('weight_loss_intent'),
            'fatigue_pattern': details.get('tiredness', {}).get('fatigue_pattern'),
            'follow_up_answers': answers[:len(asked)], 'questions_asked': asked,
            'model_version': V3_MODEL_VERSION,
            'context_note': (
                'Modeli hii imefunzwa kwa dalili zilizoripotiwa na majibu ya ndiyo/hapana kutoka kwa wagonjwa wa kuigiza. '
                'Dalili ambazo hujataja hubaki hazijulikani. Muda na ukali husaidia ushauri, lakini si vipengele vya modeli. '
                'Matokeo hayajathibitishwa kitabibu.' if language == 'sw' else
                'This model learns reported symptoms and yes/no answers from complete simulated patient records. '
                'Unmentioned symptoms remain unknown. Duration and severity guide advice but are not trained disease-model features. '
                'Results have not been clinically validated.'),
        },
    })
    return profile
