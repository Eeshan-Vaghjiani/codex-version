
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import {
  getSavedSymptomConfirmation,
  getSavedSymptomMapping,
} from '../services/symptoms'

import {
  clearPredictionResult,
  createPrediction,
  getSavedPredictionResult,
  isPredictionForConfirmation,
  savePredictionResult,
} from '../services/predictions'

import { getApiErrorMessage } from '../services/api'
import PredictionFeedback from '../components/PredictionFeedback'
import PossibleExplanations from '../components/PossibleExplanations'
import { getPatientPrimary, hasPatientDecision } from '../services/patientResult'

function PredictionPage() {
  const mapping = getSavedSymptomMapping()
  const confirmation = getSavedSymptomConfirmation()

  const [age, setAge] = useState(() =>
    getSavedPredictionResult()?.request_context?.age?.toString() || '')
  const [sex, setSex] = useState(() =>
    getSavedPredictionResult()?.request_context?.sex || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [followUpAnswer, setFollowUpAnswer] = useState('')

  // Keep a saved result only when it belongs to
  // this exact symptom description and selection.
  const [result, setResult] = useState(() => {
    const saved = getSavedPredictionResult()

    if (
      !isPredictionForConfirmation(
        saved,
        mapping?.input_text,
        confirmation?.confirmed_codes,
      )
    ) {
      return null
    }

    // An urgent confirmation must never reuse
    // an ordinary disease prediction.
    if (
      (confirmation?.safety_status === 'urgent_review' ||
        confirmation?.has_red_flag || mapping?.has_red_flag) &&
      saved?.status !== 'urgent_review'
    ) {
      return null
    }

    return saved
  })

  if (!mapping || !confirmation) {
    return <Navigate to="/symptoms" replace />
  }

  const isConfirmedUrgent =
    confirmation.safety_status === 'urgent_review' ||
    confirmation.has_red_flag === true || mapping.has_red_flag === true

  const confirmedSymptoms =
    confirmation.confirmed_symptoms || []

  const confirmedCodes =
    confirmation.confirmed_codes || []

  const needsFollowUp = result?.status === 'needs_follow_up'
  const assessmentComplete = Boolean(result) && !needsFollowUp
  const question = needsFollowUp ? result.follow_up_question : null
  const contextNote = result?.context_note || result?.assessment_context?.context_note
  const duration = result?.assessment_context?.duration
  const durationLabel = duration && ({
    under_3_days: 'Less than 3 days / Chini ya siku 3',
    '3_to_14_days': '3 to 14 days / Siku 3 hadi 14',
    over_14_days: 'More than 14 days / Zaidi ya siku 14',
    unknown: 'Not sure / Sina uhakika',
  }[duration.text] || duration.text)
  const prediction = getPatientPrimary(result)
  const currentDecision = hasPatientDecision(result)

  const swahili = result?.assessment_context?.language === 'sw'

  const isUrgentResult =
    result?.status === 'urgent_review' || result?.care_level === 'urgent_review' ||
    result?.has_red_flag === true || isConfirmedUrgent

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    const numericAge = Number(age)

    if (
      !age ||
      !Number.isInteger(numericAge) ||
      numericAge < 0 ||
      numericAge > 120
    ) {
      setError('Please enter a valid age between 0 and 120.')
      return
    }

    if (sex !== 'M' && sex !== 'F') {
      setError('Please select your sex before continuing.')
      return
    }

    if (confirmedCodes.length === 0) {
      setError(
        'No confirmed symptoms are available for prediction.',
      )
      return
    }

    const previousAnswers = result?.follow_up_answers || []
    if (needsFollowUp && !question?.options?.some(
      (option) => option.value === followUpAnswer,
    )) {
      setError('Please choose one of the listed answers. / Tafadhali chagua jibu moja.')
      return
    }
    const followUpAnswers = needsFollowUp
      ? [...previousAnswers, { question_id: question.id, answer: followUpAnswer }]
      : []

    setLoading(true)

    try {
      clearPredictionResult()

      const response = await createPrediction({
        age: numericAge,
        sex,
        text: mapping.input_text,
        confirmedCodes,
        ...(followUpAnswers.length > 0 && { followUpAnswers }),
      })

      // The backend is responsible for red-flag routing.
      // Do not accept a disease prediction for a known
      // urgent-review confirmation.
      if (
        isConfirmedUrgent &&
        response.status !== 'urgent_review'
      ) {
        setError(
          'Urgent safety guidance could not be confirmed. Please seek prompt medical assessment rather than relying on an automated prediction.',
        )
        return
      }

      setResult(response)
      setFollowUpAnswer('')
      savePredictionResult(response, mapping.input_text, {
        age: numericAge,
        sex,
      })
    } catch (requestError) {
      if (requestError.response?.status === 401) {
        setError(
          'Your login session is no longer valid. Please log in again.',
        )
      } else if (requestError.response?.status === 422) {
        setError(
          getApiErrorMessage(
            requestError,
            'Please check your details and confirmed symptoms before trying again.',
          ),
        )
      } else {
        setError(
          getApiErrorMessage(
            requestError,
            'RespiraCare could not generate the result. Please try again.',
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }

  function handleStartAgain() {
    clearPredictionResult()
    setResult(null)
    setAge('')
    setSex('')
    setError('')
    setFollowUpAnswer('')
  }

  return (
    <section
      className="pred34-page"
      aria-labelledby="pred34-title"
    >
      <div className="rc-container pred34-container">

        {/* Shared page introduction */}
        <div className="row g-4 align-items-end pred34-intro">
          <div className="col-12 col-lg-8">
            <p className="pred34-eyebrow">
              Health awareness
            </p>

            <h1 id="pred34-title">
              Understand your
              <span> symptoms.</span>
            </h1>

            <p className="pred34-lead">
              Answer a few short questions to explore what
              your symptoms may mean and when to seek care.
              This information is not a medical diagnosis.
            </p>
          </div>

          <div className="col-12 col-lg-4">
            <div className="pred34-progress">
              <div className="pred34-progress-labels">
                <strong>Step 3 of 3</strong>
                <span>
                  {needsFollowUp ? 'A brief follow-up / Swali fupi'
                    : result ? 'Assessment complete' : 'Health awareness'}
                </span>
              </div>

              <div
                className="pred34-progress-track"
                role="progressbar"
                aria-label="Assessment progress"
                aria-valuemin={0}
                aria-valuemax={3}
                aria-valuenow={assessmentComplete ? 3 : 2}
              >
                <span
                  style={{
                    width: assessmentComplete ? '100%' : '66.67%',
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Before a prediction is submitted */}
        {!result && (
          <div className="row g-4 pred34-workspace">
            <div className="col-12 col-lg-8">
              <section
                className="pred34-panel"
                aria-labelledby="pred34-form-title"
              >
                <div className="pred34-panel-header">
                  <div>
                    <p className="pred34-kicker">
                      Final step
                    </p>

                    <h2 id="pred34-form-title">
                      Complete your information
                    </h2>

                    <p>
                      Enter the remaining details required
                      for this assessment.
                    </p>
                  </div>

                  {!isConfirmedUrgent && (
                    <span className="pred34-ready">
                      Ready
                    </span>
                  )}
                </div>

                <div className="pred34-confirmed">
                  <div className="pred34-confirmed-heading">
                    <strong>Confirmed symptoms</strong>
                    <span>
                      {confirmedCodes.length} selected
                    </span>
                  </div>

                  <div className="pred34-symptom-list">
                    {confirmedSymptoms.map((symptom) => (
                      <span
                        key={symptom.code}
                        className="pred34-symptom"
                      >
                        {symptom.display_name}
                      </span>
                    ))}
                  </div>
                </div>

                {isConfirmedUrgent && (
                  <div
                    className="pred34-warning"
                    role="alert"
                  >
                    <strong>
                      Safety-sensitive symptom confirmed
                    </strong>

                    <p>
                      {confirmation.health_guidance || mapping.health_guidance ||
                        'Seek urgent medical help now if you are struggling to breathe. Do not wait to complete this form. / Tafuta huduma ya matibabu ya dharura sasa ikiwa unapata shida kubwa ya kupumua. Usisubiri kukamilisha fomu hii.'}
                    </p>
                  </div>
                )}

                <form
                  className="pred34-form"
                  onSubmit={handleSubmit}
                >
                  <div className="row g-3">
                    <div className="col-12 col-md-6">
                      <div className="pred34-field">
                        <label htmlFor="prediction-age">
                          Age
                        </label>

                        <input
                          id="prediction-age"
                          className="form-control"
                          type="number"
                          inputMode="numeric"
                          min="0"
                          max="120"
                          value={age}
                          disabled={loading}
                          placeholder="e.g. 25"
                          onChange={(event) => {
                            setAge(event.target.value)
                            setError('')
                          }}
                        />
                      </div>
                    </div>

                    <div className="col-12 col-md-6">
                      <div className="pred34-field">
                        <label htmlFor="prediction-sex">
                          Sex
                        </label>

                        <select
                          id="prediction-sex"
                          className="form-select"
                          value={sex}
                          disabled={loading}
                          onChange={(event) => {
                            setSex(event.target.value)
                            setError('')
                          }}
                        >
                          <option value="">
                            Select
                          </option>

                          <option value="M">
                            Male
                          </option>

                          <option value="F">
                            Female
                          </option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="pred34-input-note">
                    <strong>
                      Why are these required?
                    </strong>

                    <p>
                      These details are required for this assessment.
                      They do not identify the cause of your symptoms.
                      Seek urgent care immediately if you have
                      serious warning signs.
                    </p>
                  </div>

                  {error && (
                    <div
                      className="form-message error-message pred34-form-error"
                      role="alert"
                    >
                      {error}
                    </div>
                  )}

                  <div className="pred34-actions">
                    <Link
                      to="/symptoms/confirm"
                      className="button button-secondary pred34-secondary"
                    >
                      Back to confirmation
                    </Link>

                    <button
                      type="submit"
                      className="button button-primary pred34-primary"
                      disabled={loading}
                    >
                      {loading
                        ? 'Generating result...'
                        : isConfirmedUrgent
                          ? 'Continue safety review'
                          : 'Generate awareness result'}

                      {!loading && (
                        <span aria-hidden="true">→</span>
                      )}
                    </button>
                  </div>
                </form>
              </section>
            </div>

            <div className="col-12 col-lg-4">
              <aside className="pred34-aside">
                <p className="pred34-kicker">
                  Before you continue
                </p>

                <h2>What happens next?</h2>

                <div className="pred34-aside-step">
                  <span>01</span>
                  <div>
                    <strong>Submit your details</strong>
                    <p>
                      We use your confirmed symptoms
                      and the details you provide.
                    </p>
                  </div>
                </div>

                <div className="pred34-aside-step">
                  <span>02</span>
                  <div>
                    <strong>Review the result</strong>
                    <p>
                      We may ask a short follow-up question
                      or explain that there is insufficient
                      information for a condition assessment.
                    </p>
                  </div>
                </div>

                <div className="pred34-aside-step">
                  <span>03</span>
                  <div>
                    <strong>Read the guidance</strong>
                    <p>
                      Understand the limitations and
                      when to seek medical help.
                    </p>
                  </div>
                </div>

                <p className="pred34-aside-footnote">
                  A model result cannot confirm or rule out
                  any disease.
                </p>
              </aside>
            </div>
          </div>
        )}

        {/* Result returned by the backend */}
        {result && (
          <div className="pred34-results">
            {isUrgentResult ? (
              <section
                className="pred34-urgent-result"
                aria-labelledby="pred34-urgent-title"
                role="alert"
              >
                <p className="pred34-kicker">
                  Urgent review
                </p>

                <h2 id="pred34-urgent-title">
                  Seek prompt medical assessment.
                </h2>

                <p>
                  {result.health_guidance ||
                    'Your confirmed symptoms may need prompt medical attention. Please consult a qualified healthcare professional.'}
                </p>

                <p className="pred34-urgent-footnote">
                  No automated disease prediction is
                  displayed for this urgent-review case.
                </p>
              </section>
            ) : needsFollowUp ? (
              <section className="pred34-panel" aria-labelledby="follow-up-title">
                <h2 id="follow-up-title">{question?.text || 'More information is needed'}</h2>
                {question?.rationale && <p>{question.rationale}</p>}
                <form onSubmit={handleSubmit}>
                  <fieldset disabled={loading}>
                    <legend className="visually-hidden">{question?.text}</legend>
                    {(question?.options || []).map((option, index) => (
                      <label className="d-block my-3" key={option.value}>
                        <input type="radio" name="follow-up-answer"
                          value={option.value}
                          checked={followUpAnswer === option.value}
                          onChange={() => { setFollowUpAnswer(option.value); setError('') }} />
                        {' '}{/^\d+[.)]\s/.test(option.label) ? option.label : `${index + 1}. ${option.label}`}
                      </label>
                    ))}
                  </fieldset>
                  {error && <p role="alert">{error}</p>}
                  <button className="button button-primary" type="submit" disabled={loading}>
                    {loading ? 'Updating assessment...' : 'Continue / Endelea'}
                  </button>
                </form>
                <p className="mt-3">{result.health_guidance}</p>
              </section>
            ) : (
              <>
                {prediction && result.uncertain === true && result.uncertainty_message && (
                  <div className="pred34-uncertainty" role="status">
                    <strong>About this result</strong>
                    <p>{result.uncertainty_message}</p>
                  </div>
                )}
                <div className="pred34-result-intro">
                  <p className="pred34-kicker">
                    Analysis complete
                  </p>

                  <h2>{prediction ? (swahili ? 'Hali inayowezekana' : 'Possible explanation')
                    : swahili ? 'Tunahitaji maelezo zaidi' : 'More information is needed'}</h2>

                  <p>
                    {currentDecision && result.assessment_summary || (prediction
                      ? 'Your symptoms may fit this condition. An examination or tests may still be needed.'
                      : swahili ? 'Dalili hizi zinaweza kuwa na sababu kadhaa. Hazitoshi kutambua ugonjwa fulani.'
                        : 'These symptoms can have several causes. There is not enough information to suggest a particular illness.')}
                  </p>
                </div>

                {prediction ? (
                  <PossibleExplanations
                    primary={prediction}
                    language={result.assessment_context?.language}
                  />
                ) : (
                  <section className="pred34-uncertainty" role="status">
                    <h3>{swahili ? 'Hatua inayofuata' : 'What can help'}</h3>
                    <p>{currentDecision ? (result.uncertainty_message || 'A healthcare professional can help assess your symptoms. Review the next steps below.') : 'Start a new symptom check to use the current assessment. Earlier model rankings cannot be treated as a supported result.'}</p>
                  </section>
                )}

                {Array.isArray(
                  result.unsupported_model_features,
                ) &&
                  result.unsupported_model_features.length > 0 && (
                    <div
                      className="pred34-information"
                      role="note"
                      aria-label="Unsupported symptom information"
                    >
                      <strong>
                        Some symptom details were not used
                      </strong>

                      <p>
                        {result.unsupported_model_features.length}{' '}
                        confirmed symptom detail(s) could
                        not be used by this prediction model.
                        They were excluded from the model
                        calculation. This does not mean those
                        symptoms are absent.
                      </p>
                    </div>
                  )}

                <section
                  className="pred34-guidance"
                  aria-labelledby="pred34-guidance-title"
                >
                  <p className="pred34-kicker">
                    Health guidance
                  </p>

                  <h3 id="pred34-guidance-title">
                    {swahili ? 'Hatua zinazofuata' : 'What to do next'}
                  </h3>

                  {result.health_guidance !== result.next_steps?.[0] && <p>{result.health_guidance}</p>}
                  {result.care_level === 'professional_review' && (
                    <strong>{swahili ? 'Tathmini ya mtaalamu wa afya inapendekezwa' : 'Professional review recommended'}</strong>
                  )}
                  {Array.isArray(result.next_steps) && result.next_steps.length > 0 && (
                    <ul>{result.next_steps.map((step) => <li key={step}>{step}</li>)}</ul>
                  )}
                </section>
              </>
            )}

            {durationLabel && (
              <p className="pred34-input-note">Duration / Muda: {durationLabel}</p>
            )}

            {contextNote && (
              <div className="pred34-information" role="note" aria-label="Assessment context limitations">
                <p>{contextNote}</p>
              </div>
            )}

            <section
              className="pred34-disclaimer"
              aria-label="Medical disclaimer"
            >
              <strong>Important</strong>

              <p>{result.disclaimer}</p>
            </section>

            {result.prediction_id && !needsFollowUp && <div className="pred34-feedback">
              <PredictionFeedback
                key={result.prediction_id}
                predictionId={result.prediction_id}
              />
            </div>}

            {result.prediction_id && <div className="pred34-reference">
              <span>Session reference</span>
              <code>{result.prediction_id}</code>
            </div>}

            <div className="pred34-result-actions">
              <button
                type="button"
                className="button button-secondary pred34-secondary"
                onClick={handleStartAgain}
              >
                Review another result
              </button>

              <Link
                to="/dashboard"
                className="button button-primary pred34-primary"
              >
                Return to dashboard
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        )}

        <div className="pred34-bottom-note">
          <div>
            <strong>
              Health-awareness information only
            </strong>

            <p>
              RespiraCare is not a substitute for
              assessment by a qualified healthcare
              professional.
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

export default PredictionPage
