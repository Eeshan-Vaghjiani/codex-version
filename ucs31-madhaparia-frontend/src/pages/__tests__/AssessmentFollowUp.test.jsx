import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PredictionPage from '../PredictionPage'
import { createPrediction, savePredictionResult } from '../../services/predictions'

vi.mock('../../services/predictions', async (importOriginal) => ({
  ...await importOriginal(), createPrediction: vi.fn(),
}))
vi.mock('../../components/PredictionFeedback', () => ({ default: () => null }))

const text = 'Nina kikohozi lakini sina homa.'
const question = {
  id: 'duration', text: 'Umekuwa na dalili kwa muda gani?',
  options: [
    { value: 'short', label: 'Chini ya wiki moja' },
    { value: 'long', label: 'Wiki kadhaa' },
    { value: 'unknown', label: 'Sina uhakika' },
  ], rationale: 'Muda wa dalili husaidia kutoa mwongozo.',
}
const pending = {
  status: 'needs_follow_up', confirmed_codes: ['cough'], predictions: [],
  follow_up_question: question, follow_up_answers: [],
  health_guidance: 'Jibu swali hili ukipenda.', disclaimer: 'Huu si utambuzi.',
}
function seed(saved) {
  sessionStorage.setItem('respiracare_symptom_mapping', JSON.stringify({
    input_text: text, recognised_symptoms: [{ code: 'cough', display_name: 'Cough' }],
  }))
  sessionStorage.setItem('respiracare_symptom_confirmation', JSON.stringify({
    input_text: text, confirmed_codes: ['cough'],
    confirmed_symptoms: [{ code: 'cough', display_name: 'Cough' }], safety_status: 'continue',
  }))
  if (saved) savePredictionResult(saved, text, { age: 21, sex: 'F' })
}
function page() {
  return render(<MemoryRouter><PredictionPage /></MemoryRouter>)
}
function continueAssessment() {
  fireEvent.click(screen.getByRole('button', { name: 'Continue / Endelea' }))
}

