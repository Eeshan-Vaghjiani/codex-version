import {
  act,
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

import SymptomInputPage from '../SymptomInputPage'

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

function renderSymptomInputPage() {
  return render(
    <MemoryRouter>
      <SymptomInputPage />
    </MemoryRouter>,
  )
}

function analyse(text) {
  renderSymptomInputPage()

  fireEvent.change(
    screen.getByLabelText('Symptom description'),
    {
      target: {
        value: text,
      },
    },
  )

  fireEvent.click(
    screen.getByRole('button', {
      name: 'Analyse symptoms',
    }),
  )
}

describe('SymptomInputPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('ignores an analysis response when the user has changed the description', async () => {
    let resolveRequest
    api.post.mockImplementationOnce(() => new Promise((resolve) => { resolveRequest = resolve }))
    analyse('I have fever')
    fireEvent.change(screen.getByLabelText('Symptom description'), {
      target: { value: 'Nina kikohozi' },
    })
    await act(async () => resolveRequest({ data: {
      input_text: 'I have fever', recognised_symptoms: [{ code: 'fever', display_name: 'Fever' }],
    } }))
    expect(screen.queryByText('Fever')).not.toBeInTheDocument()
    expect(sessionStorage.getItem('respiracare_symptom_mapping')).toBeNull()
  })

  it('shows urgent guidance before confirmation and does not offer the questionnaire', async () => {
    api.post.mockResolvedValueOnce({ data: {
      input_text: 'Nashindwa kupumua', has_red_flag: true,
      health_guidance: 'Tafuta huduma ya dharura sasa.',
      recognised_symptoms: [{ code: 'breathing_difficulty', display_name: 'Difficulty breathing', status: 'present' }],
    } })
    analyse('Nashindwa kupumua')
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Tafuta huduma ya dharura sasa.')
    expect(alert).toHaveFocus()
    expect(screen.queryByText('Continue to confirmation')).not.toBeInTheDocument()
  })

  it('shows absent symptoms and extracted duration and severity distinctly', async () => {
    api.post.mockResolvedValueOnce({ data: {
      input_text: 'Mild cough for two days, no fever',
      recognised_symptoms: [
        { code: 'cough', display_name: 'Cough', status: 'present', duration_text: 'two days', severity: 'mild' },
        { code: 'fever', display_name: 'Fever', status: 'absent' },
      ],
    } })
    analyse('Mild cough for two days, no fever')
    expect(await screen.findByText('Reported absent / Haipo')).toBeInTheDocument()
    expect(screen.getByText('Duration: two days.')).toBeInTheDocument()
    expect(screen.getByText('Severity: mild.')).toBeInTheDocument()
  })

  it('shows symptom wording for confirmation without text-match percentages', async () => {
    api.post.mockResolvedValueOnce({ data: {
      input_text: 'cogh', recognised_symptoms: [{ code: 'cough', display_name: 'Cough',
        matched_text: 'cogh', language: 'en', match_type: 'fuzzy', match_score: 92 }],
      unmatched_wording: [{ unmatched_text: 'unclear', suggestions: [{ code: 'fever',
        suggested_alias: 'fever', language: 'en', score: 77 }] }],
    } })
    analyse('cogh')
    expect(await screen.findByText('Please confirm this symptom')).toBeInTheDocument()
    expect(screen.queryByText(/92%|77%|Fuzzy match/)).not.toBeInTheDocument()
  })

  it(
    'clears an older prediction result when new symptoms are analysed',
    async () => {
      sessionStorage.setItem(
        'respiracare_prediction_result',
        JSON.stringify({
          prediction_id: 'old-id',
        }),
      )

      api.post.mockResolvedValue({
        data: {
          input_text: 'nina homa',
          recognised_symptoms: [
            {
              code: 'fever',
              display_name: 'Fever',
              matched_text: 'homa',
              language: 'sw',
              match_type: 'exact',
              match_score: 100,
              is_red_flag: false,
            },
          ],
          unmatched_wording: [],
          has_red_flag: false,
        },
      })

      analyse('nina homa')

      await screen.findByText('Fever')

      expect(
        sessionStorage.getItem(
          'respiracare_prediction_result',
        ),
      ).toBeNull()
    },
  )

  it(
    'does not offer confirmation when nothing was recognised',
    async () => {
      api.post.mockResolvedValue({
        data: {
          input_text: 'my knee itches',
          recognised_symptoms: [],
          unmatched_wording: [],
          has_red_flag: false,
        },
      })

      analyse('my knee itches')

      await screen.findByText(
        'No supported symptoms were recognised',
      )

      expect(
        screen.queryByText(
          'Continue to confirmation',
        ),
      ).not.toBeInTheDocument()
    },
  )

  it(
    'shows a readable message for a validation error list',
    async () => {
      api.post.mockRejectedValue({
        response: {
          status: 422,
          data: {
            detail: [
              {
                type: 'string_too_long',
                loc: ['body', 'text'],
                msg: 'String should have at most 2000 characters',
              },
            ],
          },
        },
      })

      analyse('fever')

      await waitFor(() => {
        expect(
          screen.getByRole('alert'),
        ).toHaveTextContent(
          'Please check your symptom description',
        )
      })
    },
  )
})
