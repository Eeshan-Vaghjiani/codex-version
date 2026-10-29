
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import {
  clearSymptomConfirmation,
  confirmSymptoms,
  getSavedSymptomMapping,
  saveSymptomConfirmation,
} from '../services/symptoms'

import { clearPredictionResult } from '../services/predictions'
import { getApiErrorMessage } from '../services/api'

function SymptomConfirmationPage() {
  const mapping = getSavedSymptomMapping()
  const recognised = mapping?.recognised_symptoms || []
  const present = recognised.filter((symptom) =>
    (!symptom.status || symptom.status === 'present') && symptom.reported_subject !== 'other_person')
  const otherMentions = recognised.filter((symptom) =>
    symptom.reported_subject === 'other_person' || (symptom.status && symptom.status !== 'present'))

  const [selectedCodes, setSelectedCodes] = useState(
    () => present.map((symptom) => symptom.code),
  )
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!mapping) {
    return <Navigate to="/symptoms" replace />
  }

  function toggleSymptom(code) {
    setError('')
    setResult(null)

    clearSymptomConfirmation()
    clearPredictionResult()

    setSelectedCodes((current) =>
      current.includes(code)
        ? current.filter((item) => item !== code)
        : [...current, code],
    )
  }

  async function handleConfirmation() {
    setError('')

    if (selectedCodes.length === 0) {
      setError(
        'Please confirm at least one symptom or return to the previous step and revise your description.',
      )
      return
    }

    setLoading(true)
    clearPredictionResult()
    clearSymptomConfirmation()

    try {
      const confirmation = await confirmSymptoms(
        mapping.input_text,
        selectedCodes,
      )

      setResult(confirmation)
      saveSymptomConfirmation(confirmation)
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          'Your symptoms could not be confirmed. Please try again.',
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  function handleReviewAgain() {
    setResult(null)
    setError('')
    clearSymptomConfirmation()
    clearPredictionResult()
  }

  const confirmed = result?.confirmed_symptoms || []
  const rejected = result?.rejected_symptoms || []
  const isUrgent = result?.safety_status === 'urgent_review'

  return (
    <section
      className="sym33-page"
      aria-labelledby="sym33-confirm-title"
    >
      <div className="rc-container sym33-container">

        {/* Page heading */}
        <div className="row g-4 align-items-end sym33-intro-row">
          <div className="col-12 col-lg-8">
            <p className="sym33-eyebrow">
              Symptom review
            </p>

            <h1 id="sym33-confirm-title">
              Check what we recognised.
              <span> You decide what's correct.</span>
            </h1>

            <p className="sym33-lead">
              Review the symptoms identified from your
              description. Keep the ones that match how
              you feel and remove any that do not.
            </p>
          </div>

          <div className="col-12 col-lg-4">
            <div className="sym33-progress">
              <div className="sym33-progress-top">
                <strong>Step 2 of 3</strong>
                <span>Confirm symptoms</span>
              </div>

              <div
                className="sym33-progress-track"
                role="progressbar"
                aria-label="Assessment progress"
                aria-valuemin={0}
                aria-valuemax={3}
                aria-valuenow={2}
              >
                <span style={{ width: '66.67%' }} />
              </div>
            </div>
          </div>
        </div>

        {!result ? (
          <div className="sym33-confirm-panel">

            <div className="sym33-confirm-header">
              <div>
                <p className="sym33-section-kicker">
                  Recognised symptoms
                </p>

                <h2>Review your selections</h2>

                <p>
                  {recognised.length} symptom
                  {recognised.length === 1 ? '' : 's'} recognised
                  from your description.
                </p>
              </div>

              <div className="sym33-total">
                <strong>{selectedCodes.length}</strong>
                <span>selected</span>
              </div>
            </div>

            <div className="sym33-original-description">
              <strong>Your original description</strong>

              <p>“{mapping.input_text}”</p>
            </div>

            {mapping.has_red_flag && (
              <div
                className="sym33-alert sym33-alert-warning"
                role="alert"
              >
                <strong>
                  Safety-sensitive wording detected
                </strong>

                <p>
                  One or more recognised symptoms may
                  need urgent attention. If your symptoms
                  are severe, rapidly worsening, or involve
                  breathing difficulty, seek medical
                  attention promptly.
                </p>
              </div>
            )}

            <div
              className="sym33-selection-list"
              aria-label="Select your symptoms"
            >
              {present.map((symptom) => {
                const selected = selectedCodes.includes(
                  symptom.code,
                )

                return (
                  <button
                    type="button"
                    key={symptom.code}
                    className={`sym33-selection-row${
                      selected ? ' is-selected' : ''
                    }${
                      symptom.is_red_flag ? ' is-warning' : ''
                    }`}
                    aria-pressed={selected}
                    disabled={loading}
                    onClick={() =>
                      toggleSymptom(symptom.code)
                    }
                  >
                    <span
                      className="sym33-checkbox"
                      aria-hidden="true"
                    >
                      {selected ? '✓' : ''}
                    </span>

                    <span className="sym33-selection-copy">
                      <span className="sym33-selection-title">
                        <strong>{symptom.display_name}</strong>

                        {symptom.is_red_flag && (
                          <span className="sym33-warning-tag">
                            Safety-sensitive
                          </span>
                        )}
                      </span>

                      <span className="sym33-selection-description">
                        Recognised from{' '}
                        <b>“{symptom.matched_text}”</b>
                      </span>
                    </span>

                    <span className="sym33-selection-state">
                      {selected ? 'Selected' : 'Not selected'}
                    </span>
                  </button>
                )
              })}
            </div>

            {otherMentions.length > 0 && (
              <div className="sym33-original-description" role="note" aria-label="Absent or uncertain symptoms">
                <strong>Absent or uncertain symptoms / Dalili zisizopo au zisizo na uhakika</strong>
                <ul>{otherMentions.map((symptom) => (
                  <li key={symptom.code}>{symptom.display_name}: {symptom.reported_subject === 'other_person'
                    ? 'reported for another person / imeripotiwa kwa mtu mwingine' : symptom.status === 'absent'
                    ? 'reported absent / haipo' : 'uncertain / hakuna uhakika'}</li>
                ))}</ul>
                <p>These are preserved separately and are not selected as present symptoms.</p>
              </div>
            )}

            <p className="sym33-selection-help">
              Select a symptom to include it, or select
              it again to remove it. At least one symptom
              must remain selected.
            </p>

            {error && (
              <div
                className="form-message error-message sym33-error"
                role="alert"
              >
                {error}
              </div>
            )}

            <div className="sym33-confirm-actions">
              <Link
                to="/symptoms"
                className="button button-secondary sym33-secondary-button"
              >
                Back to symptom input
              </Link>

              <button
                type="button"
                className="button button-primary sym33-primary-button"
                disabled={loading}
                onClick={handleConfirmation}
              >
                {loading
                  ? 'Confirming...'
                  : 'Confirm selected symptoms'}

                {!loading && (
                  <span aria-hidden="true">→</span>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div
            className="sym33-confirm-result"
            aria-live="polite"
          >
            {isUrgent ? (
              <div
                className="sym33-alert sym33-alert-urgent"
                role="alert"
              >
                <p className="sym33-section-kicker">
                  Urgent review recommended
                </p>

                <h2>
                  A confirmed symptom needs prompt attention.
                </h2>

                <p>
                  RespiraCare detected a safety-sensitive
                  confirmed symptom. Seek prompt professional
                  medical assessment, particularly if you
                  have severe or worsening symptoms or
                  difficulty breathing.
                </p>

                <p>
                  This assessment will not continue to
                  automated disease prediction.
                </p>
              </div>
            ) : (
              <div className="sym33-confirm-success">
                <p className="sym33-section-kicker">
                  Confirmation complete
                </p>

                <h2>Your symptoms have been confirmed.</h2>

                <p>
                  Only the symptoms you selected will be
                  used in the next stage of the assessment.
                </p>
              </div>
            )}

            <section
              className="sym33-confirm-summary"
              aria-labelledby="sym33-summary-title"
            >
              <div className="sym33-results-heading">
                <div>
                  <p className="sym33-section-kicker">
                    Your selection
                  </p>

                  <h2 id="sym33-summary-title">
                    Confirmed symptoms
                  </h2>
                </div>

                <div className="sym33-total">
                  <strong>{confirmed.length}</strong>
                  <span>confirmed</span>
                </div>
              </div>

              <div className="sym33-summary-list">
                {confirmed.map((symptom) => (
                  <div
                    className="sym33-summary-row"
                    key={symptom.code}
                  >
                    <div>
                      <strong>{symptom.display_name}</strong>
                      <p>{symptom.matched_text}</p>
                    </div>

                    {symptom.is_red_flag && (
                      <span className="sym33-warning-tag">
                        Safety-sensitive
                      </span>
                    )}
                  </div>
                ))}
              </div>

              {rejected.length > 0 && (
                <div className="sym33-excluded">
                  <h3>Not confirmed</h3>

                  <p>
                    These symptoms were excluded from
                    your confirmed selection.
                  </p>

                  <div className="sym33-excluded-list">
                    {rejected.map((symptom) => (
                      <span key={symptom.code}>
                        {symptom.display_name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {!isUrgent && (
              <div className="sym33-next">
                <div>
                  <p className="sym33-section-kicker">
                    Next step
                  </p>

                  <h3>Generate your health-awareness result</h3>

                  <p>
                    Provide your age and sex in the next
                    step to continue the assessment. We may
                    ask a relevant follow-up question or
                    explain that more evidence is needed.
                  </p>
                </div>

                <Link
                  to="/prediction"
                  className="button button-primary sym33-primary-button"
                >
                  Continue to prediction
                  <span aria-hidden="true">→</span>
                </Link>
              </div>
            )}

            <div className="sym33-result-actions">
              <button
                type="button"
                className="sym33-text-action"
                onClick={handleReviewAgain}
              >
                Review selections again
              </button>

              {isUrgent && (
                <Link
                  to="/dashboard"
                  className="button button-secondary sym33-secondary-button"
                >
                  Return to dashboard
                </Link>
              )}
            </div>
          </div>
        )}

        <div className="sym33-bottom-note">
          <div>
            <strong>Health-awareness information only</strong>

            <p>
              RespiraCare provides preliminary
              health-awareness support and is not a
              medical diagnosis.
            </p>
          </div>

          <Link to="/dashboard">
            Return to dashboard
          </Link>
        </div>

      </div>
    </section>
  )
}

export default SymptomConfirmationPage
