import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PredictionPage from '../PredictionPage'
import SymptomInputPage from '../SymptomInputPage'
import HomePage from '../HomePage'
import { savePredictionResult } from '../../services/predictions'
import { getPatientMatch } from '../../services/patientResult'
import { mapSymptoms } from '../../services/symptoms'

vi.mock('../../services/symptoms', async (importOriginal) => ({
  ...await importOriginal(), mapSymptoms: vi.fn(),
}))

const text = 'I have cough, no fever and maybe headache for two days'
const primary = { display_name: 'Chest infection (bronchitis)', condition: 'Bronchitis',
  model_match_percent: 71, match_band: 'moderate', score_kind: 'v3_relative_model_match' }
const result = { status: 'prediction_complete', input_text: text, confirmed_codes: ['cough'],
  primary_prediction: primary, predictions: [primary],
  decision: { status: 'possible_explanation', policy_version: 'presentation-fixture-only' },
  assessment_context: { symptom_states: { cough: 'present', fever: 'absent', headache: 'unknown' },
    duration: { text: 'two days' }, severity: { cough: 'mild' } },
  disclaimer: 'Guidance only, not a diagnosis.', health_guidance: 'Monitor and seek review if worsening.',
}

function seed(response = result) {
  sessionStorage.setItem('respiracare_symptom_mapping', JSON.stringify({ input_text: text }))
  sessionStorage.setItem('respiracare_symptom_confirmation', JSON.stringify({ confirmed_codes: ['cough'] }))
  savePredictionResult(response, text, { age: 24, sex: 'F' })
}
function page() {
  render(<MemoryRouter initialEntries={['/prediction']}><Routes>
    <Route path="/prediction" element={<PredictionPage />} />
    <Route path="/symptoms" element={<SymptomInputPage />} />
  </Routes></MemoryRouter>)
}

describe('Patient safety presentation', () => {
  beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks() })
  it('shows one V3 whole-percent match with honest labels and care first', () => {
    seed(); page()
    expect(screen.getByText(/Model match: 71% — Moderate match/)).toBeInTheDocument()
    expect(screen.getByText(/not a probability, not a diagnosis, not overall accuracy/)).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(1)
    const care = screen.getByText(/Care priority:/)
    const name = screen.getByRole('heading', { name: primary.display_name })
    expect(care.compareDocumentPosition(name) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
  it('shows duration, severity and present / absent / uncertain on the result itself', () => {
    seed(); page()
    expect(screen.getByText('cough: present')).toBeInTheDocument()
    expect(screen.getByText('fever: absent')).toBeInTheDocument()
    expect(screen.getByText(/headache: uncertain/, { selector: 'li' })).toBeInTheDocument()
    expect(screen.getByText(/Duration \/ Muda: two days/, { selector: 'li' })).toBeInTheDocument()
    expect(screen.getByText(/Severity \/ Ukali: cough: mild/, { selector: 'li' })).toBeInTheDocument()
    expect(screen.getByText(/COVID is not one of the conditions/)).toBeInTheDocument()
    expect(screen.getByText(/V3 partial-evidence: 21 conditions/)).toBeInTheDocument()
  })
  it('rechecks corrections from the result, clears old result and reopens confirmation flow', async () => {
    seed(); page()
    const corrected = 'I have fever, no cough for three weeks'
    mapSymptoms.mockResolvedValueOnce({ input_text: corrected, recognised_symptoms: [
      { code: 'fever', display_name: 'Fever', status: 'present' },
    ], unmatched_wording: [], has_red_flag: false })
    fireEvent.change(screen.getByLabelText(/Correct symptoms, duration or severity/), { target: { value: corrected } })
    fireEvent.click(screen.getByRole('button', { name: /Recheck corrections/ }))
    expect(await screen.findByLabelText('Symptom description')).toHaveValue(corrected)
    expect(mapSymptoms).toHaveBeenCalledWith(corrected)
    expect(sessionStorage.getItem('respiracare_prediction_result')).toBeNull()
    expect(sessionStorage.getItem('respiracare_symptom_confirmation')).toBeNull()
  })
  it.each(['urgent_review', 'assessment_uncertain', 'insufficient_evidence'])('never shows a name or score for %s', (status) => {
    seed({ ...result, status }); page()
    expect(screen.queryByText(primary.display_name)).not.toBeInTheDocument()
    expect(screen.queryByText(/71%/)).not.toBeInTheDocument()
  })
  it('does not convert legacy or malformed scores into a V3 match', () => {
    expect(getPatientMatch({ model_confidence_percent: 96.75 })).toBeNull()
    for (const value of [71.2, '71', NaN, Infinity, -1, 101]) {
      expect(getPatientMatch({ ...primary, model_match_percent: value })).toBeNull()
    }
    expect(getPatientMatch(primary)).toBe('71%')
  })
  it('copies a patient-controlled handover summary without ranked candidates', async () => {
    const writeText = vi.fn().mockResolvedValue()
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    seed(); page()
    fireEvent.click(screen.getByRole('button', { name: /Copy summary/ }))
    expect(await screen.findByText(/Copied. Only share/)).toBeInTheDocument()
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('headache: uncertain'))
    expect(writeText.mock.calls[0][0]).not.toMatch(/model_confidence_percent|raw_relative_score|71%/)
    expect(writeText.mock.calls[0][0]).toContain('not a diagnosis')
  })
  it('keeps the handover readable when clipboard permission is denied', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
      writeText: vi.fn().mockRejectedValue(new Error('Permission denied')),
    } })
    seed(); page()
    fireEvent.click(screen.getByRole('button', { name: /Copy summary/ }))
    expect(await screen.findByText(/Copy is unavailable/)).toBeInTheDocument()
  })
  it('makes the HomePage promise conditional on the checked selection rules', () => {
    render(<MemoryRouter><HomePage /></MemoryRouter>)
    expect(screen.getByText(/Names are withheld when the information or independently checked selection rules/)).toBeInTheDocument()
    expect(screen.queryByText(/see one predicted condition and its confidence information/)).not.toBeInTheDocument()
  })
})
