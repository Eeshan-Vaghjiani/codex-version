// Patient views require an explicit backend selection decision. Ranked model
// candidates (including historical ones) must never become a primary by position.
export function getPatientPrimary(result) {
  if (result?.status !== 'prediction_complete' || result?.has_red_flag === true ||
      result?.care_level === 'urgent_review' ||
      result?.decision?.status !== 'possible_explanation' ||
      !result?.decision?.policy_version ||
      !result?.primary_prediction?.display_name) return null
  return result.primary_prediction
}

export function hasPatientDecision(result) {
  return Boolean(result?.decision?.policy_version)
}
