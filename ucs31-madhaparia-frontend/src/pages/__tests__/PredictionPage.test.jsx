import {
  render,
  screen,
} from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import {
  beforeEach,
  describe,
  expect,
  it,
} from 'vitest'

import PredictionPage from '../PredictionPage'
import {
  isPredictionForConfirmation,
  savePredictionResult,
} from '../../services/predictions'

const OLD_TEXT = 'I have fever and cough'
const NEW_TEXT = 'I am coughing up blood and I have fever'

const routinePrediction = {
  prediction_id: 'old-routine-id',
  status: 'prediction_complete',
  confirmed_codes: ['cough', 'fever'],
  input_text: OLD_TEXT,
  predictions: [
    {
      rank: 1,
      condition: 'tb',
      display_name: 'Tuberculosis (TB)',
      model_confidence_percent: 96.75,
      description: 'Old routine result',
    },
    {
      rank: 2,
      condition: 'pneumonia',
      display_name: 'Pneumonia',
      model_confidence_percent: 2.1,
      description: 'Second ranked result',
    },
    {
      rank: 3,
      condition: 'bronchitis',
      display_name: 'Bronchitis',
      model_confidence_percent: 1.15,
      description: 'Third ranked result',
    },
  ],
  confidence_explanation: 'Confidence note',
  health_guidance: 'Routine guidance',
  disclaimer: 'Disclaimer text',
}

function saveState({
  text,
  codes,
  safetyStatus,
  prediction,
}) {
  sessionStorage.setItem(
    'respiracare_symptom_mapping',
    JSON.stringify({
      input_text: text,
      recognised_symptoms: [],
      has_red_flag: safetyStatus === 'urgent_review',
    }),
  )

  sessionStorage.setItem(
    'respiracare_symptom_confirmation',
    JSON.stringify({
      input_text: text,
      confirmed_codes: codes,
      confirmed_symptoms: codes.map((code) => ({
        code,
        display_name: code,
      })),
      safety_status: safetyStatus,
    }),
  )

  if (prediction) {
    savePredictionResult(prediction, prediction.input_text)
  }
}

function renderPredictionPage() {
  return render(
    <MemoryRouter>
      <PredictionPage />
    </MemoryRouter>,
  )
}

describe('isPredictionForConfirmation', () => {
  it('matches the same text and codes in any order', () => {
    expect(
      isPredictionForConfirmation(
        routinePrediction,
        OLD_TEXT,
        ['fever', 'cough'],
      ),
    ).toBe(true)
  })

  it('rejects a result made from different text', () => {
    expect(
      isPredictionForConfirmation(
        routinePrediction,
        NEW_TEXT,
        ['cough', 'fever'],
      ),
    ).toBe(false)
  })

  it('rejects a result made from different codes', () => {
    expect(
      isPredictionForConfirmation(
        routinePrediction,
        OLD_TEXT,
        ['fever'],
      ),
    ).toBe(false)
  })

  it('rejects a missing result', () => {
    expect(
      isPredictionForConfirmation(
        null,
        OLD_TEXT,
        ['fever'],
      ),
    ).toBe(false)
  })
})

describe('PredictionPage saved results', () => {
  beforeEach(() => sessionStorage.clear())

  function seed(prediction = routinePrediction, safetyStatus = 'continue') {
    saveState({ text: OLD_TEXT, codes: ['cough', 'fever'], safetyStatus, prediction })
  }
  const selected = { ...routinePrediction,
    decision: { status: 'possible_explanation', policy_version: 'kenya-single-primary-v1' },
    primary_prediction: routinePrediction.predictions[0],
  }

  it('discards an old policy cache before reopening the form', () => {
    seed()
    const old = JSON.parse(sessionStorage.getItem('respiracare_prediction_result'))
    sessionStorage.setItem('respiracare_prediction_result', JSON.stringify({ ...old, cache_version: 'consultation-v3-2026-10-27' }))
    renderPredictionPage()
    expect(screen.getByLabelText('Age')).toBeInTheDocument()
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
  })

  it('displays only the explicit backend primary even if stray candidates exist', () => {
    seed(selected); renderPredictionPage()
    expect(screen.getByText('Tuberculosis (TB)')).toBeInTheDocument()
    expect(screen.queryByText('Pneumonia')).not.toBeInTheDocument()
    expect(screen.queryByText('Bronchitis')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Possible explanation', exact: true })).toBeInTheDocument()
    expect(screen.queryByText(/96.75%|Confidence note|About the model ranking/)).not.toBeInTheDocument()
  })

  it.each([
    routinePrediction,
    { ...selected, primary_prediction: null },
    { ...selected, decision: { status: 'uncertain', policy_version: 'kenya-single-primary-v1' } },
    { ...selected, status: 'assessment_uncertain' },
    { ...selected, status: 'insufficient_evidence' },
  ])('does not invent a primary for an unsupported or unmarked result', (response) => {
    seed(response); renderPredictionPage()
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'More information is needed' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText(/96.75%/)).not.toBeInTheDocument()
  })

  it('keeps urgent guidance ahead of even an explicitly selected primary', () => {
    seed({ ...selected, status: 'urgent_review', health_guidance: 'Seek urgent medical assessment.' })
    renderPredictionPage()
    expect(screen.getByRole('alert')).toHaveTextContent('Seek urgent medical assessment.')
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
  })

  it('does not reuse a routine saved result for a red flag confirmation', () => {
    seed(selected, 'urgent_review'); renderPredictionPage()
    expect(screen.getByLabelText('Age')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
  })

  it('shows a next step once when the guidance paragraph repeats the first bullet', () => {
    const guidance = 'Arrange a medical assessment if symptoms persist.'
    seed({ ...selected, health_guidance: guidance, next_steps: [guidance, 'Seek urgent care for serious warning signs.'] })
    renderPredictionPage()
    expect(screen.getAllByText(guidance)).toHaveLength(1)
  })

  it('explains unused symptom details without treating absent features as negative evidence', () => {
    seed({ ...selected, unsupported_model_features: ['headache'] }); renderPredictionPage()
    expect(screen.getByRole('note', { name: 'Unsupported symptom information' }))
      .toHaveTextContent('This does not mean those symptoms are absent.')
  })
})
