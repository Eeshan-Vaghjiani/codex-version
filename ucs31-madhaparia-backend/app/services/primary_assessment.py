"""Patient-facing selective result, scope safeguards and explicit uncertainty."""
from copy import deepcopy
from app.core.errors import ServiceNotReadyError
from app.services.patient_terminology import patient_term
from app.services.consultation_guidance import consultation_guidance, SW_SYMPTOMS
from app.services.health_guidance import COVID_SCOPE_NOTE
from app.services.v3_prediction import get_v3_bundle

PATIENT_POLICY_VERSION = 'kenya_single_primary_v1'
RESPIRATORY_FEATURES = frozenset({'E_103','E_112','E_166','E_169','E_181','E_182','E_190','E_194',
 'E_201','E_203','E_212','E_214','E_217','E_220','E_45','E_65','E_66','E_67','E_77','E_97'})
PUBLIC_CONTEXT_FIELDS = {'language','symptom_states','symptom_durations','duration','severity','cough_type',
 'onset_text','weight_loss_intent','fatigue_pattern','follow_up_answers','questions_asked','model_version','context_note','age'}

# Family-level flu-like answer. NOT a model class and NOT a diagnosis: a
# family of common viral upper-respiratory illnesses, used only for the
# narrow 4:0 exception in primary_selection.py. Dual format, as for every
# patient result: simple name first, medical description in parentheses.
FAMILY_DUAL_NAME = {
    'en': 'Flu-like illness / common cold (viral upper respiratory infection)',
    'sw': 'Ugonjwa unaofanana na mafua / mafua ya kawaida (maambukizi ya virusi ya njia za juu za hewa)',
}
FAMILY_SIMPLE_NAME = {
    'en': 'Flu-like illness / common cold',
    'sw': 'Ugonjwa unaofanana na mafua / mafua ya kawaida',
}
FAMILY_DESCRIPTION = {
    'en': 'A family of common viral illnesses of the nose and throat. This is not one confirmed disease: influenza, a common cold and other viral upper-respiratory illnesses overlap heavily and cannot be separated from these symptoms alone.',
    'sw': 'Familia ya magonjwa ya kawaida ya virusi ya pua na koo. Hii si ugonjwa mmoja uliothibitishwa: influenza, mafua ya kawaida na magonjwa mengine ya virusi ya njia za juu za hewa yanafanana sana na hayawezi kutenganishwa kwa dalili hizi pekee.',
}
FAMILY_NOTE = {
    'en': 'Family answer, not a diagnosis: this names a family of common viral illnesses, not one confirmed disease.',
    'sw': 'Jibu la familia, si utambuzi: hili linataja familia ya magonjwa ya kawaida ya virusi, si ugonjwa mmoja uliothibitishwa.',
}
TB_NOTE = {
    'en': 'About TB: TB is a bacterial infection. It is testable and treatable. Having TB does not mean having HIV, and TB is nothing to be ashamed of.',
    'sw': 'Kuhusu TB: TB ni maambukizi ya bakteria. Inaweza kupimwa na kutibiwa. Kuwa na TB haimaanishi kuwa na HIV, na TB si jambo la aibu.',
}
# Features that count as specific support for a serious name (see
# primary_selection.SPARSE_SERIOUS_FEATURES). Used as defence in depth here.
_SPARSE_SPECIFIC_FEATURES = frozenset({'E_162', 'E_45', 'E_14', 'E_66', 'E_50'})


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
    # Withheld / uncertain wording must never read as reassurance.
    if decision_status in ('uncertain', 'insufficient_information') or primary is None:
        reason = (context.get('_decision_reasons') or [None])[0]
        reason_text = {
            'close_alternative': 'The top two patterns were too close to choose one safely.',
            'dangerous_close_second': 'A serious condition was close behind the top pattern, so no single name is given.',
            'non_specific_input': 'The symptoms do not point clearly to a respiratory condition.',
            'insufficient_evidence': 'There is too little information to name one condition.',
            'ambiguous_model_rank': 'The patterns were too close or too weak to name one condition safely.',
        }.get(reason, 'There is not enough clear information to name one condition safely.')
        reason_text_sw = {
            'close_alternative': 'Mifumo miwili ya juu ilikuwa karibu sana kuchagua moja kwa usalama.',
            'dangerous_close_second': 'Hali mbaya ilikuwa karibu nyuma ya mfumo wa juu, kwa hivyo jina moja halitolewi.',
            'non_specific_input': 'Dalili hazielekezi wazi kwa ugonjwa wa mfumo wa upumuaji.',
            'insufficient_evidence': 'Taarifa ni chache mno kutaja ugonjwa mmoja.',
            'ambiguous_model_rank': 'Mifumo ilikuwa karibu sana au dhaifu mno kutaja ugonjwa mmoja kwa usalama.',
        }.get(reason, 'Hakuna taarifa wazi za kutosha kutaja ugonjwa mmoja kwa usalama.')
        base['withheld_reason'] = reason_text_sw if sw else reason_text
        base['withheld_message'] = (
            'Hatukuweza kutaja ugonjwa mmoja kutokana na taarifa hizi. Hii HAIMAANISHI uko sawa, na HAIONDOI ugonjwa wowote. Fuatilia kwa saa 24-48, na tafuta huduma mapema ikiwa dalili zinazidi au dalili ya hatari inatokea.'
            if sw else
            'We cannot name one condition from this information. This does NOT mean you are fine, and it does NOT rule out any condition. Check again in 24-48 hours if symptoms continue, and seek care sooner if they get worse or a warning sign appears.')
    # COVID is out of scope in V3. Show the note whenever taste/smell loss,
    # sinusitis, or a flu-like result is involved, and on every withheld result.
    states = context.get('symptom_states', {})
    needs_covid_note = (
        states.get('loss_of_smell') == 'present' or states.get('loss_of_taste') == 'present'
        or (primary and primary['condition'] in ('Acute rhinosinusitis', 'Chronic rhinosinusitis', 'Allergic sinusitis', 'Influenza', 'URTI'))
        or (primary and primary.get('is_family_answer'))
        or primary is None
    )
    if needs_covid_note:
        base['covid_scope_note'] = COVID_SCOPE_NOTE['sw' if sw else 'en']
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
    if 'dangerous_close_second' in context.get('_decision_reasons', []):
        base['care_level'] = 'professional_review'
        base['next_steps'] = [
            ('Hali mbaya inaweza kuwa karibu. Tafuta tathmini ya mtaalamu wa afya leo, usisubiri.' if sw else
             'A serious condition may be close behind. Seek professional assessment today, do not wait.'),
            base['next_steps'][-1],
        ]
    if 'sparse_serious_guard' in context.get('_decision_reasons', []):
        base['care_level'] = 'professional_review'
        base['next_steps'] = [
            ('Dalili hizi pekee hazitoshi kutaja ugonjwa mbaya kwa uhakika. Tafuta tathmini ya mtaalamu wa afya; uchunguzi au vipimo vinaweza kuhitajika.' if sw else
             'These symptoms alone are not enough to name a serious condition with confidence. Seek professional assessment; an examination or tests may be needed.'),
            base['next_steps'][-1],
        ]
    # Withheld must still be useful: never a bare "we cannot name one" with
    # no next step. A fever in Kenya always gets a malaria-test step.
    if primary is None and states.get('fever') == 'present':
        malaria_step = ('Ikiwa una homa nchini Kenya, fikiria kipimo cha malaria.' if sw else
                        'If you have a fever in Kenya, consider a malaria test.')
        if malaria_step not in base['next_steps']:
            base['next_steps'].insert(1, malaria_step)
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
    # Defence in depth for the sparse-serious guard: even if a caller
    # bypasses classify_primary's guard, a serious name on <=3 present
    # features with no specific support never reaches the patient here.
    if chosen['status'] == 'eligible' and chosen.get('primary_prediction'):
        _raw_condition = chosen['primary_prediction'].get('condition')
        _match = chosen.get('match') or {}
        _is_sparse_serious = (
            _raw_condition == 'Pulmonary neoplasm'
            or (_raw_condition == 'Tuberculosis' and (_match.get('band') == 'strong'))
        ) and len(present) <= 3 and not (set(present) & _SPARSE_SPECIFIC_FEATURES)
        if _is_sparse_serious:
            chosen['status'], chosen['primary_prediction'] = 'uncertain', None
            reasons = ['sparse_serious_guard']
    if chosen['status'] == 'family' and chosen.get('primary_prediction'):
        raw = chosen['primary_prediction']
        primary = {
            'condition': raw['condition'],
            'is_family_answer': True,
            'family_top_condition': raw.get('family_top_condition'),
            'medical_name': 'Viral upper respiratory infection',
            'display_name': FAMILY_DUAL_NAME['sw' if sw else 'en'],
            'dual_name': FAMILY_DUAL_NAME['sw' if sw else 'en'],
            'simple_name': FAMILY_SIMPLE_NAME['sw' if sw else 'en'],
            'description': FAMILY_DESCRIPTION['sw' if sw else 'en'],
            'family_note': FAMILY_NOTE['sw' if sw else 'en'],
            'match_percent_rounded': (chosen.get('match') or {}).get('percent_rounded'),
            'match_band': (chosen.get('match') or {}).get('band'),
            'match_label': (chosen.get('match') or {}).get('label'),
            'match_label_detail': ('Alama hii ni ya familia ya magonjwa ya virusi, si uwezekano kwamba una ugonjwa mmoja uliothibitishwa.' if sw else
                                   'This match is for the viral family pattern, not the probability that you have one confirmed disease.'),
            'explanation': ('Dalili ulizoripoti zinapatana na familia hii ya magonjwa ya kawaida ya virusi, lakini pia zinaweza kuonekana katika hali nyingine.' if sw else
                            'Some of the symptoms you reported fit this family of common viral illnesses, but they can also occur in other conditions.'),
            'supporting_symptoms': list(dict.fromkeys(
                SW_SYMPTOMS.get(code, item.get('display_name', code.replace('_',' '))) if sw
                else item.get('display_name', code.replace('_',' '))
                for code,item in confirmation.get('_symptom_details', {}).items()
                if context.get('symptom_states', {}).get(code) == 'present')),
            'evidence_note': ('Matokeo haya hayajathibitishwa katika huduma za kliniki nchini Kenya.' if sw else
                              'This assessment has not been clinically validated for patients in Kenya.'),
        }
    if chosen['status'] == 'eligible' and chosen.get('primary_prediction'):
        raw = chosen['primary_prediction']
        primary = {**patient_term(raw['condition'], language),
            'match_percent_rounded': (chosen.get('match') or {}).get('percent_rounded'),
            'match_band': (chosen.get('match') or {}).get('band'),
            'match_label': (chosen.get('match') or {}).get('label'),
            'match_label_detail': (chosen.get('match') or {}).get('label_detail'),
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
    if primary and primary.get('condition') == 'Tuberculosis':
        primary['tb_note'] = TB_NOTE['sw' if sw else 'en']
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
