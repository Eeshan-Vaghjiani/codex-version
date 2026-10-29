import { describe, expect, it } from 'vitest'
import { getPatientPrimary } from '../patientResult'

const primary = { condition: 'example', display_name: 'Backend familiar name' }
const selected = { status: 'prediction_complete', primary_prediction: primary,
  decision: { status: 'possible_explanation', policy_version: 'kenya-single-primary-v1' },
  predictions: [{ display_name: 'Stray highest ranked candidate' }],
}

describe('Patient result selection contract', () => {
  it('uses the explicit primary rather than the first model candidate', () => {
    expect(getPatientPrimary(selected)).toBe(primary)
  })
  it.each([
    { ...selected, primary_prediction: null },
    { ...selected, decision: undefined },
    { ...selected, decision: { status: 'possible_explanation' } },
    { ...selected, decision: { status: 'uncertain', policy_version: 'current' } },
    { ...selected, status: 'needs_follow_up' },
    { ...selected, status: 'insufficient_evidence' },
    { ...selected, status: 'assessment_uncertain' },
    { ...selected, status: 'reassessment_required' },
    { ...selected, status: 'urgent_review' },
    { ...selected, has_red_flag: true },
    { ...selected, care_level: 'urgent_review' },
  ])('does not promote scores, unmarked history or an urgent response to a disease result', (result) => {
    expect(getPatientPrimary(result)).toBeNull()
  })
})
