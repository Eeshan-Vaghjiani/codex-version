
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

import SymptomConfirmationPage from '../SymptomConfirmationPage'

vi.mock('../../services/api', async (importOriginal) => {
  const actual = await importOriginal()

  return {
    ...actual,
    default: {
      post: vi.fn(),
    },
  }
})

import api from '../../services/api'

const mapping = {
  input_text: 'I have fever and cough',
  recognised_symptoms: [
    {
      code: 'fever',
      display_name: 'Fever',
      matched_text: 'fever',
      is_red_flag: false,
    },
    {
      code: 'cough',
      display_name: 'Cough',
      matched_text: 'cough',
      is_red_flag: false,
    },
  ],
  has_red_flag: false,
}

function renderConfirmationPage() {
  return render(
    <MemoryRouter>
      <SymptomConfirmationPage />
    </MemoryRouter>,
  )
}

describe('Symptom confirmation workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()

    sessionStorage.setItem(
      'respiracare_symptom_mapping',
      JSON.stringify(mapping),
    )
  })

  it('does not preselect absent or uncertain symptoms as present', async () => {
    sessionStorage.setItem('respiracare_symptom_mapping', JSON.stringify({
      ...mapping, recognised_symptoms: [
        { ...mapping.recognised_symptoms[0], status: 'absent' },
        { ...mapping.recognised_symptoms[1], status: 'present' },
        { code: 'wheezing', display_name: 'Wheezing', status: 'unknown' },
      ],
    }))
    api.post.mockResolvedValueOnce({ data: { confirmed_codes: ['cough'], confirmed_symptoms: [], rejected_symptoms: [] } })
    renderConfirmationPage()
    expect(screen.queryByRole('button', { name: /Fever/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Wheezing/ })).not.toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('Fever: reported absent')
    fireEvent.click(screen.getByRole('button', { name: 'Confirm selected symptoms' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/symptoms/confirm', {
      text: mapping.input_text, confirmed_codes: ['cough'],
    }))
  })

  it('does not select symptoms reported only for another person', () => {
    sessionStorage.setItem('respiracare_symptom_mapping', JSON.stringify({
      ...mapping, recognised_symptoms: [
        { ...mapping.recognised_symptoms[0], status: 'present', reported_subject: 'other_person' },
        { ...mapping.recognised_symptoms[1], status: 'present', reported_subject: 'self' },
      ],
    }))
    renderConfirmationPage()
    expect(screen.queryByRole('button', { name: /Fever/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Cough/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('note')).toHaveTextContent('Fever: reported for another person')
  })

  it('sends only selected symptoms to the backend', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        safety_status: 'safe',
        confirmed_symptoms: [mapping.recognised_symptoms[0]],
        rejected_symptoms: [mapping.recognised_symptoms[1]],
      },
    })

    renderConfirmationPage()

    fireEvent.click(
      screen.getByRole('button', {
        name: /Cough/,
      }),
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Confirm selected symptoms',
      }),
    )

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/symptoms/confirm',
        {
          text: 'I have fever and cough',
          confirmed_codes: ['fever'],
        },
      )
    })

    expect(
      await screen.findByText('Confirmation complete'),
    ).toBeInTheDocument()

    const saved = JSON.parse(
      sessionStorage.getItem(
        'respiracare_symptom_confirmation',
      ),
    )

    expect(saved.confirmed_symptoms).toHaveLength(1)
  })

  it('prevents confirmation when no symptoms are selected', () => {
    renderConfirmationPage()

    fireEvent.click(
      screen.getByRole('button', {
        name: /Fever/,
      }),
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: /Cough/,
      }),
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Confirm selected symptoms',
      }),
    )

    expect(
      screen.getByRole('alert'),
    ).toHaveTextContent(
      'Please confirm at least one symptom',
    )

    expect(api.post).not.toHaveBeenCalled()
  })

  it('shows urgent guidance for a confirmed red flag', async () => {
    const redFlag = {
      code: 'breathing_difficulty',
      display_name: 'Difficulty breathing',
      matched_text: 'difficulty breathing',
      is_red_flag: true,
    }

    sessionStorage.setItem(
      'respiracare_symptom_mapping',
      JSON.stringify({
        input_text: 'I have difficulty breathing',
        recognised_symptoms: [redFlag],
        has_red_flag: true,
      }),
    )

    api.post.mockResolvedValueOnce({
      data: {
        safety_status: 'urgent_review',
        confirmed_symptoms: [redFlag],
        rejected_symptoms: [],
      },
    })

    renderConfirmationPage()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Confirm selected symptoms',
      }),
    )

    expect(
      await screen.findByText(
        'Urgent review recommended',
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        /A confirmed symptom needs prompt attention/,
      ),
    ).toBeInTheDocument()

    expect(api.post).toHaveBeenCalledWith(
      '/symptoms/confirm',
      {
        text: 'I have difficulty breathing',
        confirmed_codes: ['breathing_difficulty'],
      },
    )
  })
})