describe('Targeted assessment follow-ups', () => {
  beforeEach(() => { vi.clearAllMocks(); sessionStorage.clear() })

  it('shows localized numbered options without a disease or feedback', () => {
    seed(pending); page()
    expect(screen.getByRole('heading', { name: question.text })).toBeInTheDocument()
    expect(screen.getByText('A brief follow-up / Swali fupi')).toBeInTheDocument()
    expect(screen.getByLabelText('1. Chini ya wiki moja')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '3. Sina uhakika' })).toBeInTheDocument()
    expect(screen.queryByText('Condition pattern')).not.toBeInTheDocument()
    expect(screen.queryByText('Session reference')).not.toBeInTheDocument()
  })

  it('validates selection before making a request', () => {
    seed(pending); page(); continueAssessment()
    expect(screen.getByRole('alert')).toHaveTextContent('Please choose one of the listed answers')
    expect(createPrediction).not.toHaveBeenCalled()
  })

  it('submits stable question ID and answer with the original demographics and symptoms', async () => {
    seed(pending)
    createPrediction.mockResolvedValueOnce({ ...pending, status: 'insufficient_evidence', follow_up_question: null })
    page()
    fireEvent.click(screen.getByLabelText('2. Wiki kadhaa')); continueAssessment()
    await waitFor(() => expect(createPrediction).toHaveBeenCalledWith({
      age: 21, sex: 'F', text, confirmedCodes: ['cough'],
      followUpAnswers: [{ question_id: 'duration', answer: 'long' }],
    }))
    expect(await screen.findByText('What can help')).toBeInTheDocument()
    const saved = JSON.parse(sessionStorage.getItem('respiracare_prediction_result'))
    expect(saved.request_context).toEqual({ age: 21, sex: 'F' })
  })

  it('appends each answer and resets the selection for the next question', async () => {
    const prior = [{ question_id: 'breathing', answer: 'no' }]
    seed({ ...pending, follow_up_answers: prior })
    createPrediction.mockResolvedValueOnce({ ...pending,
      follow_up_answers: [...prior, { question_id: 'duration', answer: 'short' }],
      follow_up_question: { ...question, id: 'weight_loss', text: 'Have you lost weight?' },
    })
    page(); fireEvent.click(screen.getByLabelText('1. Chini ya wiki moja')); continueAssessment()
    await screen.findByRole('heading', { name: 'Have you lost weight?' })
    expect(createPrediction.mock.calls[0][0].followUpAnswers).toEqual([
      ...prior, { question_id: 'duration', answer: 'short' },
    ])
    expect(screen.getAllByRole('radio').every((radio) => !radio.checked)).toBe(true)
  })

  it('keeps the question available when the backend rejects an answer', async () => {
    seed(pending)
    createPrediction.mockRejectedValueOnce({ response: { status: 422, data: { detail: 'Answer is invalid.' } } })
    page(); fireEvent.click(screen.getByLabelText('3. Sina uhakika')); continueAssessment()
    expect(await screen.findByRole('alert')).toHaveTextContent('Answer is invalid.')
    expect(screen.getByRole('heading', { name: question.text })).toBeInTheDocument()
  })

  it.each(['needs_follow_up', 'insufficient_evidence'])('suppresses stray disease scores for %s', (status) => {
    seed({ ...pending, status, predictions: [{ display_name: 'Unsupported diagnosis', model_confidence_percent: 100 }] })
    page()
    expect(screen.queryByText('Unsupported diagnosis')).not.toBeInTheDocument()
    expect(screen.queryByText('100%')).not.toBeInTheDocument()
  })

  it('prioritizes urgent guidance over a returned follow-up question and disease', () => {
    seed({ ...pending, status: 'urgent_review',
      health_guidance: 'Tafuta huduma ya dharura sasa.',
      predictions: [{ display_name: 'Unsupported diagnosis', model_confidence_percent: 100 }],
    })
    page()
    expect(screen.getByRole('alert')).toHaveTextContent('Tafuta huduma ya dharura sasa.')
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
    expect(screen.queryByText('Unsupported diagnosis')).not.toBeInTheDocument()
  })

  it('treats a red-flag response as urgent even when its status is inconsistent', () => {
    seed({ ...pending, status: 'prediction_complete', has_red_flag: true,
      health_guidance: 'Get urgent medical help now.',
      predictions: [{ display_name: 'Misleading pattern', model_confidence_percent: 100 }],
    })
    page()
    expect(screen.getByRole('alert')).toHaveTextContent('Get urgent medical help now.')
    expect(screen.queryByText('Misleading pattern')).not.toBeInTheDocument()
  })

  it('displays emergency guidance before any demographic form submission', () => {
    seed()
    const mapping = JSON.parse(sessionStorage.getItem('respiracare_symptom_mapping'))
    sessionStorage.setItem('respiracare_symptom_mapping', JSON.stringify({
      ...mapping, has_red_flag: true, health_guidance: 'Get urgent medical help now.',
    }))
    page()
    expect(screen.getByRole('alert')).toHaveTextContent('Get urgent medical help now.')
    expect(createPrediction).not.toHaveBeenCalled()
  })

  it('explains preserved context that the active model cannot learn from', () => {
    seed({ ...pending, status: 'insufficient_evidence',
      assessment_context: {
        context_note: 'Negation and duration are retained for guidance but this model has not learned their effects.',
        duration: { text: 'under_3_days', min_days: 0, max_days: 2 },
      },
    })
    page()
    expect(screen.getByRole('note', { name: 'Assessment context limitations' }))
      .toHaveTextContent('Negation and duration are retained for guidance')
    expect(screen.queryByText('About model confidence')).not.toBeInTheDocument()
    expect(screen.getByText('Duration / Muda: Less than 3 days / Chini ya siku 3')).toBeInTheDocument()
  })

  it('uses numbered backend option labels without duplicating their numbers', () => {
    seed({ ...pending, follow_up_question: { ...question,
      options: [{ value: 'yes', label: '1. Ndiyo' }, { value: 'no', label: '2. Hapana' }],
    } })
    page()
    expect(screen.getByRole('radio', { name: '1. Ndiyo' })).toBeInTheDocument()
    expect(screen.queryByText('1. 1. Ndiyo')).not.toBeInTheDocument()
  })

  it('turns follow-up answers into a backend selected possibility and practical next steps', async () => {
    seed(pending)
    createPrediction.mockResolvedValueOnce({
      status: 'prediction_complete', confirmed_codes: ['cough'], uncertain: true,
      assessment_context: { language: 'en' },
      assessment_summary: 'Several conditions could explain the reported symptoms.',
      decision: { status: 'possible_explanation', policy_version: 'kenya-single-primary-v1' },
      primary_prediction: { condition: 'example', display_name: 'Example possibility',
        supporting_symptoms: ['Cough'], contradicting_symptoms: ['No fever'],
        explanation: 'Explanation supplied by the backend.', model_confidence_percent: 40 },
      uncertainty_message: 'This is a tentative assessment.',
      next_steps: ['Arrange a review if your symptoms persist.'], care_level: 'professional_review',
    })
    page()
    fireEvent.click(screen.getByLabelText('1. Chini ya wiki moja'))
    continueAssessment()
    expect(await screen.findByRole('heading', { name: 'Possible explanation', exact: true })).toBeInTheDocument()
    expect(screen.getByText('Example possibility')).toBeInTheDocument()
    expect(screen.getByText('Several conditions could explain the reported symptoms.')).toBeInTheDocument()
    expect(screen.getByText('Arrange a review if your symptoms persist.')).toBeInTheDocument()
    expect(screen.getByText('Professional review recommended')).toBeInTheDocument()
    expect(screen.queryByText('What can help')).not.toBeInTheDocument()
    expect(screen.queryByText(/40%/)).not.toBeInTheDocument()
  })

  it('prioritizes an urgent care level even if a response includes tentative candidates', () => {
    seed({ ...pending, status: 'prediction_complete', care_level: 'urgent_review',
      predictions: [{ condition: 'example', display_name: 'Example possibility' }],
      health_guidance: 'Get emergency help now.',
    })
    page()
    expect(screen.getByRole('alert')).toHaveTextContent('Get emergency help now.')
    expect(screen.queryByText('Example possibility')).not.toBeInTheDocument()
  })
})
