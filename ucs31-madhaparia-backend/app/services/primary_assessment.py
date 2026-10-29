"""Patient-facing selective result, scope safeguards and explicit uncertainty."""
from copy import deepcopy
from app.core.errors import ServiceNotReadyError
from app.services.patient_terminology import patient_term
from app.services.consultation_guidance import consultation_guidance, SW_SYMPTOMS
from app.services.v3_prediction import get_v3_bundle

PATIENT_POLICY_VERSION = 'kenya_single_primary_v1'
RESPIRATORY_FEATURES = frozenset({'E_103','E_112','E_166','E_169','E_181','E_182','E_190','E_194',
 'E_201','E_203','E_212','E_214','E_217','E_220','E_45','E_65','E_66','E_67','E_77','E_97'})
PUBLIC_CONTEXT_FIELDS = {'language','symptom_states','symptom_durations','duration','severity','cough_type',
 'onset_text','weight_loss_intent','fatigue_pattern','follow_up_answers','questions_asked','model_version','context_note','age'}


def has_respiratory_scope(features):
    return bool(set(features) & RESPIRATORY_FEATURES)


def public_assessment_context(context):
    public = {key: deepcopy(value) for key,value in (context or {}).items() if key in PUBLIC_CONTEXT_FIELDS}
    if 'context_note' in public:
        public['context_note'] = (
            'Programu hii inatathmini baadhi ya magonjwa ya mfumo wa upumuaji. Uchunguzi au vipimo vinaweza kuhitajika.'
            if public.get('language') == 'sw' else
            'This app considers a limited set of respiratory conditions. An examination or tests may be needed.')
    return public


def select_primary_evidence(present_features, absent_features, age, sex):
    from app.ml.primary_selection import classify_primary
    supported = set(get_v3_bundle()['features'])
    missing = (set(present_features)|set(absent_features)) - supported
    try:
        result = classify_primary([x for x in present_features if x in supported],
                                  [x for x in absent_features if x in supported], age, sex)
    except (OSError, ValueError, KeyError) as error:
        raise ServiceNotReadyError('The assessment decision policy is unavailable or does not match its model.') from error
    if missing:
        result.update(status='uncertain', primary_prediction=None, reasons=['unsupported_information'])
        result['diagnostics']['unsupported_features'] = sorted(missing)
    return result


def patient_guidance(context, age, decision_status='uncertain', primary=None):
    sw = context.get('language') == 'sw'
    base = consultation_guidance(context, age)
    # No confidence percentage, ranking score or technical probability note is
    # exposed on the patient transport contract, including expandable sections.
    base.pop('score_note', None)
    base.pop('confidence_explanation', None)
    base['context_note'] = public_assessment_context(dict(context, context_note=''))['context_note']
    states = context.get('symptom_states', {})
    scope = has_respiratory_scope(context.get('_present_features', []))
    if decision_status == 'insufficient_information':
        summary = ('Tafadhali eleza dalili unazohisi na muda ambao umekuwa nazo, ili tuweze kuuliza maswali yanayofaa.' if sw else
                   'Please describe the symptoms you are experiencing and how long you have had them, so we can ask relevant questions.')
    elif 'unsupported_information' in context.get('_decision_reasons', []):
        summary = ('Programu haijaelewa baadhi ya maelezo. Tafadhali yaeleze tena au wasiliana na mtaalamu wa afya.' if sw else
                   'Some details could not be understood by this app. Please rephrase them or contact a healthcare professional.')
    elif primary is not None:
        summary = ('Hili ni jambo linaloweza kueleza dalili zako, si utambuzi uliothibitishwa.' if sw else
                   'This is one possible explanation for your symptoms, not a confirmed diagnosis.')
    elif not scope and any(value == 'present' for value in states.values()):
        summary = ('Dalili hizi zinaweza kuwa na sababu kadhaa. Programu hii inalenga magonjwa ya mfumo wa upumuaji na haiwezi kutathmini sababu zote.' if sw else
                   'These symptoms can have several causes. This app focuses on respiratory conditions and cannot assess every possible cause.')
    else:
        summary = ('Dalili ulizotoa zinafanana na hali kadhaa. Kwa sasa hatuwezi kupendekeza ugonjwa mmoja kwa msingi wa taarifa hizi.' if sw else
                   'The symptoms you reported overlap with several conditions. The information does not support naming one illness at this point.')
    base['assessment_summary'] = summary
    base['uncertainty_message'] = ('Maswali yanasaidia kuelewa dalili, lakini uchunguzi au vipimo vya mtaalamu wa afya vinaweza kuhitajika.' if sw else
                                   'Your answers help clarify the symptoms, but an examination or tests may be needed.')
    # A possibility of these conditions needs clinical assessment, rather than
    # a generic home-care recommendation based on a relative model ranking.
    medical_review_classes = {'Tuberculosis','Pulmonary neoplasm','Pneumonia','Whooping cough',
        'Acute pulmonary edema','Spontaneous pneumothorax','Epiglottitis',
        'Acute COPD exacerbation / infection','Bronchiolitis','Croup','Larygospasm'}
    if primary and primary['condition'] in medical_review_classes:
        base['care_level'] = 'professional_review'
        base['next_steps'] = [
            ('Wasiliana na mtaalamu wa afya ili atathmini dalili hizi; uchunguzi au vipimo vinaweza kuhitajika.' if sw else
             'Contact a healthcare professional to assess this possibility; an examination or tests may be needed.'),
            base['next_steps'][-1],
        ]
    base['health_guidance'] = base['next_steps'][0]
    return base


