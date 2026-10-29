
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Chart } from '@highcharts/react'
import { PieSeries } from '@highcharts/react/series/Pie'
import { ColumnSeries } from '@highcharts/react/series/Column'

import { getAdminFeedback, getAdminHistory } from '../services/admin'
import { getApiErrorMessage } from '../services/api'
import { Accessibility } from '@highcharts/react/modules/Accessibility'

const PURPLE = '#70549a'
const LILAC = '#a78bc7'
const AMBER = '#c18535'

function isUrgent(item) {
  return item.status === 'urgent_review' || item.has_red_flag === true
}

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

function statusLabel(item) {
  if (isUrgent(item)) return 'Urgent review'
  if (item.status === 'prediction_complete') return 'Prediction complete'
  return item.status ? item.status.replaceAll('_', ' ') : 'Status unavailable'
}

const baseChart = {
  chart: { backgroundColor: 'transparent', height: 280, animation: false },
  title: { text: undefined },
  legend: { enabled: false },
  plotOptions: { series: { animation: false } },
}

function AdminDashboardPage() {
  const [history, setHistory] = useState([])
  const [feedback, setFeedback] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeView, setActiveView] = useState('history')
  const [historyFilter, setHistoryFilter] = useState('all')
  const [historySearch, setHistorySearch] = useState('')
  const [feedbackSearch, setFeedbackSearch] = useState('')

  useEffect(() => {
    let active = true

    async function loadAdminData() {
      try {
        const [historyResponse, feedbackResponse] = await Promise.all([
          getAdminHistory(),
          getAdminFeedback(),
        ])
        if (!active) return
        setHistory(Array.isArray(historyResponse?.history) ? historyResponse.history : [])
        setFeedback(Array.isArray(feedbackResponse?.feedback) ? feedbackResponse.feedback : [])
      } catch (requestError) {
        if (!active) return
        if (requestError.response?.status === 403) {
          setError('Administrator access is required to view this information.')
        } else if (requestError.response?.status === 401) {
          setError('Your login session is no longer valid.')
        } else {
          setError(getApiErrorMessage(
            requestError,
            'RespiraCare could not load the administrator dashboard.',
          ))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadAdminData()
    return () => { active = false }
  }, [])

  const stats = useMemo(() => {
    const urgent = history.filter(isUrgent).length
    const helpful = feedback.filter((item) => item.was_helpful === true).length
    const notHelpful = feedback.filter((item) => item.was_helpful === false).length
    return {
      urgent,
      nonUrgent: history.length - urgent,
      helpful,
      notHelpful,
      helpfulPercent: helpful + notHelpful > 0
        ? Math.round((helpful / (helpful + notHelpful)) * 100)
        : null,
    }
  }, [history, feedback])

  const sessions = useMemo(() => {
    const term = historySearch.trim().toLowerCase()
    return history.filter((item) => {
      if (historyFilter === 'urgent' && !isUrgent(item)) return false
      if (historyFilter === 'normal' && isUrgent(item)) return false
      if (!term) return true
      return [
        item.user_id,
        item.prediction_id,
        item.input_text,
        !isUrgent(item) ? item.predictions?.[0]?.display_name : '',
      ].filter(Boolean).join(' ').toLowerCase().includes(term)
    }).sort((a, b) => {
      const first = new Date(a.created_at).getTime()
      const second = new Date(b.created_at).getTime()
      return (Number.isFinite(second) ? second : 0) -
        (Number.isFinite(first) ? first : 0)
    })
  }, [history, historyFilter, historySearch])

  const visibleFeedback = useMemo(() => {
    const term = feedbackSearch.trim().toLowerCase()
    return feedback.filter((item) => {
      if (!term) return true
      return [item.comment, item.prediction_id, item.feedback_id]
        .filter(Boolean).join(' ').toLowerCase().includes(term)
    }).sort((a, b) => {
      const first = new Date(a.created_at).getTime()
      const second = new Date(b.created_at).getTime()
      return (Number.isFinite(second) ? second : 0) -
        (Number.isFinite(first) ? first : 0)
    })
  }, [feedback, feedbackSearch])

  const ownerByPrediction = useMemo(
    () => new Map(history.map((item) => [item.prediction_id, item.user_id])),
    [history],
  )

  if (loading || error) {
    return (
      <section className="adm36-page">
        <div className="rc-container adm36-container">
          <div className="adm36-state" role={error ? 'alert' : 'status'}>
            <h1>{error ? 'Administrator data unavailable' : 'Loading administrator dashboard...'}</h1>
            <p>{error || 'Retrieving prediction and feedback records.'}</p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="adm36-page" aria-labelledby="adm36-title">
      <div className="rc-container adm36-container">
        <header className="adm36-intro">
          <p className="adm36-eyebrow">RespiraCare administration</p>
          <h1 id="adm36-title">System activity <span>overview.</span></h1>
          <p>Review saved assessments, safety-sensitive sessions and patient feedback in one place.</p>
        </header>

        <div className="row g-3 adm36-stat-row" aria-label="Administrator statistics">
          <div className="col-12 col-sm-6 col-xl-3">
            <article className="adm36-stat"><span>Saved sessions</span><strong>{history.length}</strong><p>Records returned by the history API</p></article>
          </div>
          <div className="col-12 col-sm-6 col-xl-3">
            <article className="adm36-stat"><span>Non-urgent sessions</span><strong>{stats.nonUrgent}</strong><p>No urgent flag in these records</p></article>
          </div>
          <div className="col-12 col-sm-6 col-xl-3">
            <article className="adm36-stat is-urgent"><span>Urgent reviews</span><strong>{stats.urgent}</strong><p>Safety-sensitive session records</p></article>
          </div>
          <div className="col-12 col-sm-6 col-xl-3">
            <article className="adm36-stat"><span>Feedback responses</span><strong>{feedback.length}</strong><p>{stats.helpfulPercent == null ? 'No rated feedback yet' : `${stats.helpfulPercent}% of rated responses marked helpful`}</p></article>
          </div>
        </div>

        <div className="row g-4 adm36-charts">
          <div className="col-12 col-lg-6">
            <section className="adm36-chart-panel" aria-labelledby="adm36-outcomes-title">
              <p className="adm36-kicker">Session outcomes</p>
              <h2 id="adm36-outcomes-title">Assessment routes</h2>
              <p>Based on the available administrator history records.</p>
              {history.length === 0 ? (
                <p className="adm36-chart-empty">No sessions available to chart yet.</p>
              ) : (
                <>
                  <div className="adm36-chart" aria-label="Chart of non-urgent and urgent-review session counts">
                    <Chart options={{
                      ...baseChart,
                      tooltip: { pointFormat: '<b>{point.y}</b> sessions' },
                      plotOptions: { pie: { innerSize: '65%', dataLabels: { enabled: false }, borderWidth: 0 } },
                    }}>
                      <Chart options={{
                        ...baseChart,
                        tooltip: { pointFormat: '<b>{point.y}</b> sessions' },
                        plotOptions: {
                          pie: {
                            innerSize: '65%',
                            dataLabels: { enabled: false },
                            borderWidth: 0,
                          },
                        },
                      }}>
                        <Accessibility />
                        <PieSeries name="Sessions" data={[
                          { name: 'Non-urgent', y: stats.nonUrgent, color: PURPLE },
                          { name: 'Urgent review', y: stats.urgent, color: AMBER },
                        ]} />
                      </Chart>
                    </Chart>
                  </div>
                  <div className="adm36-key"><span><i className="adm36-dot" />Non-urgent: {stats.nonUrgent}</span><span><i className="adm36-dot is-amber" />Urgent: {stats.urgent}</span></div>
                </>
              )}
            </section>
          </div>
          <div className="col-12 col-lg-6">
            <section className="adm36-chart-panel" aria-labelledby="adm36-feedback-title">
              <p className="adm36-kicker">Patient responses</p>
              <h2 id="adm36-feedback-title">Feedback overview</h2>
              <p>Helpful versus not-helpful ratings in received feedback.</p>
              {stats.helpful + stats.notHelpful === 0 ? (
                <p className="adm36-chart-empty">No rated feedback available to chart yet.</p>
              ) : (
                <>
                  <div className="adm36-chart" aria-label="Chart of helpful and not-helpful feedback counts">
                    <Chart options={{
                      ...baseChart,
                      chart: { ...baseChart.chart, type: 'column' },
                      xAxis: { categories: ['Helpful', 'Not helpful'], lineColor: '#ded6e8' },
                      yAxis: { min: 0, allowDecimals: false, title: { text: 'Responses' }, gridLineColor: '#eee9f3' },
                      tooltip: { pointFormat: '<b>{point.y}</b> responses' },
                      plotOptions: { column: { borderWidth: 0, borderRadius: 4 } },
                    }}>
                      <Chart options={{
                        ...baseChart,
                        chart: { ...baseChart.chart, type: 'column' },
                        xAxis: {
                          categories: ['Helpful', 'Not helpful'],
                          lineColor: '#ded6e8',
                        },
                        yAxis: {
                          min: 0,
                          allowDecimals: false,
                          title: { text: 'Responses' },
                          gridLineColor: '#eee9f3',
                        },
                        tooltip: { pointFormat: '<b>{point.y}</b> responses' },
                        plotOptions: {
                          column: { borderWidth: 0, borderRadius: 4 },
                        },
                      }}>
                        <Accessibility />
                        <ColumnSeries name="Feedback" data={[
                          { y: stats.helpful, color: PURPLE },
                          { y: stats.notHelpful, color: LILAC },
                        ]} />
                      </Chart>
                    </Chart>
                  </div>
                  <p className="adm36-chart-summary">{stats.helpful} helpful · {stats.notHelpful} not helpful</p>
                </>
              )}
            </section>
          </div>
        </div>

        <div className="adm36-tabs" role="group" aria-label="Administrator record view">
          <button type="button" aria-pressed={activeView === 'history'} className={activeView === 'history' ? 'is-active' : ''} onClick={() => setActiveView('history')}>
            Prediction history <span>{history.length}</span>
          </button>
          <button type="button" aria-pressed={activeView === 'feedback'} className={activeView === 'feedback' ? 'is-active' : ''} onClick={() => setActiveView('feedback')}>
            Feedback <span>{feedback.length}</span>
          </button>
        </div>

        {activeView === 'history' ? (
          <section className="adm36-record-panel" aria-labelledby="adm36-history-heading">
            <div className="adm36-record-heading">
              <div><p className="adm36-kicker">All patient sessions</p><h2 id="adm36-history-heading">Prediction history</h2></div>
              <div className="adm36-search"><label htmlFor="adm36-history-search">Search sessions</label><input className="form-control" id="adm36-history-search" type="search" placeholder="Symptoms, user or condition" value={historySearch} onChange={(event) => setHistorySearch(event.target.value)} /></div>
            </div>
            <div className="adm36-filters" role="group" aria-label="Filter sessions">
              <button type="button" aria-pressed={historyFilter === 'all'} className={historyFilter === 'all' ? 'is-active' : ''} onClick={() => setHistoryFilter('all')}>All</button>
              <button type="button" aria-pressed={historyFilter === 'normal'} className={historyFilter === 'normal' ? 'is-active' : ''} onClick={() => setHistoryFilter('normal')}>Non-urgent</button>
              <button type="button" aria-pressed={historyFilter === 'urgent'} className={historyFilter === 'urgent' ? 'is-active' : ''} onClick={() => setHistoryFilter('urgent')}>Urgent review</button>
            </div>
            <p className="adm36-showing" role="status">Showing {sessions.length} of {history.length} sessions</p>
            {sessions.length === 0 ? (
              <div className="adm36-empty"><strong>No matching sessions</strong><p>Change the filter or search to view other records.</p></div>
            ) : (
              <div className="adm36-record-list">
                {sessions.map((item) => {
                  const urgent = isUrgent(item)
                  const firstPrediction = !urgent ? item.predictions?.[0] : null
                  return (
                    <article className={`adm36-record${urgent ? ' is-urgent' : ''}`} key={item.prediction_id}>
                      <div className="adm36-record-top">
                        <div><span className="adm36-date">{formatDate(item.created_at)}</span><h3>{urgent ? 'Urgent-review session' : firstPrediction?.display_name || 'Prediction session'}</h3></div>
                        <span className={`adm36-status${urgent ? ' is-urgent' : ''}`}>{statusLabel(item)}</span>
                      </div>
                      <div className="adm36-owner"><span>Patient user ID</span><code>{item.user_id || 'Legacy / unassigned session'}</code></div>
                      <div className="adm36-description"><strong>Original description</strong><p>“{item.input_text || 'No description saved'}”</p></div>
                      <div className="adm36-details"><div><span>Age</span><strong>{item.age ?? '—'}</strong></div><div><span>Sex</span><strong>{sexLabel(item.sex)}</strong></div><div><span>Confirmed symptoms</span><strong>{item.confirmed_codes?.length ?? 0}</strong></div></div>
                      <div className="adm36-record-footer"><code>{item.prediction_id}</code><Link className="button button-secondary adm36-button" to={`/admin/history/${encodeURIComponent(item.prediction_id)}`}>View session →</Link></div>
                    </article>
                  )
                })}
              </div>
            )}
          </section>
        ) : (
          <section className="adm36-record-panel" aria-labelledby="adm36-feedback-heading">
            <div className="adm36-record-heading">
              <div><p className="adm36-kicker">Patient responses</p><h2 id="adm36-feedback-heading">Prediction feedback</h2></div>
              <div className="adm36-search"><label htmlFor="adm36-feedback-search">Search feedback</label><input className="form-control" id="adm36-feedback-search" type="search" placeholder="Comment or session ID" value={feedbackSearch} onChange={(event) => setFeedbackSearch(event.target.value)} /></div>
            </div>
            <p className="adm36-showing" role="status">Showing {visibleFeedback.length} of {feedback.length} responses</p>
            {visibleFeedback.length === 0 ? (
              <div className="adm36-empty"><strong>No matching feedback</strong><p>Feedback will appear here when patients submit a response.</p></div>
            ) : (
              <div className="adm36-record-list">
                {visibleFeedback.map((item) => (
                  <article className="adm36-record" key={item.feedback_id}>
                    <div className="adm36-record-top"><div><span className="adm36-date">{formatDate(item.created_at)}</span><h3>Patient feedback</h3></div><span className={`adm36-status${item.was_helpful === false ? ' is-negative' : ''}`}>{item.was_helpful === true ? 'Helpful' : item.was_helpful === false ? 'Not helpful' : 'No rating'}</span></div>
                    <div className="adm36-owner"><span>Patient user ID</span><code>{ownerByPrediction.get(item.prediction_id) || 'Unavailable'}</code></div>
                    <div className="adm36-description"><strong>Comment</strong><p>{item.comment || 'No additional comment was provided.'}</p></div>
                    <div className="adm36-record-footer"><code>Feedback ID: {item.feedback_id}</code><Link className="button button-secondary adm36-button" to={`/admin/history/${encodeURIComponent(item.prediction_id)}`}>Open prediction →</Link></div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        <div className="adm36-bottom-note"><strong>Administrator access only</strong><p>These records contain patient assessment information and must remain accessible only to authorised administrators. Dashboard counts reflect records returned by the current endpoints.</p></div>
      </div>
    </section>
  )
}

export default AdminDashboardPage
