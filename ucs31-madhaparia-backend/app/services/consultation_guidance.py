"""Render model associations and practical guidance without claiming a diagnosis."""
from app.services.health_guidance import CONDITION_INFORMATION, get_prediction_guidance
from app.services.v3_prediction import get_v3_bundle

SW_SYMPTOMS = {
    'cough': 'kikohozi', 'fever': 'homa', 'runny_blocked_nose': 'mafua au pua kuziba',
    'sore_throat': 'koo kuuma', 'muscle_aches': 'maumivu ya misuli', 'wheezing': 'sauti ya mluzi wakati wa kupumua',
    'productive_cough': 'makohozi yenye rangi au mengi kuliko kawaida',
    'weight_loss': 'kupungua uzito bila kukusudia', 'heavy_sweating': 'jasho jingi',
    'headache': 'kichwa kuuma', 'chest_pain': 'maumivu ya kifua',
    'shortness_of_breath': 'shida ya kupumua',
}


def symptom_specific_advice(context, sw):
    """Plain-language advice tailored to the reported symptoms when no
    condition is named. Taken from Codex 292acf1 (with credit in
    CHANGELOG), adapted to Muse's guards: guidance only, never a
    diagnosis, no model evidence, and NO specific medicine is named
    (Codex's paracetamol lines are replaced with rest/fluids/monitor
    wording, per Muse's no-specific-medicine rule). Called only for a
    withheld (sparse) result at self-care/review level, never for an
    urgent or professional-review result."""
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
            'Kichwa kipya, kikali, au cha upande mmoja, au chenye udhaifu wa kiungo, kuchanganyikiwa, shingo ngumu, au kuzimia kinahitaji tathmini ya haraka; vinginevyo pumzika, kunywa maji na fuatilia.' if sw else
            'A new, severe, or one-sided headache, or one with limb weakness, confusion, a stiff neck, or fainting needs urgent assessment; otherwise rest, drink fluids and monitor.')
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
            'Koo kuuma mara nyingi hutokana na virusi na hutulia yenyewe; pumzika na kunywa maji.' if sw else
            'A sore throat most often comes from a virus and settles on its own; rest and drink fluids.')
    if present('heavy_sweating'):
        lines.append(
            'Jasho usiku na kikohozi kinachoendelea au kupungua uzito vinahitaji tathmini (inawezekana TB); vikiwa peke yake, fuatilia na upitie upya vikiendelea.' if sw else
            'Night sweats with a persistent cough or weight loss need assessment (possible TB); on their own, monitor and review if they continue.')
    if present('muscle_aches') or present('chills'):
        lines.append(
            'Maumivu ya mwili na kutetemeka mara nyingi hutokea na homa na maambukizi ya virusi; pumzika, unywe maji. Mwone mhudumu wa afya kama vinaendelea zaidi ya siku chache.' if sw else
            'Body aches and chills commonly occur with fever and viral infections; rest and drink fluids. See a clinician if they persist beyond a few days.')
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
    review = states.get('weight_loss') == 'present' or persistent or severe or (age < 5 and states.get('fever') == 'present')
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
    # Duration advice (advice-only, NOT a model feature). Acute vs chronic
    # thinking, in plain language, with a concrete next step.
    min_days = duration.get('min_days')
    if min_days is not None and min_days < 3:
        duration_advice = ('Dalili za siku 2-3 mara nyingi ni za papo hapo: mafua, maambukizi ya virusi, COVID inawezekana, maambukizi ya kifua ya papo hapo, au nimonia ya mwanzo. Ikiwa una homa nchini Kenya, fikiria kipimo cha malaria.'
                           if sw else
                           'Symptoms for 2-3 days are usually acute: flu or a viral infection, COVID is possible, acute chest infection, or early pneumonia. If you have a fever in Kenya, consider a malaria test.')
    elif min_days is not None and min_days >= 14:
        duration_advice = ('Kikohozi cha zaidi ya wiki 2 kinahitaji uchunguzi wa muda mrefu: TB, pumu, au COPD. Uliza kuhusu kipimo cha TB na uchunguzi wa kifua.'
                           if sw else
                           'A cough for more than 2 weeks needs a chronic workup: TB, asthma, or COPD. Ask about a TB test and a chest examination.')
    elif persistent:
        duration_advice = ('Kikohozi cha muda mrefu kinahitaji uchunguzi wa muda mrefu: TB, pumu, au COPD. Uliza kuhusu kipimo cha TB.'
                           if sw else
                           'A persistent cough needs a chronic workup: TB, asthma, or COPD. Ask about a TB test.')
    else:
        duration_advice = None
    if duration_advice:
        # After the primary care step: health_guidance is next_steps[0]
        # and must stay the care recommendation, not duration context.
        next_steps.insert(1, duration_advice)
    next_steps.append('Ukipata shida kali ya kupumua, kushindwa kuzungumza au midomo kuwa ya buluu, tafuta huduma ya dharura mara moja.'
                      if sw else 'Seek emergency care immediately for severe breathing difficulty, inability to speak normally, or blue lips.')
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
