
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AdminHistoryDetailPage from '../AdminHistoryDetailPage'
import { getAdminHistoryItem } from '../../services/admin'

vi.mock('../../services/admin', () => ({
  getAdminHistoryItem: vi.fn(),
}))

const singleSession = {
  prediction_id: 'test-session',
  user_id: 'test-user',
  created_at: '2026-10-23T12:00:00Z',
  age: 25,
  sex: 'M',
  input_text: 'I have fever and cough',
  confirmed_codes: ['fever', 'cough'],
  status: 'prediction_complete',
  has_red_flag: false,
  predictions: [{
    rank: 1,
    condition: 'Tuberculosis',
    display_name: 'Tuberculosis (TB)',
    model_confidence_percent: 72,
    description: 'Example condition information.',
  }],
}

function renderAdminHistoryDetail() {
  return render(
    <MemoryRouter initialEntries={['/admin/history/test-session']}>
      <Routes>
        <Route path="/admin/history/:predictionId" element={<AdminHistoryDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Admin history detail display', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows a single saved condition without ranking', async () => {
    getAdminHistoryItem.mockResolvedValueOnce(singleSession)
    renderAdminHistoryDetail()
    expect(await screen.findByRole('heading', { name: 'Saved possible explanations' }))
      .toBeInTheDocument()
    expect(screen.getByText('Tuberculosis (TB)')).toBeInTheDocument()
    expect(screen.queryByText('Rank')).not.toBeInTheDocument()
  })

  it('keeps caution and context visible when legacy response metadata is missing', async () => {
    getAdminHistoryItem.mockResolvedValueOnce({ ...singleSession,
      assessment_context: { context_note: 'Duration remains preserved for guidance.' },
    })
    renderAdminHistoryDetail()
    await screen.findByRole('heading', { name: 'Saved possible explanations' })
    expect(screen.getByRole('status')).toHaveTextContent('has not been clinically validated')
    expect(screen.getByRole('note', { name: 'Assessment context limitations' }))
      .toHaveTextContent('Duration remains preserved')
  })

  it('preserves competing possibilities in older records', async () => {
    getAdminHistoryItem.mockResolvedValueOnce({
      ...singleSession,
      predictions: [
        ...singleSession.predictions,
        {
          rank: 2,
          condition: 'Pneumonia',
          display_name: 'Pneumonia',
          model_confidence_percent: 18,
          description: 'Older prediction.',
        },
      ],
    })
    renderAdminHistoryDetail()
    expect(await screen.findByRole('heading', { name: 'Saved possible explanations' }))
      .toBeInTheDocument()
    expect(screen.getByText('Tuberculosis (TB)')).toBeInTheDocument()
    expect(screen.getByText('Pneumonia')).toBeInTheDocument()
    expect(screen.queryByText('Rank')).not.toBeInTheDocument()
  })

  it('shows urgent guidance without a prediction', async () => {
    getAdminHistoryItem.mockResolvedValueOnce({
      ...singleSession,
      status: 'urgent_review',
      has_red_flag: true,
      predictions: [],
    })
    renderAdminHistoryDetail()
    expect(await screen.findByText(/The prediction model was bypassed/i))
      .toBeInTheDocument()
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
  })

  it('does not show a disease when status alone indicates urgent review', async () => {
    getAdminHistoryItem.mockResolvedValueOnce({
      ...singleSession,
      status: 'urgent_review',
      has_red_flag: false,
    })
    renderAdminHistoryDetail()
    expect(await screen.findByText(/The prediction model was bypassed/i))
      .toBeInTheDocument()
    expect(screen.queryByText('Tuberculosis (TB)')).not.toBeInTheDocument()
  })
})
