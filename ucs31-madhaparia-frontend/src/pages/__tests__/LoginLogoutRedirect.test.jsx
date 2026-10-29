import {
  fireEvent,
  render,
  screen,
  waitFor,
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

import AppLayout from '../../layouts/AppLayout'
import LoginPage from '../LoginPage'
import { useAuth } from '../../context/useAuth'

vi.mock('../../context/useAuth', () => ({
  useAuth: vi.fn(),
}))

describe('redirect after login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function renderLogin(state) {
    return render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: '/login',
            state,
          },
        ]}
      >
        <Routes>
          <Route
            path="/login"
            element={<LoginPage />}
          />
          <Route
            path="/history"
            element={<div>History page</div>}
          />
          <Route
            path="/dashboard"
            element={<div>Dashboard page</div>}
          />
        </Routes>
      </MemoryRouter>,
    )
  }

  it('returns to the page that was requested', () => {
    useAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        role: 'patient',
      },
    })

    renderLogin({
      from: '/history',
      authenticationRequired: true,
    })

    expect(
      screen.getByText('History page'),
    ).toBeInTheDocument()
  })

  it('uses the dashboard when nothing was requested', () => {
    useAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        role: 'patient',
      },
    })

    renderLogin(undefined)

    expect(
      screen.getByText('Dashboard page'),
    ).toBeInTheDocument()
  })
})

describe('logout', () => {
  it('goes to the home page and then signs out', async () => {
    const logout = vi.fn()

    useAuth.mockReturnValue({
      isAuthenticated: true,
      isAdmin: false,
      user: {
        email: 'patient@example.com',
        role: 'patient',
      },
      logout,
    })

    render(
      <MemoryRouter initialEntries={['/history']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route
              path="/"
              element={<div>Home page</div>}
            />
            <Route
              path="/history"
              element={<div>History page</div>}
            />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Log out',
      }),
    )

    expect(
      await screen.findByText('Home page'),
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(logout).toHaveBeenCalledTimes(1)
    })
  })
})
