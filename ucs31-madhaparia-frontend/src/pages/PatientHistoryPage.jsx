
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../services/api'
import { getPatientHistory } from '../services/history'
import { getPatientPrimary } from '../services/patientResult'

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

function isUrgentSession(item) {
  return item.status === 'urgent_review' || item.care_level === 'urgent_review' || item.has_red_flag === true
}

function statusLabel(item) {
  if (isUrgentSession(item)) return 'Urgent review'
  if (getPatientPrimary(item)) return 'Possible explanation'
  if (item.status === 'reassessment_required') return 'New check needed'
  if (item.status === 'needs_follow_up') return 'Follow-up needed'
  if (['assessment_uncertain', 'insufficient_evidence', 'prediction_complete'].includes(item.status)) return 'More information needed'
  return item.status ? item.status.replaceAll('_', ' ') : 'Status unavailable'
}

function PatientHistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    let active = true

    async function loadHistory() {
      try {
        const data = await getPatientHistory()
        if (active) {
          setHistory(Array.isArray(data?.history) ? data.history : [])
        }
      } catch (requestError) {
        if (!active) return
        setError(
          requestError.response?.status === 401
            ? 'Your login session is no longer valid. Please log in again.'
            : getApiErrorMessage(
                requestError,
                'RespiraCare could not load your prediction history.',
              ),
        )
      } finally {
        if (active) setLoading(false)
      }
    }

    loadHistory()
    return () => {
      active = false
    }
  }, [])

  const urgentCount = history.filter(isUrgentSession).length
  const searchTerm = search.trim().toLowerCase()

  const visibleHistory = history
    .filter((item) => {
      const urgent = isUrgentSession(item)
      if (filter === 'urgent' && !urgent) return false
      if (filter === 'complete' && urgent) return false
      if (!searchTerm) return true

      const searchable = [
        item.input_text,
        getPatientPrimary(item)?.display_name,
        item.prediction_id,
      ].filter(Boolean).join(' ').toLowerCase()

      return searchable.includes(searchTerm)
    })
    .sort((a, b) => {
      const first = new Date(a.created_at).getTime()
      const second = new Date(b.created_at).getTime()
      return (Number.isFinite(second) ? second : 0) -
        (Number.isFinite(first) ? first : 0)
    })

  return (
    <section className="hist35-page" aria-labelledby="hist35-title">
      <div className="rc-container hist35-container">
        <div className="hist35-intro">
          <div>
            <p className="hist35-eyebrow">Patient history</p>
            <h1 id="hist35-title">
              Your previous <span>health-awareness sessions.</span>
            </h1>
            <p className="hist35-lead">
              Review the symptom descriptions, saved results and safety
              guidance from your previous assessments.
            </p>
          </div>
          <Link to="/symptoms" className="button button-primary hist35-button">
            New symptom check <span aria-hidden="true">→</span>
          </Link>
        </div>

        {loading && (
          <div className="hist35-state" role="status">
            <div className="auth-spinner" aria-hidden="true" />
            <h2>Loading your history...</h2>
            <p>Retrieving your saved assessment sessions.</p>
          </div>
        )}

        {!loading && error && (
          <div className="hist35-state hist35-state-error" role="alert">
            <h2>History could not be loaded</h2>
            <p>{error}</p>
            <Link className="button button-secondary hist35-button" to="/dashboard">
              Return to dashboard
            </Link>
          </div>
        )}

        {!loading && !error && history.length === 0 && (
          <div className="hist35-state">
            <p className="hist35-empty-number">0 sessions</p>
            <h2>No prediction history yet</h2>
            <p>Your completed assessments will appear here once saved.</p>
            <Link className="button button-primary hist35-button" to="/symptoms">
              Check symptoms
            </Link>
          </div>
        )}

        {!loading && !error && history.length > 0 && (
          <>
            <div className="hist35-overview" aria-label="History overview">
              <div>
                <span>Saved sessions</span>
                <strong>{history.length}</strong>
              </div>
              <div>
                <span>Urgent reviews</span>
                <strong>{urgentCount}</strong>
              </div>
              <p>Most recent sessions first</p>
            </div>

            <div className="hist35-toolbar">
              <div className="hist35-filters" role="group" aria-label="Filter history">
                <button type="button" className={filter === 'all' ? 'is-active' : ''}
                  aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>
                  All sessions
                </button>
                <button type="button" className={filter === 'complete' ? 'is-active' : ''}
                  aria-pressed={filter === 'complete'} onClick={() => setFilter('complete')}>
                  Assessments
                </button>
                <button type="button" className={filter === 'urgent' ? 'is-active' : ''}
                  aria-pressed={filter === 'urgent'} onClick={() => setFilter('urgent')}>
                  Urgent review
                </button>
              </div>
              <div className="hist35-search">
                <label htmlFor="hist35-search-input">Search history</label>
                <input id="hist35-search-input" className="form-control"
                  value={search} onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search symptoms or conditions" type="search" />
              </div>
            </div>

            <p className="hist35-showing" role="status">
              Showing {visibleHistory.length} of {history.length} saved sessions
            </p>

            {visibleHistory.length === 0 ? (
              <div className="hist35-state">
                <h2>No matching sessions</h2>
                <p>Try a different search or change the selected filter.</p>
                <button type="button" className="button button-secondary hist35-button"
                  onClick={() => { setFilter('all'); setSearch('') }}>
                  Clear filters
                </button>
              </div>
            ) : (
              <div className="hist35-list">
                {visibleHistory.map((item) => {
                  const urgent = isUrgentSession(item)
                  const topPrediction = getPatientPrimary(item)

                  return (
                    <article className={`hist35-session${urgent ? ' is-urgent' : ''}`}
                      key={item.prediction_id}>
                      <div className="hist35-session-top">
                        <div>
                          <p className="hist35-date">{formatDate(item.created_at)}</p>
                          <h2>{urgent ? 'Urgent-review session' :
                            topPrediction ? 'Possible explanation' : 'More information needed'}</h2>
                        </div>
                        <span className={`hist35-status${urgent ? ' is-urgent' : ''}`}>
                          {statusLabel(item)}
                        </span>
                      </div>

                      <div className="hist35-quote">
                        <strong>Original symptom description</strong>
                        <p>“{item.input_text || 'No description saved'}”</p>
                      </div>

                      <div className="hist35-metadata">
                        <div><span>Age</span><strong>{item.age ?? '—'}</strong></div>
                        <div><span>Sex</span><strong>{sexLabel(item.sex)}</strong></div>
                        <div><span>Confirmed symptoms</span>
                          <strong>{item.confirmed_codes?.length ?? 0}</strong></div>
                      </div>

                      {urgent ? (
                        <div className="hist35-urgent-note">
                          <strong>Safety-sensitive assessment</strong>
                          <p>This session followed the urgent-review route rather than automated disease prediction.</p>
                        </div>
                      ) : topPrediction && (
                        <div className="hist35-result-preview">
                          <div>
                            <span>Possible explanation</span>
                            <strong>{topPrediction.display_name}</strong>
                          </div>
                        </div>
                      )}

                      <div className="hist35-session-bottom">
                        <div className="hist35-reference">
                          <span>Session reference</span>
                          <code>{item.prediction_id}</code>
                        </div>
                        <Link className="button button-secondary hist35-button"
                          to={`/history/${encodeURIComponent(item.prediction_id)}`}>
                          View details <span aria-hidden="true">→</span>
                        </Link>
                      </div>
                    </article>
                  )
                })}
              </div>
            )}
          </>
        )}

        <div className="hist35-bottom-note">
          <div>
            <strong>Health-awareness information only</strong>
            <p>Historical model results are not medical diagnoses and cannot confirm or rule out an illness.</p>
          </div>
          <Link to="/dashboard">Return to dashboard</Link>
        </div>
      </div>
    </section>
  )
}

export default PatientHistoryPage
