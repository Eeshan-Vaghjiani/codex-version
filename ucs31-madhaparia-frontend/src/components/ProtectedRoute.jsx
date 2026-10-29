import {
  Navigate,
  useLocation,
} from 'react-router-dom'

import { useAuth } from '../context/useAuth'
import SessionUnavailable from './SessionUnavailable'

function ProtectedRoute({ children }) {
  const location = useLocation()

  const {
    isAuthenticated,
    loading,
    retrySession,
    sessionError,
  } = useAuth()

  if (loading) {
    return (
      <div className="auth-loading-page">
        <div className="auth-loading-spinner" />

        <p>
          Checking your RespiraCare session...
        </p>
      </div>
    )
  }

  if (!isAuthenticated && sessionError) {
    return (
      <SessionUnavailable
        message={sessionError}
        onRetry={retrySession}
      />
    )
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location.pathname,
          authenticationRequired: true,
        }}
      />
    )
  }

  return children
}

export default ProtectedRoute