"""Render model associations and practical guidance without claiming a diagnosis."""
from app.services.health_guidance import CONDITION_INFORMATION, get_prediction_guidance
from app.services.v3_prediction import get_v3_bundle
from app.services.patient_terminology import terminology

LIVE_MODEL_NOTICE = 'V3 partial-evidence: 21 conditions, 34 features; simulated DDXPlus only; not clinically validated for patients in Kenya.'

SW_SYMPTOMS = {
    'tiredness': 'uchovu', 'weakness': 'mwili kukosa nguvu',
    'cough': 'kikohozi', 'fever': 'homa', 'runny_blocked_nose': 'mafua au pua kuziba',
    'sore_throat': 'koo kuuma', 'muscle_aches': 'maumivu ya misuli', 'wheezing': 'sauti ya mluzi wakati wa kupumua',
    'productive_cough': 'makohozi yenye rangi au mengi kuliko kawaida',
    'weight_loss': 'kupungua uzito bila kukusudia', 'heavy_sweating': 'jasho jingi',
    'headache': 'kichwa kuuma', 'chest_pain': 'maumivu ya kifua',
    'shortness_of_breath': 'shida ya kupumua',
}


def withheld_viral_guidance(states, duration, sw):
    """Actionable advice for a likely viral cold/flu when no condition is named.

    Triggers on a mild sore-throat + runny/blocked-nose pattern, or on a
    patient-stated common cold or flu-like illness, with no danger sign.
    This is guidance, not a diagnosis: it does not name a condition.
    """
    cold_claim = states.get('common_cold') == 'present'
    flu_claim = states.get('flu_like') == 'present'
    urti = states.get('sore_throat') == 'present' and states.get('runny_blocked_nose') == 'present'
    if not (cold_claim or flu_claim or urti):
        return []
    danger = any(states.get(code) == 'present' for code in (
        'shortness_of_breath', 'intense_coughing_fits', 'vomiting_after_coughing',
        'chest_pain', 'weight_loss', 'weakness'))
    if danger:
        return []
    days = (duration or {}).get('min_days')
    if days is not None and days >= 14:
        return []
    if flu_claim:
        opening = ('Maelezo haya yanafanana na ugonjwa wenye dalili kama mafua. Virusi kadhaa vinaweza kusababisha hali hii, ikiwemo influenza na COVID; dalili pekee haziwezi kuthibitisha ni ipi. Pumzika, unywe maji, tumia paracetamol kwa maumivu au homa; antibiotiki hazisaidii kwa maambukizi ya virusi.' if sw else
            'This describes a flu-like illness. Several viruses, including influenza and COVID, can cause it; symptoms alone cannot confirm which one. Rest, drink fluids, and use paracetamol for discomfort or fever; antibiotics do not help a viral infection.')
    else:
        opening = ('Mchanganyiko huu mara nyingi hutokana na mafua ya virusi (maambukizi ya njia ya juu ya upumuaji). Kwa kawaida hupita yenyewe; pumzika, unywe maji, na tumia paracetamol kwa maumivu. Antibiotiki hazihitajiki kwa mafua ya virusi.' if sw else
            'This combination most often comes from a common viral cold (upper-respiratory infection). It usually clears on its own; rest, drink fluids, and use paracetamol for discomfort. Antibiotics are not needed for a viral cold.')
    lines = [
        opening,
        ('Mwone mhudumu wa afya kama haijaimarika baada ya siku 5-7, au mapema kwa shida ya kupumua, maumivu ya kifua, homa kali, au kama una pumu, COPD au kisukari.' if sw else
         'See a clinician if not improving in about 5-7 days, or sooner for breathing difficulty, chest pain, high fever, or if you have asthma, COPD or diabetes.'),
    ]
    if states.get('fever') == 'present' or states.get('chills') == 'present':
        lines.append(
            ('COVID na influenza zinaweza kuonekana hivi. Kama umepoteza ladha/harufu, umekaribiana na mwenye COVID, au unataka uhakika, ulizia kipimo cha COVID.' if sw else
             'COVID and flu can look like this. If you have loss of taste/smell, known COVID exposure, or want certainty, ask about a COVID test.'))
    return lines


