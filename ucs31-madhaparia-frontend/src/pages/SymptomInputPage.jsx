
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import {
  clearSymptomConfirmation,
  clearSymptomMapping,
  mapSymptoms,
  saveSymptomMapping,
} from '../services/symptoms'

import { clearPredictionResult } from '../services/predictions'
import { getApiErrorMessage } from '../services/api'

function languageLabel(language) {
  if (language === 'en') return 'English'
  if (language === 'sw') return 'Kiswahili'
  return language || 'Unspecified'
}

const examples = [
  {
    label: 'English + Kiswahili',
    text: 'I have fever na kikohozi',
  },
  {
    label: 'Misspelled symptoms',
    text: 'I have a couhg and feaver',
  },
  {
    label: 'Unmatched wording',
    text: 'I have fever and a skin rash',
  },
]

function SymptomInputPage() {
  const location = useLocation()
  const [text, setText] = useState(location.state?.text || '')
  const [mapping, setMapping] = useState(location.state?.mapping || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const requestVersion = useRef(0)
  const urgentAlert = useRef(null)
  useEffect(() => () => { requestVersion.current += 1 }, [])
  useEffect(() => {
    if (location.state?.mapping) clearSymptomConfirmation()
  }, [location.state])

  useEffect(() => {
    if (mapping?.has_red_flag) {
      // Bring emergency guidance into view immediately, before any questionnaire.
      urgentAlert.current?.focus({ preventScroll: true })
      urgentAlert.current?.scrollIntoView?.({ block: 'start', behavior: 'instant' })
    }
  }, [mapping])

  const recognised = mapping?.recognised_symptoms || []
  const unmatched = mapping?.unmatched_wording || []

  function invalidatePreviousResults() {
    requestVersion.current += 1
    setMapping(null)
    clearSymptomMapping()
    clearSymptomConfirmation()
    clearPredictionResult()
  }

  function handleTextChange(event) {
    setText(event.target.value)
    setError('')
    invalidatePreviousResults()
  }

  function loadExample(exampleText) {
    setText(exampleText)
    setError('')
    invalidatePreviousResults()
  }

  function handleReset() {
    setText('')
    setError('')
    invalidatePreviousResults()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    const cleanedText = text.trim()

    if (!cleanedText) {
      setError(
        'Please describe at least one symptom before continuing.',
      )
      return
    }

    setLoading(true)

    // Invalidate older results before a new analysis.
    invalidatePreviousResults()
    const version = requestVersion.current

    try {
      const result = await mapSymptoms(cleanedText)
      if (version !== requestVersion.current) return
      setMapping(result)
      saveSymptomMapping(result)
    } catch (requestError) {
      if (version !== requestVersion.current) return
      if (requestError.response?.status === 422) {
        setError(
          'Please check your symptom description and try again.',
        )
      } else {
        setError(
          getApiErrorMessage(
            requestError,
            'Your symptoms could not be analysed. Please try again.',
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <section
      className="sym33-page"
      aria-labelledby="sym33-input-title"
    >
      <div className="rc-container sym33-container">

        {/* Page heading */}
        <div className="row g-4 align-items-end sym33-intro-row">
          <div className="col-12 col-lg-8">
            <p className="sym33-eyebrow">Symptom awareness</p>

            <h1 id="sym33-input-title">
              Tell us how you're feeling.
              <span> Use your own words.</span>
            </h1>

            <p className="sym33-lead">
              Describe your symptoms naturally in English,
              Kiswahili, or a mix of both. We'll show you
              what RespiraCare recognises before you confirm
              anything.
            </p>
          </div>

          <div className="col-12 col-lg-4">
            <div className="sym33-progress">
              <div className="sym33-progress-top">
                <strong>Step 1 of 3</strong>
                <span>Describe symptoms</span>
              </div>

              <div
                className="sym33-progress-track"
                role="progressbar"
                aria-label="Assessment progress"
                aria-valuemin={0}
                aria-valuemax={3}
                aria-valuenow={1}
              >
                <span style={{ width: '33.33%' }} />
              </div>
            </div>
          </div>
        </div>

        {/* Input and guidance */}
        <div className="row g-4 sym33-workspace">
          <div className="col-12 col-lg-8">
            <div className="sym33-form-panel">
              <div className="sym33-section-heading">
                <div>
                  <p className="sym33-section-kicker">
                    Your description
                  </p>

                  <h2>Describe your symptoms</h2>
                </div>

                <span className="sym33-language-label">
                  English + Kiswahili
                </span>
              </div>

              <form onSubmit={handleSubmit}>
                <label
                  className="sym33-field-label"
                  htmlFor="symptom-text"
                >
                  Symptom description
                </label>

                <p
                  className="sym33-field-help"
                  id="sym33-text-help"
                >
                  Include the symptoms you're experiencing.
                  You don't need to use medical terms.
                </p>

                <textarea
                  id="symptom-text"
                  className="form-control sym33-textarea"
                  value={text}
                  onChange={handleTextChange}
                  placeholder="For example: I have fever na kikohozi and I feel tired..."
                  rows={6}
                  maxLength={1000}
                  aria-describedby="sym33-text-help sym33-character-count"
                  aria-invalid={Boolean(error && !text.trim())}
                />

                <div className="sym33-input-meta">
                  <span id="sym33-character-count">
                    {text.length} / 1000 characters
                  </span>

                  <span>Write naturally, in either language.</span>
                </div>

                {error && (
                  <div
                    className="form-message error-message sym33-error"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                <div className="sym33-form-actions">
                  {(text || mapping) && (
                    <button
                      type="button"
                      className="button button-secondary sym33-secondary-button"
                      onClick={handleReset}
                      disabled={loading}
                    >
                      Clear description
                    </button>
                  )}

                  <button
                    type="submit"
                    className="button button-primary sym33-primary-button"
                    disabled={loading}
                  >
                    {loading
                      ? 'Analysing symptoms...'
                      : mapping
                        ? 'Analyse again'
                        : 'Analyse symptoms'}

                    {!loading && (
                      <span aria-hidden="true">→</span>
                    )}
                  </button>
                </div>
              </form>

              {/* Examples */}
              <div className="sym33-examples">
                <p className="sym33-section-kicker">
                  Need an example?
                </p>

                <p>
                  Select an example below to fill in the
                  description. You can edit it before
                  analysing.
                </p>

                <div className="sym33-example-actions">
                  {examples.map((example) => (
                    <button
                      type="button"
                      key={example.label}
                      onClick={() => loadExample(example.text)}
                      disabled={loading}
                    >
                      {example.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Writing guidance */}
          <div className="col-12 col-lg-4">
            <aside className="sym33-help-panel">
              <p className="sym33-section-kicker">
                Writing guidance
              </p>

              <h2>Speak naturally.</h2>

              <p className="sym33-help-intro">
                A short description in everyday language
                is enough to get started.
              </p>

              <div className="sym33-language-examples">
                <div>
                  <strong>English</strong>
                  <p>“I have a cough and fever.”</p>
                </div>

                <div>
                  <strong>Kiswahili</strong>
                  <p>“Nina kikohozi na homa.”</p>
                </div>

                <div>
                  <strong>Mixed language</strong>
                  <p>“I have fever na kikohozi.”</p>
                </div>
              </div>

              <p className="sym33-help-note">
                The NLP system can recognise some spelling
                mistakes using fuzzy matching. You will
                still review the recognised symptoms
                yourself.
              </p>
            </aside>
          </div>
        </div>

        {/* NLP mapping results */}
        {mapping && (
          <section
            className="sym33-results"
            aria-labelledby="sym33-results-title"
          >
            <div className="sym33-results-heading">
              <div>
                <p className="sym33-section-kicker">
                  Analysis complete
                </p>

                <h2 id="sym33-results-title">
                  Here's what we recognised.
                </h2>

                <p>
                  Review the results below. You can choose
                  which symptoms are correct in the next step.
                </p>
              </div>

              <div className="sym33-total">
                <strong>{recognised.length}</strong>
                <span>recognised</span>
              </div>
            </div>

            {mapping.has_red_flag && (
              <div
                className="sym33-alert sym33-alert-warning"
                role="alert"
                ref={urgentAlert}
                tabIndex={-1}
              >
                <strong>
                  Safety-sensitive wording detected
                </strong>

                <p>
                  {mapping.health_guidance || mapping.safety_message ||
                    'Seek urgent medical help now if you are struggling to breathe. Do not wait to finish this assessment. / Tafuta huduma ya matibabu ya dharura sasa ikiwa unapata shida kubwa ya kupumua. Usisubiri kukamilisha tathmini hii.'}
                </p>
                {mapping.safety_question && <fieldset disabled={loading}>
                  <legend>{mapping.safety_question.text}</legend>
                  {mapping.safety_question.options.map((option) => <button key={option.value} type="button"
                    className="button button-secondary m-1" onClick={async () => {
                      setLoading(true)
                      try {
                        const checked = await mapSymptoms(text, option.value)
                        setMapping(checked)
                        saveSymptomMapping(checked)
                      } catch { setError('Could not update the safety check. Seek same-day care; at rest or unable to speak: hospital casualty now.') }
                      finally { setLoading(false) }
                    }}>{option.label}</button>)}
                </fieldset>}
                {mapping.disclaimer && <p>{mapping.disclaimer}</p>}
              </div>
            )}

            {recognised.length > 0 ? (
              <div className="sym33-recognised-list">
                {recognised.map((symptom) => (
                  <article
                    key={symptom.code}
                    className={`sym33-recognised-row${
                      symptom.is_red_flag
                        ? ' is-warning'
                        : ''
                    }`}
                  >
                    <div className="sym33-recognised-main">
                      <div className="sym33-recognised-heading">
                        <h3>{symptom.display_name}</h3>
                        {symptom.status && (
                          <span>{symptom.reported_subject === 'other_person' ? 'Reported for another person / Mtu mwingine'
                            : symptom.status === 'absent' ? 'Reported absent / Haipo'
                            : symptom.status === 'unknown' ? 'Uncertain / Hakuna uhakika'
                              : 'Present / Ipo'}</span>
                        )}

                        {symptom.is_red_flag && (
                          <span className="sym33-warning-tag">
                            Safety-sensitive
                          </span>
                        )}
                      </div>

                      <p>
                        Recognised from{' '}
                        <strong>
                          “{symptom.matched_text}”
                        </strong>
                      </p>
                      {(symptom.duration_text || symptom.severity) && <p>
                        {symptom.duration_text && <span>Duration: {symptom.duration_text}. </span>}
                        {symptom.severity && <span>Severity: {symptom.severity}.</span>}
                      </p>}
                    </div>

                    <div className="sym33-recognised-meta">
                      <span>
                        Please confirm this symptom
                      </span>

                      <span>
                        {languageLabel(symptom.language)}
                      </span>

                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="sym33-empty-state">
                <h3>No supported symptoms were recognised</h3>

                <p>
                  Try using different wording or review
                  the unmatched phrases below.
                </p>
              </div>
            )}

            {unmatched.length > 0 && (
              <section className="sym33-unmatched">
                <p className="sym33-section-kicker">
                  Needs review
                </p>

                <h3>Unmatched wording</h3>

                <p>
                  These phrases were not automatically
                  accepted as recognised symptoms.
                  Suggestions are shown for reference only.
                </p>

                {unmatched.map((item, index) => (
                  <div
                    className="sym33-unmatched-row"
                    key={`${item.unmatched_text}-${index}`}
                  >
                    <strong>
                      “{item.unmatched_text}”
                    </strong>

                    {(item.suggestions || []).length > 0 ? (
                      <div className="sym33-suggestions">
                        {item.suggestions.map((suggestion, i) => (
                          <span
                            key={`${suggestion.code}-${i}`}
                          >
                            {suggestion.suggested_alias}
                            {' · '}
                            {languageLabel(suggestion.language)}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p>
                        No close supported suggestion
                        was found.
                      </p>
                    )}
                  </div>
                ))}
              </section>
            )}

            {recognised.some((symptom) => (!symptom.status || symptom.status === 'present') && symptom.reported_subject !== 'other_person') && !mapping.has_red_flag && (
              <div className="sym33-next">
                <div>
                  <p className="sym33-section-kicker">
                    Next step
                  </p>

                  <h3>Review and confirm your symptoms</h3>

                  <p>
                    Select only the recognised symptoms
                    that correctly describe how you feel.
                  </p>
                </div>

                <Link
                  to="/symptoms/confirm"
                  className="button button-primary sym33-primary-button"
                >
                  Continue to confirmation
                  <span aria-hidden="true">→</span>
                </Link>
              </div>
            )}
          </section>
        )}

        <div className="sym33-bottom-note">
          <div>
            <strong>Health-awareness information only</strong>
            <p>
              Symptom recognition is not a medical diagnosis
              or a substitute for professional medical care.
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

export default SymptomInputPage
