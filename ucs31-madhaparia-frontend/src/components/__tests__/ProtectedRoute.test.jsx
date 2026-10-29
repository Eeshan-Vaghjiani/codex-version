import {
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

import ProtectedRoute from '../ProtectedRoute'
import { useAuth } from '../../context/useAuth'

vi.mock('../../context/useAuth', () => ({
  useAuth: vi.fn(),
}))

function renderProtectedRoute() {
  return render(
    <MemoryRouter
      initialEntries={['/history']}
    >
      <Routes>
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <div>Protected content</div>
            </ProtectedRoute>
          }
        />

        <Route
          path="/login"
          element={
            <div>Login page</div>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it(
    'shows the session loading state',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: false,
        loading: true,
      })

      renderProtectedRoute()

      expect(
        screen.getByText(
          'Checking your RespiraCare session...',
        ),
      ).toBeInTheDocument()
    },
  )

  it(
    'redirects unauthenticated users to login',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: false,
        loading: false,
      })

      renderProtectedRoute()

      expect(
        screen.getByText('Login page'),
      ).toBeInTheDocument()
    },
  )

  it(
    'offers a retry instead of logging out when the backend is unreachable',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: false,
        loading: false,
        sessionError:
          'RespiraCare could not connect to the backend.',
        retrySession: vi.fn(),
      })

      renderProtectedRoute()

      expect(
        screen.getByRole('alert'),
      ).toHaveTextContent(
        'could not connect to the backend',
      )

      expect(
        screen.getByRole('button', {
          name: 'Try again',
        }),
      ).toBeInTheDocument()

      expect(
        screen.queryByText('Login page'),
      ).not.toBeInTheDocument()
    },
  )

  it(
    'allows authenticated users to access protected content',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: true,
        loading: false,
      })

      renderProtectedRoute()

      expect(
        screen.getByText(
          'Protected content',
        ),
      ).toBeInTheDocument()
    },
  )
})