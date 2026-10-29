
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../services/api'
import { getPatientHistoryItem } from '../services/history'
import PredictionFeedback from '../components/PredictionFeedback'
import PossibleExplanations from '../components/PossibleExplanations'
import { getPatientPrimary, hasPatientDecision } from '../services/patientResult'

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

function sexLabel(value) {
  if (value === 'M') return 'Male'
  if (value === 'F') return 'Female'
  return value || 'Not recorded'
}

function readableCode(code) {
  return String(code).replaceAll('_', ' ')
}

function PatientHistoryDetailPage() {
  const { predictionId } = useParams()
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadSession() {
      try {
        const data = await getPatientHistoryItem(predictionId)
        if (active) setSession(data)
      } catch (requestError) {
        if (!active) return
        const status = requestError.response?.status
        if (status === 404 || status === 422) {
          setError('This prediction session could not be found.')
        } else if (status === 401) {
          setError('Your login session is no longer valid.')
        } else {
          setError(getApiErrorMessage(
            requestError,
            'RespiraCare could not load this prediction session.',
          ))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadSession()
    return () => { active = false }
  }, [predictionId])

  if (loading || error || !session) {
    return (
      <section className="hist35-page" aria-label="Patient history details">
        <div className="rc-container hist35-container">
          <div className={`hist35-state${error ? ' hist35-state-error' : ''}`}
            role={error ? 'alert' : 'status'}>
            {loading ? (
              <>
                <div className="auth-spinner" aria-hidden="true" />
                <h2>Loading prediction details...</h2>
                <p>Retrieving the saved assessment session.</p>
              </>
            ) : (
              <>
                <h2>Prediction unavailable</h2>
                <p>{error || 'This prediction session could not be found.'}</p>
                <Link to="/history" className="button button-secondary hist35-button">
                  Back to history
                </Link>
              </>
            )}
          </div>
        </div>
      </section>
    )
  }

  const urgent = session.status === 'urgent_review' || session.care_level === 'urgent_review' || session.has_red_flag === true
  const prediction = getPatientPrimary(session)
  const abstained = !prediction
  const currentDecision = hasPatientDecision(session)
  const confirmedCodes = Array.isArray(session.confirmed_codes)
    ? session.confirmed_codes : []
  const uncertaintyMessage = session.uncertainty_message ||
    (session.assessment_context?.language === 'sw'
      ? 'Matokeo haya ya modeli hayajathibitishwa kitabibu. Alama yake haiwezi kuthibitisha au kuondoa ugonjwa.'
      : 'This saved model result has not been clinically validated. It cannot confirm or rule out a disease.')

  return (
    <section className="hist35-page" aria-labelledby="hist35-detail-title">
      <div className="rc-container hist35-container">
        <div className="hist35-detail-heading">
          <div>
            <Link className="hist35-breadcrumb" to="/history">
              <span aria-hidden="true">←</span> Back to patient history
            </Link>
            <p className="hist35-eyebrow">Saved assessment</p>
            <h1 id="hist35-detail-title">Session details</h1>
            <p className="hist35-lead">{formatDate(session.created_at)}</p>
          </div>
          <span className={`hist35-status${urgent ? ' is-urgent' : ''}`}>
            {urgent ? 'Urgent review' :
              prediction ? 'Possible explanation' :
              session.status === 'reassessment_required' ? 'New check needed' :
              ['assessment_uncertain', 'insufficient_evidence'].includes(session.status) ? 'More information needed' :
              (session.status?.replaceAll('_', ' ') || 'Status unavailable')}
          </span>
        </div>

        <section className="hist35-info-card" aria-labelledby="hist35-info-title">
          <div className="hist35-section-title">
            <p className="hist35-kicker">Original assessment</p>
            <h2 id="hist35-info-title">What you submitted</h2>
          </div>
          <div className="hist35-quote">
            <strong>Original symptom description</strong>
            <p>“{session.input_text || 'No description saved'}”</p>
          </div>
          <div className="hist35-detail-meta">
            <div><span>Age</span><strong>{session.age ?? '—'}</strong></div>
            <div><span>Sex</span><strong>{sexLabel(session.sex)}</strong></div>
            <div><span>Date</span><strong>{formatDate(session.created_at)}</strong></div>
          </div>
          <div className="hist35-confirmed-codes">
            <div className="hist35-confirmed-heading">
              <strong>Symptoms you confirmed</strong>
              <span>{confirmedCodes.length} recorded</span>
            </div>
            {confirmedCodes.length > 0 ? (
              <div className="hist35-code-list">
                {confirmedCodes.map((code) => (
                  <span key={code} title={code}>{readableCode(code)}</span>
                ))}
              </div>
            ) : (
              <p className="hist35-muted">No confirmed symptoms were saved.</p>
            )}
          </div>
        </section>

        {urgent ? (
          <section className="hist35-urgent-detail" role="alert">
            <p className="hist35-kicker">Urgent-review session</p>
            <h2>{session.urgency === 'emergency' ? 'Emergency — seek care immediately.' : 'Prompt clinical review is needed.'}</h2>
            <p>
              A reported warning sign or unresolved potentially serious pattern
              needs professional review. No automated disease name is displayed.
            </p>
            {session.health_guidance && <p>{session.health_guidance}</p>}
            {(session.has_red_flag || session.status === 'urgent_review') && <p>The prediction model was bypassed for reported warning signs.</p>}
            <p>Seek prompt professional medical assessment if you are experiencing severe or worsening symptoms.</p>
          </section>
        ) : (
          <section className="hist35-result-section" aria-labelledby="hist35-result-title">
            <div className="hist35-section-title">
              <p className="hist35-kicker">Saved result</p>
              <h2 id="hist35-result-title">Saved assessment</h2>
              <p>This record is health information, not a diagnosis.</p>
            </div>

            {currentDecision && session.assessment_summary && <p>{session.assessment_summary}</p>}
            <p>Care priority: {session.urgency || session.care_level || 'Review if worsening'}. {session.health_guidance}</p>

            {prediction ? (
              <PossibleExplanations primary={prediction} language={session.assessment_context?.language} />
            ) : (
              <div className="hist35-no-result"><h3>More information is needed</h3><p>{currentDecision && session.status !== 'reassessment_required' ? 'The saved assessment did not support a particular illness. Review the guidance below.' : 'This earlier assessment needs a new symptom check. Its model rankings have not been selected under the current policy.'}</p><Link className="button button-secondary" to="/symptoms">Start a new symptom check</Link></div>
            )}

            {(session.uncertain === true || prediction || abstained) && (
              <div className="hist35-uncertainty" role="status">
                <strong>About this result</strong>
                <p>{uncertaintyMessage}</p>
              </div>
            )}

            {Array.isArray(session.unsupported_model_features) &&
              session.unsupported_model_features.length > 0 && (
                <div className="hist35-uncertainty" role="note"
                  aria-label="Unsupported symptom information">
                  <strong>Some symptom details were not used</strong>
                  <p>{session.unsupported_model_features.length} confirmed symptom
                    detail(s) were excluded from the model calculation. This does
                    not mean those symptoms were absent.</p>
                </div>
              )}

            {session.health_guidance && (
              <div className="hist35-guidance">
                <p className="hist35-kicker">Health guidance</p>
                <h3>What to do next</h3>
                {session.health_guidance !== session.next_steps?.[0] && <p>{session.health_guidance}</p>}
                {Array.isArray(session.next_steps) && <ul>{session.next_steps.map((step) => <li key={step}>{step}</li>)}</ul>}
              </div>
            )}
          </section>
        )}

        {session.assessment_context?.context_note && (
          <div className="hist35-uncertainty" role="note" aria-label="Assessment context limitations">
            <p>{session.assessment_context.context_note}</p>
          </div>
        )}

        <div className="hist35-reference-detail">
          <span>Session reference</span>
          <code>{session.prediction_id}</code>
        </div>

        <div className="hist35-feedback">
          <PredictionFeedback key={session.prediction_id}
            predictionId={session.prediction_id} />
        </div>

        <div className="hist35-bottom-note">
          <div>
            <strong>Important: health-awareness information only</strong>
            <p>{session.disclaimer ||
              'Historical results are not medical diagnoses and should not replace professional medical assessment.'}</p>
          </div>
          <Link to="/dashboard">Return to dashboard</Link>
        </div>
      </div>
    </section>
  )
}

export default PatientHistoryDetailPage
