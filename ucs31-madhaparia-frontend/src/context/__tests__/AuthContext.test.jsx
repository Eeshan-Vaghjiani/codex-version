import {
  fireEvent,
  render,
  screen,
} from '@testing-library/react'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import { AuthProvider } from '../AuthContext'
import { useAuth } from '../useAuth'
import { getCurrentUser } from '../../services/auth'

vi.mock('../../services/auth', async (importOriginal) => {
  const actual = await importOriginal()

  return {
    ...actual,
    getCurrentUser: vi.fn(),
  }
})

const TOKEN_KEY = 'respiracare_access_token'

function SessionState() {
  const {
    loading,
    isAuthenticated,
    retrySession,
    sessionError,
  } = useAuth()

  if (loading) {
    return <p>loading</p>
  }

  return (
    <>
      <p>
        {isAuthenticated
          ? 'signed in'
          : 'signed out'}
        {sessionError
          ? ' / backend unavailable'
          : ''}
      </p>

      <button
        type="button"
        onClick={retrySession}
      >
        Try again
      </button>
    </>
  )
}

function renderProvider() {
  return render(
    <AuthProvider>
      <SessionState />
    </AuthProvider>,
  )
}

describe('AuthProvider session restore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    sessionStorage.setItem(TOKEN_KEY, 'saved-token')
  })

  it('keeps the token when the backend cannot be reached', async () => {
    getCurrentUser.mockRejectedValue({
      code: 'ERR_NETWORK',
      request: {},
    })

    renderProvider()

    expect(
      await screen.findByText(
        'signed out / backend unavailable',
      ),
    ).toBeInTheDocument()

    expect(
      sessionStorage.getItem(TOKEN_KEY),
    ).toBe('saved-token')
  })

  it('clears the token when the backend answers 401', async () => {
    getCurrentUser.mockRejectedValue({
      response: {
        status: 401,
        data: {
          detail: 'Invalid or expired access token.',
        },
      },
    })

    renderProvider()

    expect(
      await screen.findByText('signed out'),
    ).toBeInTheDocument()

    expect(
      sessionStorage.getItem(TOKEN_KEY),
    ).toBeNull()
  })

  it('restores a valid session', async () => {
    getCurrentUser.mockResolvedValue({
      email: 'patient@example.com',
      role: 'patient',
    })

    renderProvider()

    expect(
      await screen.findByText('signed in'),
    ).toBeInTheDocument()
  })

  it('restores the session when retried after the backend returns', async () => {
    getCurrentUser.mockRejectedValueOnce({
      code: 'ERR_NETWORK',
      request: {},
    })

    getCurrentUser.mockResolvedValueOnce({
      email: 'patient@example.com',
      role: 'patient',
    })

    renderProvider()

    await screen.findByText(
      'signed out / backend unavailable',
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Try again',
      }),
    )

    expect(
      await screen.findByText('signed in'),
    ).toBeInTheDocument()
  })
})
