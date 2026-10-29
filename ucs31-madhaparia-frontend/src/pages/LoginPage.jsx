
import { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '../context/useAuth'
import { getApiErrorMessage } from '../services/api'

function LoginPage() {
  const location = useLocation()
  const { isAuthenticated, login, user } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const accountCreated = location.state?.accountCreated
  const authenticationRequired = location.state?.authenticationRequired

  // Keep existing role-based and requested-page redirects.
  if (isAuthenticated) {
    const requestedRoute = location.state?.from
    const defaultRoute = user?.role === 'admin' ? '/admin' : '/dashboard'

    return <Navigate to={requestedRoute || defaultRoute} replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!email.trim() || !password) {
      setError('Please enter your email address and password.')
      return
    }

    setLoading(true)

    try {
      await login(email.trim(), password)
    } catch (requestError) {
      const status = requestError.response?.status

      if (status === 401) {
        setError('The email or password you entered is incorrect.')
      } else if (status === 422) {
        setError('Please check your email address and password.')
      } else {
        setError(
          getApiErrorMessage(
            requestError,
            'Login could not be completed. Please try again.',
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="login-page" aria-labelledby="login-heading">
      <div className="rc-container">
        <div className="row align-items-center gx-xl-5 gy-5 login-grid">

          {/* Introduction */}
            <div className="col-12 col-lg-6 order-2 order-lg-1 d-none d-lg-block">            <div className="login-editorial">

              <p className="login-eyebrow">
                Your RespiraCare account
              </p>

              <h1 id="login-heading">
                Your health awareness,
                <span> right where you left off.</span>
              </h1>

              <p className="login-intro">
                Sign in to revisit earlier symptom checks or start a new one.
                Everything is organised in one place, at your own pace.
              </p>

              <div
                className="login-benefits"
                aria-label="What you can do after signing in"
              >
                <div className="login-benefit">
                  <span className="login-benefit-number" aria-hidden="true">
                    01
                  </span>

                  <div>
                    <strong>Pick up where you left off</strong>
                    <p>
                      Review your previous health-awareness sessions.
                    </p>
                  </div>
                </div>

                <div className="login-benefit">
                  <span className="login-benefit-number" aria-hidden="true">
                    02
                  </span>

                  <div>
                    <strong>Describe symptoms naturally</strong>
                    <p>
                      Use English, Kiswahili, or a mix of both.
                    </p>
                  </div>
                </div>
              </div>

              <p className="login-editorial-note">
                Your account history is only accessible through an
                authorised session.
              </p>

            </div>
          </div>

          {/* Login form */}
          <div className="col-12 col-lg-6 order-1 order-lg-2">
            <div className="login-panel">

              <p className="login-panel-eyebrow">
                Account access
              </p>

              <h2>Log in</h2>

              <p className="login-panel-description">
                Welcome back. Enter your details below.
              </p>

              {accountCreated && (
                <div
                  className="form-message success-message"
                  role="status"
                >
                  Your account was created successfully. You can now log in.
                </div>
              )}

              {authenticationRequired && (
                <div
                  className="form-message info-message"
                  role="status"
                >
                  Please log in to access that page.
                </div>
              )}

              {error && (
                <div
                  className="form-message error-message"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <form className="login-form" onSubmit={handleSubmit}>

                <div className="login-field">
                  <label
                    className="form-label"
                    htmlFor="login-email"
                  >
                    Email address
                  </label>

                  <input
                    id="login-email"
                    className="form-control login-input"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                    autoComplete="email"
                    required
                  />
                </div>

                <div className="login-field">
                  <label
                    className="form-label"
                    htmlFor="login-password"
                  >
                    Password
                  </label>

                  <div className="login-password-wrap">
                    <input
                      id="login-password"
                      className="form-control login-input"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="Enter your password"
                      autoComplete="current-password"
                      required
                    />

                    <button
                      className="login-password-toggle"
                      type="button"
                      aria-pressed={showPassword}
                      aria-label={
                        showPassword ? 'Hide password' : 'Show password'
                      }
                      onClick={() =>
                        setShowPassword((current) => !current)
                      }
                    >
                      {showPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn btn-primary login-submit"
                  disabled={loading}
                >
                  <span>{loading ? 'Logging in...' : 'Log in'}</span>
                  {!loading && <span aria-hidden="true">→</span>}
                </button>

              </form>

              <p className="login-register">
                New to RespiraCare?{' '}
                <Link to="/register">Create an account</Link>
              </p>

              <p className="login-disclaimer">
                For health awareness and education only.
                RespiraCare does not provide a medical diagnosis.
              </p>

            </div>
          </div>

        </div>
      </div>
    </section>
  )
}

export default LoginPage
