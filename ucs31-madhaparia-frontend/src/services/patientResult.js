// Patient views require an explicit backend selection decision. Ranked model
// candidates (including historical ones) must never become a primary by position.
export function getPatientPrimary(result) {
  if (result?.status !== 'prediction_complete' || result?.has_red_flag === true ||
      ['emergency', 'urgent_same_day'].includes(result?.urgency) ||
      result?.care_level === 'urgent_review' ||
      result?.decision?.status !== 'possible_explanation' ||
      !result?.decision?.policy_version ||
      !result?.primary_prediction?.display_name) return null
  return result.primary_prediction
}

export function hasPatientDecision(result) {
  return Boolean(result?.decision?.policy_version)
}

export function getPatientMatch(primary) {
  const percent = primary?.model_match_percent
  if (primary?.score_kind !== 'v3_relative_model_match' ||
      !Number.isInteger(percent) || percent < 0 || percent > 100) return null
  return `${percent}%`
}

export function buildPatientSummary(result, inputText) {
  const context = result?.assessment_context || {}
  const duration = context.duration
  const durationText = ({ under_3_days: 'Less than 3 days / Chini ya siku 3',
    '3_to_14_days': '3 to 14 days / Siku 3 hadi 14', over_14_days: 'More than 14 days / Zaidi ya siku 14',
    unknown: 'Not sure / Sina uhakika' })[duration?.text] || duration?.text || 'Not reported / Haijatajwa'
  return [
    'RespiraCare — summary to show a health worker / Muhtasari kwa mhudumu wa afya',
    `Reported description / Maelezo: ${inputText || result?.input_text || 'Not recorded'}`,
    `Age / Umri: ${result?.age ?? 'Not recorded'}`,
    `Care priority / Huduma: ${result?.urgency || result?.care_level || 'Not assessed'}`,
    ...Object.entries(context.symptom_states || {}).map(([code, state]) =>
      `${context.symptom_labels?.[code] || code.replaceAll('_', ' ')}: ${state === 'unknown' ? 'uncertain / sina uhakika' : state}`),
    `Duration / Muda: ${durationText}`,
    `Severity / Ukali: ${Object.entries(context.severity || {}).map(([code, value]) => `${context.symptom_labels?.[code] || code.replaceAll('_', ' ')}: ${value}`).join(', ') || 'Not reported / Haijatajwa'}`,
    result?.assessment_summary,
    result?.uncertainty_message,
    result?.health_guidance,
    'Guidance only, not a diagnosis. Not clinically validated for patients in Kenya.',
  ].filter(Boolean).join('\n')
}
