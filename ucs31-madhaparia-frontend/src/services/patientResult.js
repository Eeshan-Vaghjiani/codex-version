// Patient views require an explicit backend selection decision. Ranked model
// candidates (including historical ones) must never become a primary by position.
// The only patient-facing number is the rounded whole-percent match band from
// the backend (match_percent_rounded / match_band). It is a model match, not
// a probability, not a diagnosis, and not overall accuracy. Raw scores stay
// in backend audit diagnostics only and are never rendered here.
export function getPatientPrimary(result) {
  if (result?.status !== 'prediction_complete' || result?.has_red_flag === true ||
      result?.care_level === 'urgent_review' ||
      result?.decision?.status !== 'possible_explanation' ||
      !result?.decision?.policy_version ||
      !(result?.primary_prediction?.display_name || result?.primary_prediction?.dual_name)) return null
  return result.primary_prediction
}

export function getPatientMatch(result) {
  const primary = getPatientPrimary(result)
  if (!primary) return null
  if (typeof primary.match_percent_rounded !== 'number' || !primary.match_band) return null
  return {
    percent_rounded: primary.match_percent_rounded,
    band: primary.match_band,
    label: primary.match_label || 'Model match, not a probability.',
    label_detail: primary.match_label_detail || '',
  }
}

export function hasPatientDecision(result) {
  return Boolean(result?.decision?.policy_version)
}
