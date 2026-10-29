import {
  fireEvent,
  render,
  screen,
} from '@testing-library/react'
import {
  MemoryRouter,
  Route,
  Routes,
} from 'react-router-dom'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import LoginPage from '../LoginPage'
import PatientHistoryDetailPage from '../PatientHistoryDetailPage'
import { useAuth } from '../../context/useAuth'
import { getPatientHistoryItem } from '../../services/history'

vi.mock('../../context/useAuth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../../services/history', () => ({
  getPatientHistoryItem: vi.fn(),
}))

// The shape FastAPI uses for a 422 response.
const validationError = {
  response: {
    status: 422,
    data: {
      detail: [
        {
          type: 'uuid_parsing',
          loc: ['path', 'prediction_id'],
          msg: 'Input should be a valid UUID',
          input: 'not-a-uuid',
        },
      ],
    },
  },
}

describe('pages with a 422 validation list', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('login shows a message instead of crashing', async () => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      login: vi.fn().mockRejectedValue(
        validationError,
      ),
    })

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    fireEvent.change(
      screen.getByPlaceholderText('you@example.com'),
      {
        target: {
          value: 'someone@localhost',
        },
      },
    )

    fireEvent.change(
      screen.getByPlaceholderText('Enter your password'),
      {
        target: {
          value: 'abc',
        },
      },
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Log in',
      }),
    )

    expect(
      await screen.findByText(
        'Please check your email address and password.',
      ),
    ).toBeInTheDocument()
  })

  it('history detail treats an invalid id as not found', async () => {
    useAuth.mockReturnValue({})

    getPatientHistoryItem.mockRejectedValue(
      validationError,
    )

    render(
      <MemoryRouter
        initialEntries={['/history/not-a-uuid']}
      >
        <Routes>
          <Route
            path="/history/:predictionId"
            element={<PatientHistoryDetailPage />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(
      await screen.findByText(
        'This prediction session could not be found.',
      ),
    ).toBeInTheDocument()
  })

  it('history detail turns other error lists into text', async () => {
    getPatientHistoryItem.mockRejectedValue({
      response: {
        status: 500,
        data: {
          detail: [
            {
              msg: 'Something unexpected happened',
            },
          ],
        },
      },
    })

    render(
      <MemoryRouter
        initialEntries={['/history/abc']}
      >
        <Routes>
          <Route
            path="/history/:predictionId"
            element={<PatientHistoryDetailPage />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(
      await screen.findByText(
        'Something unexpected happened',
      ),
    ).toBeInTheDocument()
  })
})