def symptom_specific_advice(context, sw):
    """Plain-language advice tailored to the reported symptoms when no condition
    is named. Guidance only: it never names a diagnosis and adds no model
    evidence. Called only for the withheld (sparse) path."""
    states = context.get('symptom_states', {})
    duration = context.get('duration') or {}
    persistent = (duration.get('min_days') >= 14 if duration.get('min_days') is not None else any(
        word in str(duration.get('text', '')).lower() for word in ('weeks', 'months', 'wiki', 'miezi')))
    present = lambda code: states.get(code) == 'present'
    lines = []
    if present('headache') and present('fever'):
        lines.append(
            'Kichwa kuuma na homa vinaweza kuwa maambukizi makubwa. Tafuta huduma ya haraka ikifuatana na shingo ngumu, kuchanganyikiwa, vipele, au kusikia mwanga; vinginevyo fuatilia na upitie upya.' if sw else
            'Headache with fever can be a more serious infection. Seek urgent care if it comes with a stiff neck, confusion, a rash, or sensitivity to light; otherwise monitor and review.')
    elif present('headache'):
        lines.append(
            'Kichwa kipya, kikali, au cha upande mmoja, au chenye udhaifu wa kiungo, kuchanganyikiwa, shingo ngumu, au kuzimia kinahitaji tathmini ya haraka; vinginevyo fuatilia na tumia paracetamol.' if sw else
            'A new, severe, or one-sided headache, or one with limb weakness, confusion, a stiff neck, or fainting needs urgent assessment; otherwise monitor and use paracetamol.')
    if present('chest_pain'):
        lines.append(
            'Maumivu yoyote ya kifua yanahitaji kutathminiwa. Tafuta huduma sasa kama ni makali, yanaenea mkononi au taya, au yanafuatana na jasho, shida ya kupumua, au kichefuchefu.' if sw else
            'Any chest pain should be assessed. Seek care now if it is severe, spreads to your arm or jaw, or comes with sweating, breathlessness, or nausea.')
    if present('cough') and not persistent:
        lines.append(
            'Kikohozi kwa kawaida hutulia ndani ya wiki 2-3. Mwone mhudumu wa afya mapema kama kinazidi, unakohoa damu, au una shida ya kupumua, maumivu ya kifua, au homa isiyotulia.' if sw else
            'A cough usually settles within 2-3 weeks. See a clinician sooner if it is getting worse, you cough blood, or you have breathing difficulty, chest pain, or a fever that does not settle.')
    if present('wheezing'):
        lines.append(
            'Sauti ya mluzi inaweza kuwa pumu au maambukizi ya kifua. Mwone mhudumu wa afya kama ni mpya, au kama una pumu au COPD na inhaler yako ya kawaida haisaidii.' if sw else
            'Wheezing can be asthma or a chest infection. See a clinician if it is new, or if you have asthma or COPD and your usual inhaler is not helping.')
    if present('sore_throat') and not present('runny_blocked_nose'):
        lines.append(
            'Koo kuuma mara nyingi hutokana na virusi na hutulia yenyewe; paracetamol hupunguza maumivu. Antibiotiki hazihitajiki kwa koo la virusi.' if sw else
            'A sore throat most often comes from a virus and settles on its own; paracetamol eases the pain. Antibiotics are not needed for a viral sore throat.')
    if present('heavy_sweating'):
        lines.append(
            'Jasho usiku na kikohozi kinachoendelea au kupungua uzito vinahitaji tathmini (inawezekana TB); vikiwa peke yake, fuatilia na upitie upya vikiendelea.' if sw else
            'Night sweats with a persistent cough or weight loss need assessment (possible TB); on their own, monitor and review if they continue.')
    if present('muscle_aches') or present('chills'):
        lines.append(
            'Maumivu ya mwili na kutetemeka mara nyingi hutokea na homa na maambukizi ya virusi; pumzika, unywe maji, na tumia paracetamol. Mwone mhudumu wa afya kama vinaendelea zaidi ya siku chache.' if sw else
            'Body aches and chills commonly occur with fever and viral infections; rest, fluids, and paracetamol help. See a clinician if they persist beyond a few days.')
    if present('weakness') or present('tiredness'):
        lines.append(
            'Uchovu au udhaifu usio wa kawaida mara nyingi huboreka kwa kupumzika na maji. Mwone mhudumu wa afya kama ni mkali, unaendelea zaidi ya wiki mbili, au unafuatana na kupungua uzito, jasho usiku, au shida ya kupumua.' if sw else
            'Unusual tiredness or weakness often improves with rest and fluids. See a clinician if it is severe, persistent beyond a couple of weeks, or comes with weight loss, night sweats, or shortness of breath.')
    return lines