def build_primary_assessment(confirmation, age, sex):
    context = confirmation['assessment_context']
    language = context.get('language', 'en')
    sw = language == 'sw'
    present = confirmation['model_features']
    absent = confirmation.get('explicitly_absent_features', [])
    try:
        chosen = select_primary_evidence(present, absent, age, sex)
    except (OSError, ValueError, KeyError) as error:
        raise ServiceNotReadyError('The current assessment decision policy is unavailable or does not match its model.') from error
    primary = None
    reasons = list(chosen.get('reasons', []))
    # Unknown wording is not a formally validated OOD detector. It is an input
    # completeness guard: unsupported details must not silently produce a name.
    if confirmation.get('unmatched_wording'):
        chosen['status'], chosen['primary_prediction'] = 'uncertain', None
        reasons = ['unsupported_information']
    if any(value == 'severe' for value in context.get('severity', {}).values()):
        chosen['status'], chosen['primary_prediction'] = 'uncertain', None
        reasons = ['clinical_assessment_needed']
    if chosen['status'] == 'eligible' and chosen.get('primary_prediction'):
        raw = chosen['primary_prediction']
        primary = {**patient_term(raw['condition'], language),
            'explanation': ('Dalili ulizoripoti zinapatana na maelezo haya, lakini pia zinaweza kuonekana katika hali nyingine.' if sw else
                            'Some of the symptoms you reported are consistent with this possibility, but they can also occur in other conditions.'),
            'supporting_symptoms': list(dict.fromkeys(
                SW_SYMPTOMS.get(code, item.get('display_name', code.replace('_',' '))) if sw
                else item.get('display_name', code.replace('_',' '))
                for code,item in confirmation.get('_symptom_details', {}).items()
                if context.get('symptom_states', {}).get(code) == 'present')),
            'evidence_note': ('Matokeo haya hayajathibitishwa katika huduma za kliniki nchini Kenya.' if sw else
                              'This assessment has not been clinically validated for patients in Kenya.'),
        }
    reported = any(value in {'present','unknown'} for value in context.get('symptom_states', {}).values())
    decision_status = 'possible_explanation' if primary else 'uncertain' if reported else 'insufficient_information'
    status = 'prediction_complete' if primary else 'assessment_uncertain' if reported else 'insufficient_evidence'
    decision = {'status': decision_status, 'reasons': reasons,
                'policy_version': PATIENT_POLICY_VERSION, 'source_policy_version': chosen.get('policy_version')}
    guidance_context = dict(context, _present_features=present, _decision_reasons=reasons)
    result = {'status': status, 'primary_prediction': primary, 'predictions': [primary] if primary else [],
              'decision': decision, 'uncertain': True, 'clinical_validation': False,
              'model_status': 'research_selective_primary',
              **patient_guidance(guidance_context, age, decision_status, primary)}
    # Private audit details are stored separately and removed from patient JSON.
    result['_audit'] = {'selection': chosen, 'input_guard_reasons': reasons}
    return result


def history_patient_projection(session):
    context = getattr(session, 'assessment_context', {}) or {}
    language = context.get('language', 'en')
    sw = language == 'sw'
    base = {'prediction_id': str(session.id), 'age': session.age, 'sex': session.sex,
            'input_text': session.input_text, 'confirmed_codes': session.confirmed_codes,
            'created_at': session.created_at, 'has_red_flag': session.has_red_flag,
            'assessment_context': public_assessment_context(context), 'predictions': [], 'primary_prediction': None,
            'clinical_validation': False, 'uncertain': True}
    if session.status == 'urgent_review' or session.has_red_flag:
        from app.services.health_guidance import get_urgent_guidance
        return {**base, 'status': 'urgent_review',
                'decision': {'status':'urgent_review','reasons':['reported_warning_sign'],'policy_version':PATIENT_POLICY_VERSION},
                **get_urgent_guidance(language)}
    saved = context.get('patient_decision', {})
    if saved.get('policy_version') != PATIENT_POLICY_VERSION:
        return {**base, 'status':'reassessment_required',
                'decision': {'status':'uncertain','reasons':['previous_assessment_policy'],'policy_version':PATIENT_POLICY_VERSION},
                **patient_guidance(context, session.age),
                'assessment_summary': ('Hii ni rekodi ya toleo la awali. Fanya tathmini mpya ili kutumia njia ya sasa.' if sw else
                                       'This record was produced by an earlier assessment policy. Start a new assessment to use the current approach.')}

    primary = context.get('_patient_primary') if saved.get('status') == 'possible_explanation' else None
    if primary:
        primary = {**primary, **patient_term(primary['condition'], language)}
    return {**base, 'status':session.status, 'primary_prediction':primary,
            'predictions':[primary] if primary else [], 'decision': saved,
            'model_version': context.get('model_version'), 'uncertain': True, 'clinical_validation':False,
            **patient_guidance(dict(context, _present_features=session.model_features,
                                    _decision_reasons=saved.get('reasons', [])),
                               session.age, saved.get('status'), primary)}
