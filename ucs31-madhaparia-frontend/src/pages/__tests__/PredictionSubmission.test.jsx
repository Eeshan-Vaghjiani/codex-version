
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'

import { MemoryRouter } from 'react-router-dom'

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import PredictionPage from '../PredictionPage'

import {
  createPrediction,
} from '../../services/predictions'

vi.mock('../../services/predictions', async (importOriginal) => {
  const actual = await importOriginal()

  return {
    ...actual,
    createPrediction: vi.fn(),
  }
})

vi.mock('../../components/PredictionFeedback', () => ({
  default: () => null,
}))

const inputText = 'I have fever and cough'

const predictionResponse = {
  prediction_id: 'test-prediction',
  status: 'prediction_complete',
  confirmed_codes: ['fever', 'cough'],
  predictions: [
    {
      rank: 1,
      condition: 'tb',
      display_name: 'Tuberculosis (TB)',
      model_confidence_percent: 72,
      description: 'Example condition information.',
    },
  ],
  confidence_explanation: 'Model confidence explanation.',
  health_guidance: 'Consult a healthcare professional.',
  disclaimer: 'This is not a medical diagnosis.',
}

predictionResponse.primary_prediction = predictionResponse.predictions[0]
predictionResponse.decision = { status: 'possible_explanation', policy_version: 'kenya-single-primary-v1' }

function prepareSession() {
  sessionStorage.setItem(
    'respiracare_symptom_mapping',
    JSON.stringify({
      input_text: inputText,
      recognised_symptoms: [
        {
          code: 'fever',
          display_name: 'Fever',
        },
        {
          code: 'cough',
          display_name: 'Cough',
        },
      ],
      has_red_flag: false,
    }),
  )

  sessionStorage.setItem(
    'respiracare_symptom_confirmation',
    JSON.stringify({
      input_text: inputText,
      confirmed_codes: ['fever', 'cough'],
      confirmed_symptoms: [
        {
          code: 'fever',
          display_name: 'Fever',
        },
        {
          code: 'cough',
          display_name: 'Cough',
        },
      ],
      safety_status: 'continue',
    }),
  )
}

function renderPage() {
  return render(
    <MemoryRouter>
      <PredictionPage />
    </MemoryRouter>,
  )
}

function fillValidDetails() {
  fireEvent.change(screen.getByLabelText('Age'), {
    target: { value: '25' },
  })

  fireEvent.change(screen.getByLabelText('Sex'), {
    target: { value: 'M' },
  })
}

describe('Prediction submission workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    prepareSession()
  })

  it('submits confirmed symptoms and displays the result', async () => {
    createPrediction.mockResolvedValueOnce(predictionResponse)

    renderPage()
    fillValidDetails()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Generate awareness result',
      }),
    )

    await waitFor(() => {
      expect(createPrediction).toHaveBeenCalledWith({
        age: 25,
        sex: 'M',
        text: inputText,
        confirmedCodes: ['fever', 'cough'],
      })
    })

    expect(
      await screen.findByText('Tuberculosis (TB)'),
    ).toBeInTheDocument()

    const saved = JSON.parse(
      sessionStorage.getItem('respiracare_prediction_result'),
    )

    expect(saved.prediction_id).toBe('test-prediction')
    expect(saved.input_text).toBe(inputText)
    expect(saved.predictions).toHaveLength(1)
  })

  it('prevents submission with an invalid age', () => {
    renderPage()

    fireEvent.change(screen.getByLabelText('Age'), {
      target: { value: '150' },
    })

    fireEvent.change(screen.getByLabelText('Sex'), {
      target: { value: 'M' },
    })

    fireEvent.submit(
      screen.getByRole('button', {
        name: 'Generate awareness result',
      }).closest('form'),
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Please enter a valid age between 0 and 120.',
    )

    expect(createPrediction).not.toHaveBeenCalled()
  })

  it('shows an error when the login session has expired', async () => {
    createPrediction.mockRejectedValueOnce({
      response: {
        status: 401,
      },
    })

    renderPage()
    fillValidDetails()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Generate awareness result',
      }),
    )

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent(
      'Your login session is no longer valid. Please log in again.',
    )

    expect(
      screen.queryByText('Tuberculosis (TB)'),
    ).not.toBeInTheDocument()
  })

  it('submits a red-flag case and shows urgent guidance', async () => {
    const redFlagText = 'I am coughing up blood'

    sessionStorage.setItem(
      'respiracare_symptom_mapping',
      JSON.stringify({
        input_text: redFlagText,
        recognised_symptoms: [
          {
            code: 'coughing_blood',
            display_name: 'Coughing up blood',
            is_red_flag: true,
          },
        ],
        has_red_flag: true,
      }),
    )

    sessionStorage.setItem(
      'respiracare_symptom_confirmation',
      JSON.stringify({
        input_text: redFlagText,
        confirmed_codes: ['coughing_blood'],
        confirmed_symptoms: [
          {
            code: 'coughing_blood',
            display_name: 'Coughing up blood',
            is_red_flag: true,
          },
        ],
        safety_status: 'urgent_review',
      }),
    )

    createPrediction.mockResolvedValueOnce({
      prediction_id: 'urgent-test',
      status: 'urgent_review',
      has_red_flag: true,
      confirmed_codes: ['coughing_blood'],
      predictions: [],
      health_guidance: 'Seek urgent medical assessment.',
      disclaimer: 'This is not a medical diagnosis.',
    })

    renderPage()
    fillValidDetails()

    expect(
      screen.getByText('Safety-sensitive symptom confirmed'),
    ).toBeInTheDocument()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Continue safety review',
      }),
    )

    await waitFor(() => {
      expect(createPrediction).toHaveBeenCalledWith({
        age: 25,
        sex: 'M',
        text: redFlagText,
        confirmedCodes: ['coughing_blood'],
      })
    })

    expect(
      await screen.findByText('Seek urgent medical assessment.'),
    ).toBeInTheDocument()

    expect(
      screen.queryByText('Tuberculosis (TB)'),
    ).not.toBeInTheDocument()

    const saved = JSON.parse(
      sessionStorage.getItem('respiracare_prediction_result'),
    )

    expect(saved.status).toBe('urgent_review')
    expect(saved.predictions).toEqual([])
  })
})