def consultation_guidance(context, age):
    language = context.get('language', 'en')
    sw = language == 'sw'
    states = context.get('symptom_states', {})
    duration = context.get('duration') or {}
    persistent = (duration.get('min_days') >= 14 if duration.get('min_days') is not None else any(
        word in str(duration.get('text', '')).lower() for word in ('weeks', 'months', 'wiki', 'miezi')))
    severe = any(value == 'severe' for value in context.get('severity', {}).values())
    weakness_review = states.get('weakness') == 'present' and context.get('weakness_meaning') in {'other_weakness', 'unknown'}
    review = states.get('weight_loss') == 'present' or persistent or severe or weakness_review or (age < 5 and states.get('fever') == 'present')
    next_steps = ([
        'Tafuta tathmini ya mtaalamu wa afya kwa dalili kali, zinazoendelea, kupungua uzito bila kukusudia, au homa kwa mtoto mdogo.',
        'Daktari anaweza kuhitaji kukupima au kufanya vipimo; orodha hii haiwezi kuthibitisha au kuondoa ugonjwa.',
    ] if review else [
        'Pumzika na kunywa maji kadiri unavyoweza; fuatilia kama dalili zinaimarika au zinazidi.',
        'Dalili zikizidi, zikiendelea au zikikutia wasiwasi, tafuta tathmini ya mtaalamu wa afya.',
    ]) if sw else ([
        'Arrange a clinical assessment for severe or persistent symptoms, unexplained weight loss, or fever in a young child.',
        'A clinician may need an examination or tests; this list cannot confirm or rule out a condition.',
    ] if review else [
        'Rest, drink fluids as you can, and monitor whether symptoms improve or worsen.',
        'Seek clinical assessment if symptoms worsen, persist, or concern you.',
    ])
    next_steps.append('Ukipata shida kali ya kupumua, kushindwa kuzungumza au midomo kuwa ya buluu, tafuta huduma ya dharura mara moja.'
                      if sw else 'Seek emergency care immediately for severe breathing difficulty, inability to speak normally, or blue lips.')
    days = duration.get('min_days')
    respiratory = any(states.get(code) == 'present' for code in ('cough', 'sore_throat', 'runny_blocked_nose',
        'shortness_of_breath', 'wheezing', 'productive_cough', 'intense_coughing_fits', 'vomiting_after_coughing'))
    duration_advice = (
        ('Dalili za siku 2-3 zinaweza kutokana na maambukizi ya muda mfupi kama influenza, virusi vingine, COVID, bronchitis (maambukizi ya kifua), au nimonia ya awali. Ukiwa na homa nchini Kenya, ulizia kipimo cha malaria.' if sw else
         'Symptoms over 2-3 days can occur with acute infections such as influenza, other viruses, COVID, acute bronchitis (chest infection), or early pneumonia. With fever in Kenya, ask about a malaria test.')
        if respiratory and days is not None and days <= 3 else
        ('Kikohozi cha siku 14 au zaidi kinahitaji uchunguzi wa TB, pumu, COPD au sababu nyingine; muda pekee hautambui ugonjwa.' if sw else
         'Cough lasting 14 days or more needs assessment for TB, asthma, COPD or other causes; duration alone cannot identify a condition.')
        if persistent and states.get('cough') == 'present' else
        ('Dalili za siku 3-14 zikiendelea au zikizidi zinahitaji tathmini; muda pekee hautambui chanzo.' if sw else
         'Symptoms lasting 3-14 days need review if they persist or worsen; duration alone cannot identify the cause.')
        if respiratory and days is not None else
        ('Muda pekee hautambui chanzo. Dalili zisipoimarika, zikiathiri shughuli zako au zikikutia wasiwasi, panga kuonana na mhudumu wa afya.' if sw else
         'Duration alone does not identify the cause. If symptoms are not improving, affect your usual activities or worry you, arrange a health-worker review.')
        if days is not None else None)
    if respiratory and days is not None and days <= 3 and states.get('fever') != 'present':
        duration_advice = ('Dalili za muda mfupi za kupumua zinaweza kuwa na sababu tofauti; muda pekee hautambui maambukizi.' if sw else
            'Short-duration respiratory symptoms can have different causes; duration alone does not identify an infection.')
    if duration_advice:
        next_steps.insert(1, duration_advice)
    if not respiratory and states.get('fever') == 'present':
        next_steps.insert(1, 'Ukiwa na homa nchini Kenya, ulizia kama kipimo cha malaria kinahitajika; dalili pekee hazithibitishi malaria.' if sw else
            'With fever in Kenya, ask a health worker whether a malaria test is needed; symptoms alone do not confirm malaria.')
    if weakness_review:
        next_steps[0] = ('Panga tathmini ya mhudumu wa afya kwa kupungua nguvu kusikoeleweka au shida ya kusogeza mwili; usisubiri hali izidi.' if sw else
            'Arrange a health-worker assessment for unexplained loss of strength or difficulty moving normally; do not wait for it to worsen.')
    return {
        **get_prediction_guidance(language, context),
        'assessment_summary': (
            'Dalili zako zinaweza kuonekana katika hali kadhaa za mfumo wa upumuaji. Haya ni maelezo yanayowezekana, si utambuzi wa ugonjwa.'
            if sw else
            'Your symptoms overlap with several respiratory conditions. These are possible explanations, not a diagnosis.'),
        'uncertainty_message': (
            'Maelezo haya ni ya awali. Maswali na majibu yanasaidia kulinganisha dalili, lakini uchunguzi au vipimo vinaweza kuhitajika.'
            if sw else
            'This is a tentative assessment. Your answers help compare patterns, but an examination or tests may be needed.'),
        'next_steps': next_steps, 'care_level': 'professional_review' if review else 'self_care_or_review',
        'score_note': (
            'Alama ni za kulinganisha mifumo katika data ya kuigiza; si uwezekano wa kitabibu uliothibitishwa.'
            if sw else
            'Scores compare patterns in a simulated dataset. They are not validated clinical probabilities or estimates of illness severity.'),
        'context_note': context.get('context_note'),
        'duration_advice': duration_advice,
        'covid_scope_message': terminology()['covid_scope_message']['sw' if sw else 'en'],
        'live_model_notice': LIVE_MODEL_NOTICE,
    }


