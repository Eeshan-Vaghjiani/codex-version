import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import PatientHistoryPage from '../PatientHistoryPage'
import { getPatientHistory } from '../../services/history'
vi.mock('../../services/history', () => ({ getPatientHistory: vi.fn() }))

it('history list presents one backend primary and asks to reassess old rankings', async () => {
  getPatientHistory.mockResolvedValueOnce({ history: [
    { prediction_id: 'new', status: 'prediction_complete', input_text: 'Recent symptom description',
      decision: { status: 'possible_explanation', policy_version: 'current' },
      primary_prediction: { display_name: 'Familiar backend name' },
      predictions: [{ display_name: 'Raw secondary candidate', model_confidence_percent: 88 }],
    },
    { prediction_id: 'old', status: 'prediction_complete', input_text: 'Earlier symptom description',
      predictions: [{ display_name: 'Old alarming ranking', model_confidence_percent: 95 }],
    },
  ] })
  render(<MemoryRouter><PatientHistoryPage /></MemoryRouter>)
  expect(await screen.findByText('Familiar backend name')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'More information needed' })).toBeInTheDocument()
  expect(screen.queryByText('Raw secondary candidate')).not.toBeInTheDocument()
  expect(screen.queryByText('Old alarming ranking')).not.toBeInTheDocument()
  expect(screen.queryByText(/88%|95%/)).not.toBeInTheDocument()
})

