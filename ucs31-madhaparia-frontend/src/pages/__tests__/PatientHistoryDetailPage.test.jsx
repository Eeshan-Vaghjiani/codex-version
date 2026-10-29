
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import PatientHistoryDetailPage from '../PatientHistoryDetailPage'
import { getPatientHistoryItem } from '../../services/history'

vi.mock('../../services/history', () => ({
  getPatientHistoryItem: vi.fn(),
}))

vi.mock('../../components/PredictionFeedback', () => ({
  default: () => null,
}))

const singleSession = {
  prediction_id: 'test-session',
  created_at: '2026-10-23T12:00:00Z',
  age: 25,
  sex: 'M',
  input_text: 'I have fever and cough',
  confirmed_codes: ['fever', 'cough'],
  status: 'prediction_complete',
  has_red_flag: false,
  decision: { status: 'possible_explanation', policy_version: 'kenya-single-primary-v1' },
  predictions: [
    {
      rank: 1,
      condition: 'Tuberculosis',
      display_name: 'Tuberculosis (TB)',
      model_confidence_percent: 72,
      description: 'Example condition information.',
    },
  ],
}

singleSession.primary_prediction = singleSession.predictions[0]

function renderHistoryDetail() {
  return render(
    <MemoryRouter initialEntries={['/history/test-session']}>
      <Routes>
        <Route path="/history/:predictionId" element={<PatientHistoryDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Patient history detail display', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a single condition without ranking', async () => {
    getPatientHistoryItem.mockResolvedValueOnce(singleSession)
    renderHistoryDetail()

    expect(await screen.findByRole('heading', {
      name: 'Saved assessment',
    })).toBeInTheDocument()
    expect(screen.getByText('Tuberculosis (TB)')).toBeInTheDocument()
    expect(screen.queryByText('Rank')).not.toBeInTheDocument()
  })

  it('keeps uncertainty and preserved context visible when legacy response metadata is missing', async () => {
    getPatientHistoryItem.mockResolvedValueOnce({ ...singleSession,
      assessment_context: { context_note: 'Negative evidence was recorded but is not learned by this model.' },
    })
    renderHistoryDetail()
    await screen.findByRole('heading', { name: 'Saved assessment' })
    expect(screen.getByRole('status')).toHaveTextContent('has not been clinically validated')
    expect(screen.getByRole('note', { name: 'Assessment context limitations' }))
      .toHaveTextContent('Negative evidence was recorded')
  })

  it('asks for a new check instead of promoting candidates from an older record', async () => {
    getPatientHistoryItem.mockResolvedValueOnce({
      ...singleSession,
      decision: undefined, primary_prediction: undefined,
      predictions: [
        ...singleSession.predictions,
        {
          rank: 2,
          condition: 'Pneumonia',
          display_name: 'Pneumonia',
          model_confidence_percent: 18,
          description: 'Example older prediction.',
        },
      ],
    })
    renderHistoryDetail()

    expect(await screen.findByRole('heading', {
      name: 'Saved assessment',
    })).toBeInTheDocument()
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
    expect(screen.queryByText('Pneumonia')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Start a new symptom check' })).toBeInTheDocument()
    expect(screen.queryByText('Rank')).not.toBeInTheDocument()
  })

  it('shows urgent guidance without a disease prediction', async () => {
    getPatientHistoryItem.mockResolvedValueOnce({
      ...singleSession,
      status: 'urgent_review',
      has_red_flag: true,
      predictions: [],
    })
    renderHistoryDetail()

    expect(await screen.findByText(/The prediction model was bypassed/i))
      .toBeInTheDocument()
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Saved assessment' })).not.toBeInTheDocument()
  })
})