def explain_v3_candidates(result, confirmation, catalogue, language):
    states = confirmation['assessment_context']['symptom_states']
    feature_names = {}
    for row in catalogue:
        if states.get(row.code) not in {'present', 'absent'}:
            continue
        name = SW_SYMPTOMS.get(row.code, row.display_name) if language == 'sw' else row.display_name
        for feature in row.features:
            feature_names.setdefault(feature, name)
    def phrases(features, negative=False):
        values = [feature_names[feature] for feature in features if feature in feature_names]
        if negative:
            values = [('hakuna ' if language == 'sw' else 'No ') + value for value in values]
        return list(dict.fromkeys(values))
    candidates = []
    for prediction in result['predictions']:
        condition = prediction['condition']
        info = CONDITION_INFORMATION.get(condition)
        if info is None:
            raise ValueError(f'Condition explanation is unavailable: {condition}')
        support = phrases(prediction.get('supporting_features', [])) + phrases(prediction.get('supporting_absent_features', []), True)
        counter = phrases(prediction.get('contradicting_features', [])) + phrases(prediction.get('contradicting_absent_features', []), True)
        candidates.append({
            'rank': prediction['rank'], 'condition': condition, 'display_name': info['display_name'],
            'description': info['short_description'],
            'model_confidence_percent': round(prediction['raw_relative_score'] * 100, 2),
            'supporting_symptoms': list(dict.fromkeys(support)),
            'contradicting_symptoms': list(dict.fromkeys(counter)),
            'explanation': (
                'Mfumo huu unalingana kwa kiasi na taarifa ulizotoa. Dalili hizi zinaweza pia kutokana na hali nyingine.'
                if language == 'sw' else
                'This pattern partly matches the information you provided. The same symptoms can occur with other conditions.'),
            'evidence_note': (
                'Sababu hizi ni mahusiano yaliyojifunzwa katika wagonjwa wa kuigiza, si uthibitisho wa kitabibu.'
                if language == 'sw' else
                'These reasons describe associations learned from simulated patient records, not clinical confirmation.'),
        })
    return candidates
