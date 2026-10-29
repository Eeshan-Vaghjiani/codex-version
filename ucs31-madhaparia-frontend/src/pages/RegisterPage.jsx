
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getApiErrorMessage } from '../services/api'
import { registerPatient } from '../services/auth'

function RegisterPage() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [emailVisited, setEmailVisited] = useState(false)
  const [password, setPassword] = useState('')
  const [passwordVisited, setPasswordVisited] = useState(false)
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const trimmedEmail = email.trim()
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)
  const passwordValid = password.length >= 8
  const passwordsMatch =
    confirmPassword.length > 0 && password === confirmPassword

  // Guidance only: the minimum requirement remains 8 characters.
  const strengthLevel = !password
    ? 0
    : !passwordValid
      ? 1
      : password.length >= 12 &&
          /[a-zA-Z]/.test(password) &&
          /[^a-zA-Z]/.test(password)
        ? 3
        : 2

  const strengthLabels = [
    'Not entered',
    'Below minimum',
    'Meets minimum',
    'Better length and variety',
  ]

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setEmailVisited(true)
    setPasswordVisited(true)

    if (!trimmedEmail) {
      setError('Please enter your email address.')
      return
    }

    if (!emailValid) {
      setError('Please enter a valid email address.')
      return
    }

    if (!passwordValid) {
      setError('Please use a password with at least 8 characters.')
      return
    }

    if (!confirmPassword || !passwordsMatch) {
      setError('The passwords do not match.')
      return
    }

    setLoading(true)

    try {
      await registerPatient(trimmedEmail, password)

      navigate('/login', {
        state: { accountCreated: true },
      })
    } catch (requestError) {
      const status = requestError.response?.status

      if (status === 409) {
        setError('An account with this email already exists.')
      } else if (status === 422) {
        setError('Please check your email and password details.')
      } else {
        setError(
          getApiErrorMessage(
            requestError,
            'Your account could not be created. Please try again.',
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <section
      className="register-page"
      aria-labelledby="register-heading"
    >
      <div className="rc-container">
        <div className="row align-items-center gx-xl-5 gy-5 register-grid">

          {/* Desktop introduction */}
          <div className="col-12 col-lg-6 d-none d-lg-block">
            <div className="register-editorial">
              <p className="register-eyebrow">
                Getting started with RespiraCare
              </p>

              <h2>
                Better understanding begins{' '}
                <span>with your words.</span>
              </h2>

              <p className="register-intro">
                Create an account to describe your symptoms,
                confirm what the system recognises and keep
                your health-awareness history in one place.
              </p>

              <div className="register-benefits">
                <div className="register-benefit">
                  <span aria-hidden="true">01</span>

                  <div>
                    <strong>Describe symptoms naturally</strong>
                    <p>Use English, Kiswahili, or a mix of both.</p>
                  </div>
                </div>

                <div className="register-benefit">
                  <span aria-hidden="true">02</span>

                  <div>
                    <strong>Review before continuing</strong>
                    <p>
                      Check recognised symptoms before
                      receiving guidance.
                    </p>
                  </div>
                </div>
              </div>

              <p className="register-editorial-note">
                This tool supports health awareness.
                It does not provide a medical diagnosis.
              </p>
            </div>
          </div>

          {/* Registration form */}
          <div className="col-12 col-lg-6">
            <div className="register-panel">

              <p className="register-panel-eyebrow">
                Patient registration
              </p>

              <h1 id="register-heading">
                Create your account
              </h1>

              <p className="register-panel-description">
                A few details and you're ready to begin.
              </p>

              {error && (
                <div
                  className="form-message error-message"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <form
                className="register-form"
                onSubmit={handleSubmit}
                noValidate
              >

                {/* Email */}
                <div className="register-field">
                  <label
                    className="form-label"
                    htmlFor="register-email"
                  >
                    Email address
                  </label>

                  <input
                    id="register-email"
                    className="form-control register-input"
                    type="email"
                    inputMode="email"
                    value={email}
                    onChange={(event) => {
                      setEmail(event.target.value)
                      setError('')
                    }}
                    onBlur={() => setEmailVisited(true)}
                    placeholder="you@example.com"
                    autoComplete="email"
                    autoCapitalize="none"
                    spellCheck={false}
                    aria-invalid={emailVisited && !emailValid}
                    aria-describedby="register-email-help"
                    required
                  />

                  <p
                    id="register-email-help"
                    className={`register-field-note ${
                      emailVisited && !emailValid
                        ? 'register-field-note-error'
                        : ''
                    }`}
                  >
                    {emailVisited && !emailValid
                      ? 'Enter a valid email address.'
                      : 'You will use this email to log in.'}
                  </p>
                </div>

                {/* Password */}
                <div className="register-field">
                  <label
                    className="form-label"
                    htmlFor="register-password"
                  >
                    Password
                  </label>

                  <div className="register-password-wrap">
                    <input
                      id="register-password"
                      className="form-control register-input"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(event) => {
                        setPassword(event.target.value)
                        setError('')
                      }}
                      onBlur={() => setPasswordVisited(true)}
                      placeholder="At least 8 characters"
                      autoComplete="new-password"
                      minLength={8}
                      aria-invalid={
                        passwordVisited && !passwordValid
                      }
                      aria-describedby="register-password-help"
                      required
                    />

                    <button
                      className="register-password-toggle"
                      type="button"
                      aria-pressed={showPassword}
                      aria-label={
                        showPassword
                          ? 'Hide password'
                          : 'Show password'
                      }
                      onClick={() =>
                        setShowPassword((current) => !current)
                      }
                    >
                      {showPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>

                  <div
                    className="register-strength-heading"
                    aria-live="polite"
                  >
                    <span>Password feedback</span>
                    <strong>
                      {strengthLabels[strengthLevel]}
                    </strong>
                  </div>

                  <div
                    className="register-strength-bars"
                    aria-hidden="true"
                  >
                    {[1, 2, 3].map((level) => (
                      <span
                        key={level}
                        className={
                          level <= strengthLevel
                            ? 'is-filled'
                            : ''
                        }
                      />
                    ))}
                  </div>

                  <p
                    id="register-password-help"
                    className="register-field-note"
                  >
                    At least 8 characters required.
                    A longer, less predictable password is
                    recommended. This is only a simple estimate.
                  </p>
                </div>

                {/* Confirm password */}
                <div className="register-field">
                  <label
                    className="form-label"
                    htmlFor="register-confirm"
                  >
                    Confirm password
                  </label>

                  <div className="register-password-wrap">
                    <input
                      id="register-confirm"
                      className="form-control register-input"
                      type={
                        showConfirmPassword
                          ? 'text'
                          : 'password'
                      }
                      value={confirmPassword}
                      onChange={(event) => {
                        setConfirmPassword(event.target.value)
                        setError('')
                      }}
                      placeholder="Enter password again"
                      autoComplete="new-password"
                      aria-invalid={
                        confirmPassword.length > 0 &&
                        !passwordsMatch
                      }
                      aria-describedby="register-confirm-help"
                      required
                    />

                    <button
                      className="register-password-toggle"
                      type="button"
                      aria-pressed={showConfirmPassword}
                      aria-label={
                        showConfirmPassword
                          ? 'Hide confirmation password'
                          : 'Show confirmation password'
                      }
                      onClick={() =>
                        setShowConfirmPassword(
                          (current) => !current,
                        )
                      }
                    >
                      {showConfirmPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>

                  <p
                    id="register-confirm-help"
                    className={[
                      'register-field-note',
                      confirmPassword && !passwordsMatch
                        ? 'register-field-note-error'
                        : '',
                      passwordsMatch
                        ? 'register-field-note-valid'
                        : '',
                    ].filter(Boolean).join(' ')}
                    aria-live="polite"
                  >
                    {!confirmPassword
                      ? 'Re-enter your password to confirm it.'
                      : passwordsMatch
                        ? 'Passwords match.'
                        : 'Passwords do not match yet.'}
                  </p>
                </div>

                {/* Patient role notice */}
                <div className="register-role-note">
                  <span aria-hidden="true">✓</span>

                  <p>
                    Registration creates a{' '}
                    <strong>patient account</strong>.
                    Administrator accounts cannot be
                    created here.
                  </p>
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  className="btn btn-primary register-submit"
                  disabled={loading}
                >
                  <span>
                    {loading
                      ? 'Creating account...'
                      : 'Create account'}
                  </span>

                  {!loading && (
                    <span aria-hidden="true">→</span>
                  )}
                </button>
              </form>

              <p className="register-switch">
                Already have an account?{' '}
                <Link to="/login">Log in</Link>
              </p>

              <p className="register-disclaimer">
                RespiraCare provides health-awareness
                information only, not a medical diagnosis.
              </p>

            </div>
          </div>

        </div>
      </div>
    </section>
  )
}

export default RegisterPage
