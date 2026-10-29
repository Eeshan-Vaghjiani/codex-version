import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import PredictionPage from '../PredictionPage'
import { mapSymptoms, confirmSymptoms } from '../../services/symptoms'
import { createPrediction, savePredictionResult } from '../../services/predictions'

vi.mock('../../services/symptoms', async (original) => ({
  ...await original(), mapSymptoms: vi.fn(), confirmSymptoms: vi.fn(),
}))
vi.mock('../../services/predictions', async (original) => ({
  ...await original(), createPrediction: vi.fn(),
}))
vi.mock('../../components/PredictionFeedback', () => ({ default: () => null }))

const text = 'I feel weak for 3 days'
const questions = [
  ['cough', 'Do you have a cough?'], ['sore_throat', 'Is your throat sore?'],
  ['runny_blocked_nose', 'Is your nose runny or blocked?'],
  ['shortness_of_breath', 'Are you having difficulty breathing now?'],
].map(([code, text_en]) => ({ code, text_en, text_sw: text_en }))
const mapping = { input_text: text, recognised_symptoms: [{ code: 'weakness', status: 'present' }] }
const confirmation = { input_text: text, confirmed_codes: ['weakness'],
  confirmed_symptoms: [{ code: 'weakness', display_name: 'Feeling weak' }] }

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  sessionStorage.setItem('respiracare_symptom_mapping', JSON.stringify(mapping))
  sessionStorage.setItem('respiracare_symptom_confirmation', JSON.stringify(confirmation))
  savePredictionResult({ status: 'assessment_uncertain', confirmed_codes: ['weakness'],
    primary_prediction: null, predictions: [], assessment_context: { language: 'en' },
    decision: { status: 'uncertain', policy_version: 'fixture' },
    discriminator_questions: questions, next_steps: ['Seek review if worsening.'] },
  text, { age: 22, sex: 'M' })
})

function answer(question, value) {
  fireEvent.click(within(screen.getByRole('group', { name: question })).getByRole('radio', { name: value, exact: true }))
}

it('re-maps and server-confirms explicit additions before sending the next prediction', async () => {
  const updatedText = text + '.\nI have a cough.\nI have a sore throat.\nI have a runny or blocked nose.'
  const codes = ['weakness', 'cough', 'sore_throat', 'runny_blocked_nose']
  mapSymptoms.mockResolvedValueOnce({ ...mapping, input_text: updatedText })
  confirmSymptoms.mockResolvedValueOnce({ input_text: updatedText, confirmed_codes: codes,
    confirmed_symptoms: codes.map((code) => ({ code, display_name: code.replaceAll('_', ' ') })) })
  createPrediction.mockResolvedValueOnce({ status: 'needs_follow_up', predictions: [],
    confirmed_codes: codes, follow_up_question: { id: 'breathing_difficulty', text: 'Breathing check', options: [] } })
  render(<MemoryRouter><PredictionPage /></MemoryRouter>)
  questions.slice(0, 3).forEach((question) => answer(question.text_en, 'Yes'))
  fireEvent.click(screen.getByRole('button', { name: 'Submit and re-assess' }))
  await screen.findByRole('heading', { name: 'Complete your information' })
  expect(mapSymptoms).toHaveBeenCalledWith(updatedText)
  expect(confirmSymptoms).toHaveBeenCalledWith(updatedText, codes)
  expect(JSON.parse(sessionStorage.getItem('respiracare_symptom_mapping')).input_text).toBe(updatedText)
  expect(JSON.parse(sessionStorage.getItem('respiracare_symptom_confirmation')).confirmed_codes).toEqual(codes)
  fireEvent.click(screen.getByRole('button', { name: /Generate awareness result/ }))
  await waitFor(() => expect(createPrediction).toHaveBeenCalledWith({ age: 22, sex: 'M', text: updatedText, confirmedCodes: codes }))
})

it('does not corrupt saved text or selections when server confirmation fails', async () => {
  mapSymptoms.mockResolvedValueOnce({ input_text: text + '.\nI have a cough.' })
  confirmSymptoms.mockRejectedValueOnce({ response: { data: { detail: 'Confirmation unavailable.' } } })
  render(<MemoryRouter><PredictionPage /></MemoryRouter>)
  answer('Do you have a cough?', 'Yes')
  fireEvent.click(screen.getByRole('button', { name: 'Submit and re-assess' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Confirmation unavailable.')
  expect(JSON.parse(sessionStorage.getItem('respiracare_symptom_mapping'))).toEqual(mapping)
  expect(JSON.parse(sessionStorage.getItem('respiracare_symptom_confirmation'))).toEqual(confirmation)
  expect(createPrediction).not.toHaveBeenCalled()
})

it('routes a breathing Yes to urgent advice without ordinary reassessment', () => {
  render(<MemoryRouter><PredictionPage /></MemoryRouter>)
  answer('Are you having difficulty breathing now?', 'Yes')
  fireEvent.click(screen.getByRole('button', { name: 'Submit and re-assess' }))
  expect(screen.getByRole('alert')).toHaveTextContent('You reported difficulty breathing')
  expect(mapSymptoms).not.toHaveBeenCalled()
  expect(confirmSymptoms).not.toHaveBeenCalled()
  expect(createPrediction).not.toHaveBeenCalled()
})

it('explains how to recover a stale confirmation instead of displaying raw symptom codes', async () => {
  sessionStorage.removeItem('respiracare_prediction_result')
  sessionStorage.setItem('respiracare_symptom_confirmation', JSON.stringify({
    ...confirmation, confirmed_codes: ['weakness', 'cough'],
  }))
  createPrediction.mockRejectedValueOnce({ response: { status: 400,
    data: { detail: "The following symptom codes were not recognised as present from the submitted text: ['cough']" } } })
  render(<MemoryRouter><PredictionPage /></MemoryRouter>)
  fireEvent.change(screen.getByLabelText('Age'), { target: { value: '22' } })
  fireEvent.change(screen.getByLabelText('Sex'), { target: { value: 'M' } })
  fireEvent.click(screen.getByRole('button', { name: /Generate awareness result/ }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Your saved selections do not match the description')
  expect(screen.getByRole('link', { name: 'Back to confirmation' })).toBeInTheDocument()
})
