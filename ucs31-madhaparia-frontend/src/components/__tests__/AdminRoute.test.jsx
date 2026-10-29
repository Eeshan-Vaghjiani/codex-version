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

import AdminRoute from '../AdminRoute'
import { useAuth } from '../../context/useAuth'

vi.mock('../../context/useAuth', () => ({
  useAuth: vi.fn(),
}))

function renderAdminRoute() {
  return render(
    <MemoryRouter
      initialEntries={['/admin']}
    >
      <Routes>
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <div>
                Administrator content
              </div>
            </AdminRoute>
          }
        />

        <Route
          path="/login"
          element={
            <div>Login page</div>
          }
        />

        <Route
          path="/access-denied"
          element={
            <div>Access denied page</div>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it(
    'shows the administrator loading state',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: false,
        isAdmin: false,
        loading: true,
      })

      renderAdminRoute()

      expect(
        screen.getByText(
          'Checking administrator access...',
        ),
      ).toBeInTheDocument()
    },
  )

  it(
    'redirects unauthenticated users to login',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: false,
        isAdmin: false,
        loading: false,
      })

      renderAdminRoute()

      expect(
        screen.getByText('Login page'),
      ).toBeInTheDocument()
    },
  )

  it(
    'blocks authenticated patients from administrator pages',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: true,
        isAdmin: false,
        loading: false,
      })

      renderAdminRoute()

      expect(
        screen.getByText(
          'Access denied page',
        ),
      ).toBeInTheDocument()
    },
  )

  it(
    'allows administrators to access administrator pages',
    () => {
      useAuth.mockReturnValue({
        isAuthenticated: true,
        isAdmin: true,
        loading: false,
      })

      renderAdminRoute()

      expect(
        screen.getByText(
          'Administrator content',
        ),
      ).toBeInTheDocument()
    },
  )
})