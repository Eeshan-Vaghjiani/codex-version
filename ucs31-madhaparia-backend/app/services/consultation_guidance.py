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
