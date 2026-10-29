import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import AuthContext from './AuthContextBase'

import {
  AUTH_EXPIRED_EVENT,
  clearAuthToken,
  getAuthToken,
  getCurrentUser,
  hasAuthToken,
  loginPatient,
  saveAuthToken,
} from '../services/auth'

import { getApiErrorMessage } from '../services/api'

export function AuthProvider({
  children,
}) {
  const [user, setUser] =
    useState(null)

  // Only show the loading state when there is
  // a saved token to check.
  const [loading, setLoading] =
    useState(() => hasAuthToken())

  // Set when a saved session could not be
  // checked because the backend could not be
  // reached. The token is kept so the session
  // can be restored once the backend is back.
  const [sessionError, setSessionError] =
    useState('')

  // Increased by retrySession() to check the
  // saved session again.
  const [restoreAttempt, setRestoreAttempt] =
    useState(0)

  useEffect(() => {
    let active = true

    async function restoreSession() {
      if (!getAuthToken()) {
        return
      }

      try {
        const currentUser =
          await getCurrentUser()

        if (!active) {
          return
        }

        setUser(currentUser)
        setSessionError('')
      } catch (error) {
        if (!active) {
          return
        }

        setUser(null)

        // Only a 401 means the token itself is
        // invalid or expired. Other failures (backend
        // down, server error) must not log the user out.
        if (error.response?.status === 401) {
          clearAuthToken()
          setSessionError('')
        } else {
          setSessionError(
            getApiErrorMessage(
              error,
              'RespiraCare could not check your session. Please try again.',
            ),
          )
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    restoreSession()

    return () => {
      active = false
    }
  }, [restoreAttempt])

  function retrySession() {
    setLoading(true)
    setSessionError('')
    setRestoreAttempt(
      (current) => current + 1,
    )
  }

  useEffect(() => {
    function handleExpiredSession() {
      setUser(null)
      setSessionError('')
      setLoading(false)
    }

    window.addEventListener(
      AUTH_EXPIRED_EVENT,
      handleExpiredSession,
    )

    return () => {
      window.removeEventListener(
        AUTH_EXPIRED_EVENT,
        handleExpiredSession,
      )
    }
  }, [])

  async function login(
    email,
    password,
  ) {
    const loginData =
      await loginPatient(
        email,
        password,
      )

    saveAuthToken(
      loginData.access_token,
    )

    try {
      const currentUser =
        await getCurrentUser()

      setUser(currentUser)
      setSessionError('')

      return currentUser
    } catch (error) {
      clearAuthToken()
      setUser(null)

      throw error
    }
  }

  function logout() {
    clearAuthToken()
    setUser(null)
    setSessionError('')
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      sessionError,
      retrySession,
      isAuthenticated:
        Boolean(user),
      isAdmin:
        user?.role === 'admin',
    }),
    [user, loading, sessionError],
  )

  return (
    <AuthContext.Provider
      value={value}
    >
      {children}
    </AuthContext.Provider>
  )
}