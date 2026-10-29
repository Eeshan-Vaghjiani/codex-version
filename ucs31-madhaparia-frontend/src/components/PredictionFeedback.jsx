import { useState } from 'react'

import { getApiErrorMessage } from '../services/api'

import {
  submitPredictionFeedback,
} from '../services/feedback'

function PredictionFeedback({
  predictionId,
}) {
  const [wasHelpful, setWasHelpful] =
    useState(null)

  const [comment, setComment] =
    useState('')

  const [loading, setLoading] =
    useState(false)

  const [submitted, setSubmitted] =
    useState(false)

  const [duplicate, setDuplicate] =
    useState(false)

  const [error, setError] =
    useState('')

  async function handleSubmit(event) {
    event.preventDefault()

    setError('')

    if (
      wasHelpful !== true &&
      wasHelpful !== false
    ) {
      setError(
        'Please tell us whether this result was helpful.',
      )

      return
    }

    if (comment.length > 1000) {
      setError(
        'Feedback comments cannot exceed 1000 characters.',
      )

      return
    }

    setLoading(true)

    try {
      await submitPredictionFeedback({
        predictionId,
        wasHelpful,
        comment,
      })

      setSubmitted(true)
    } catch (requestError) {
      const detail =
        requestError.response?.data?.detail

      if (
        requestError.response?.status === 400 &&
        typeof detail === 'string' &&
        detail.includes(
          'already been submitted',
        )
      ) {
        setDuplicate(true)
      } else if (
        requestError.response?.status === 422
      ) {
        setError(
          'Please check your feedback and try again.',
        )
      } else {
        setError(
          getApiErrorMessage(
            requestError,
            'Your feedback could not be submitted. Please try again.',
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <section className="feedback-card feedback-success">
        <div className="feedback-success-icon">
          ✓
        </div>

        <div>
          <span>
            Feedback received
          </span>

          <h3>
            Thank you for helping us improve RespiraCare.
          </h3>

          <p>
            Your feedback has been saved for this
            prediction session.
          </p>
        </div>
      </section>
    )
  }

  if (duplicate) {
    return (
      <section className="feedback-card feedback-existing">
        <div className="feedback-existing-icon">
          ✓
        </div>

        <div>
          <span>
            Feedback already received
          </span>

          <h3>
            This session already has feedback.
          </h3>

          <p>
            RespiraCare only accepts one feedback
            submission for each prediction session.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="feedback-card">
      <div className="feedback-heading">
        <span>
          Your feedback
        </span>

        <h3>
          Was this health-awareness result helpful?
        </h3>

        <p>
          Your response helps evaluate and improve
          the RespiraCare experience.
        </p>
      </div>

      <form
        className="feedback-form"
        onSubmit={handleSubmit}
      >
        <div className="feedback-choice-group">
          <button
            type="button"
            aria-pressed={wasHelpful === true}
            className={
              wasHelpful === true
                ? 'feedback-choice selected'
                : 'feedback-choice'
            }
            onClick={() => {
              setWasHelpful(true)
              setError('')
            }}
          >
            <span className="feedback-choice-icon">
              ✓
            </span>

            <span>
              <strong>
                Yes
              </strong>

              <small>
                This was helpful
              </small>
            </span>
          </button>

          <button
            type="button"
            aria-pressed={wasHelpful === false}
            className={
              wasHelpful === false
                ? 'feedback-choice selected'
                : 'feedback-choice'
            }
            onClick={() => {
              setWasHelpful(false)
              setError('')
            }}
          >
            <span className="feedback-choice-icon">
              ×
            </span>

            <span>
              <strong>
                No
              </strong>

              <small>
                This was not helpful
              </small>
            </span>
          </button>
        </div>

        <div className="feedback-comment-field">
          <div className="feedback-comment-label">
            <label htmlFor={`feedback-${predictionId}`}>
              Additional comment
              <span> Optional</span>
            </label>

            <span>
              {comment.length}/1000
            </span>
          </div>

          <textarea
            id={`feedback-${predictionId}`}
            value={comment}
            maxLength="1000"
            rows="4"
            placeholder="Tell us what was useful or what could be improved..."
            onChange={(event) => {
              setComment(
                event.target.value,
              )

              setError('')
            }}
          />
        </div>

        {error && (
          <div
            className="form-message error-message"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="feedback-actions">
          <p>
            Do not include confidential or sensitive
            personal information in your comment.
          </p>

          <button
            type="submit"
            className="button button-primary"
            disabled={loading}
          >
            {loading
              ? 'Submitting feedback...'
              : 'Submit feedback'}
          </button>
        </div>
      </form>
    </section>
  )
}

export default PredictionFeedback