
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import api from '../api'

import {
  getPatientHistory,
  getPatientHistoryItem,
} from '../history'

import {
  submitPredictionFeedback,
} from '../feedback'

vi.mock('../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const historyResponse = {
  count: 2,
  history: [
    {
      prediction_id: 'v2-session',
      status: 'prediction_complete',
      predictions: [
        {
          rank: 1,
          condition: 'Tuberculosis',
          display_name: 'Tuberculosis (TB)',
          model_confidence_percent: 72,
        },
      ],
    },
    {
      prediction_id: 'urgent-session',
      status: 'urgent_review',
      has_red_flag: true,
      predictions: [],
    },
  ],
}

describe('History and feedback API integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('retrieves patient history using the default limit', async () => {
    api.get.mockResolvedValueOnce({
      data: historyResponse,
    })

    const result = await getPatientHistory()

    expect(api.get).toHaveBeenCalledWith(
      '/history',
      {
        params: {
          limit: 20,
        },
      },
    )

    expect(result).toEqual(historyResponse)
    expect(result.history[0].predictions).toHaveLength(1)
  })

  it('supports a custom history limit', async () => {
    api.get.mockResolvedValueOnce({
      data: historyResponse,
    })

    await getPatientHistory(10)

    expect(api.get).toHaveBeenCalledWith(
      '/history',
      {
        params: {
          limit: 10,
        },
      },
    )
  })

  it('retrieves an individual prediction session', async () => {
    const savedSession = historyResponse.history[0]

    api.get.mockResolvedValueOnce({
      data: savedSession,
    })

    const result = await getPatientHistoryItem(
      'v2-session',
    )

    expect(api.get).toHaveBeenCalledWith(
      '/history/v2-session',
    )

    expect(result.predictions).toHaveLength(1)
  })

  it('preserves urgent-review history records', async () => {
    api.get.mockResolvedValueOnce({
      data: historyResponse,
    })

    const result = await getPatientHistory()

    const urgent = result.history[1]

    expect(urgent.status).toBe('urgent_review')
    expect(urgent.has_red_flag).toBe(true)
    expect(urgent.predictions).toEqual([])
  })

  it('submits feedback with a trimmed comment', async () => {
    const feedbackResponse = {
      status: 'feedback_saved',
      prediction_id: 'v2-session',
      was_helpful: true,
    }

    api.post.mockResolvedValueOnce({
      data: feedbackResponse,
    })

    const result = await submitPredictionFeedback({
      predictionId: 'v2-session',
      wasHelpful: true,
      comment: '  Useful information  ',
    })

    expect(api.post).toHaveBeenCalledWith(
      '/feedback',
      {
        prediction_id: 'v2-session',
        was_helpful: true,
        comment: 'Useful information',
      },
    )

    expect(result).toEqual(feedbackResponse)
  })

  it('sends null when the optional comment is blank', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        status: 'feedback_saved',
      },
    })

    await submitPredictionFeedback({
      predictionId: 'v2-session',
      wasHelpful: false,
      comment: '   ',
    })

    expect(api.post).toHaveBeenCalledWith(
      '/feedback',
      {
        prediction_id: 'v2-session',
        was_helpful: false,
        comment: null,
      },
    )
  })
})
