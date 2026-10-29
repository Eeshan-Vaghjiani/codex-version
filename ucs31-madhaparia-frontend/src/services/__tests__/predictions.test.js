
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import api from '../api'

import {
  createPrediction,
  getSavedPredictionResult,
  savePredictionResult,
} from '../predictions'

vi.mock('../api', () => ({
  default: {
    post: vi.fn(),
  },
}))

const request = {
  age: 25,
  sex: 'M',
  text: 'I have fever na kikohozi',
  confirmedCodes: ['fever', 'cough'],
}

const v1Response = {
  prediction_id: 'v1-session',
  status: 'prediction_complete',
  model_version: '1.0',
  confirmed_codes: ['fever', 'cough'],
  predictions: [
    {
      rank: 1,
      condition: 'Tuberculosis',
      display_name: 'Tuberculosis (TB)',
      model_confidence_percent: 90,
    },
  ],
}

const v2Response = {
  prediction_id: 'v2-session',
  status: 'prediction_complete',
  model_version: 'v2_23class_prototype',
  feature_count: 66,
  confirmed_codes: ['fever', 'cough'],
  predictions: [
    {
      rank: 1,
      condition: 'Tuberculosis',
      display_name: 'Tuberculosis (TB)',
      model_confidence_percent: 72,
    },
  ],
  uncertain: true,
  uncertainty_message:
    'This result has limited certainty.',
  score_note:
    'Model confidence is not a clinical probability.',
  unsupported_model_features: [],
}

describe('Prediction API integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('preserves consultation explanations, evidence and next steps unchanged', async () => {
    const consultation = {
      status: 'prediction_complete', model_version: 'v3_partial_evidence', uncertain: true,
      assessment_summary: 'Several explanations fit the supplied symptoms.',
      next_steps: ['Follow the guidance for persistent symptoms.'], care_level: 'professional_review',
      predictions: [{ condition: 'example', display_name: 'Example explanation',
        supporting_symptoms: ['Cough'], contradicting_symptoms: ['No fever'],
        explanation: 'A learned association.', evidence_note: 'Not a causal conclusion.' }],
    }
    api.post.mockResolvedValueOnce({ data: consultation })
    expect(await createPrediction(request)).toEqual(consultation)
  })

  it('preserves follow-up identifiers, answer values, and response language', async () => {
    api.post.mockResolvedValueOnce({ data: { status: 'needs_follow_up' } })
    await createPrediction({ ...request, language: 'sw',
      followUpAnswers: [{ question_id: 'duration', answer: 'long' }],
    })
    expect(api.post).toHaveBeenCalledWith('/predict', {
      age: 25, sex: 'M', text: request.text, confirmed_codes: request.confirmedCodes,
      language: 'sw', follow_up_answers: [{ question_id: 'duration', answer: 'long' }],
    })
  })

  it('sends the correct prediction request', async () => {
    api.post.mockResolvedValueOnce({
      data: v1Response,
    })

    await createPrediction(request)

    expect(api.post).toHaveBeenCalledWith(
      '/predict',
      {
        age: 25,
        sex: 'M',
        text: 'I have fever na kikohozi',
        confirmed_codes: ['fever', 'cough'],
      },
    )
  })

  it('supports a V1 single prediction response', async () => {
    api.post.mockResolvedValueOnce({
      data: v1Response,
    })

    const result = await createPrediction(request)

    expect(result.model_version).toBe('1.0')
    expect(result.predictions).toHaveLength(1)
  })

  it('preserves all V2 response fields', async () => {
    api.post.mockResolvedValueOnce({
      data: v2Response,
    })

    const result = await createPrediction(request)

    expect(result).toEqual(v2Response)
    expect(result.predictions).toHaveLength(1)
    expect(result.uncertain).toBe(true)
    expect(result.feature_count).toBe(66)
  })

  it('saves the complete V2 prediction result', () => {
    savePredictionResult(
      v2Response,
      request.text,
    )

    const saved = getSavedPredictionResult()

    expect(saved.prediction_id).toBe('v2-session')
    expect(saved.input_text).toBe(request.text)
    expect(saved.uncertain).toBe(true)
    expect(saved.score_note).toBe(v2Response.score_note)
    expect(saved.predictions).toHaveLength(1)
  })

  it('propagates API errors', async () => {
    api.post.mockRejectedValueOnce(
      new Error('Network Error'),
    )

    await expect(
      createPrediction(request),
    ).rejects.toThrow('Network Error')
  })
})


describe('Assessment cache policy migration', () => {
  beforeEach(() => sessionStorage.clear())

  it('discards unversioned predictions instead of treating old model guesses as current', () => {
    sessionStorage.setItem('respiracare_prediction_result', JSON.stringify(v1Response))
    expect(getSavedPredictionResult()).toBeNull()
    expect(sessionStorage.getItem('respiracare_prediction_result')).toBeNull()
  })

  it('discards a cache from a different policy while keeping fresh answers resumable', () => {
    savePredictionResult({ status: 'needs_follow_up', follow_up_answers: [
      { question_id: 'breathing_difficulty', answer: 'no' },
    ] }, request.text, { age: 21, sex: 'M' })
    expect(getSavedPredictionResult().follow_up_answers).toHaveLength(1)
    const stale = JSON.parse(sessionStorage.getItem('respiracare_prediction_result'))
    sessionStorage.setItem('respiracare_prediction_result', JSON.stringify({ ...stale, cache_version: 'old-policy' }))
    expect(getSavedPredictionResult()).toBeNull()
  })
})
