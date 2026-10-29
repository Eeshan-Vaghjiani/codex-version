function readableEvidence(item) {
  if (typeof item === 'string') return item
  return item?.display_name || item?.label || item?.text || ''
}

export default function AdminModelCandidates({ predictions = [], language = 'en' }) {
  const swahili = language === 'sw'
  const candidates = predictions.slice(0, 3)

  return (
    <ol className="consultation-candidates" aria-label={swahili ? 'Hali zinazowezekana' : 'Ranked possible explanations'}>
      {candidates.map((candidate, index) => {
        const support = Array.isArray(candidate.supporting_symptoms)
          ? candidate.supporting_symptoms.map(readableEvidence).filter(Boolean) : []
        const contradicting = Array.isArray(candidate.contradicting_symptoms)
          ? candidate.contradicting_symptoms.map(readableEvidence).filter(Boolean) : []
        const score = Number(candidate.model_confidence_percent)
        const hasScore = candidate.model_confidence_percent != null &&
          Number.isFinite(score) && score >= 0 && score <= 100
        return (
          <li className="consultation-candidate" key={candidate.condition || candidate.display_name}>
            <article>
              <p className="pred34-kicker">
                {swahili ? 'Hali inayowezekana' : 'Possible explanation'} {index + 1}
              </p>
              <h3>{candidate.display_name}</h3>
              {candidate.description && <p>{candidate.description}</p>}
              {support.length > 0 && (
                <div className="consultation-evidence">
                  <strong>{swahili ? 'Dalili zinazounga mkono' : 'Symptoms that support considering this'}</strong>
                  <ul>{support.map((symptom) => <li key={symptom}>{symptom}</li>)}</ul>
                </div>
              )}
              {contradicting.length > 0 && (
                <div className="consultation-evidence">
                  <strong>{swahili ? 'Maelezo yasiyolingana sana' : 'Details that fit less well'}</strong>
                  <ul>{contradicting.map((symptom) => <li key={symptom}>{symptom}</li>)}</ul>
                </div>
              )}
              {(candidate.explanation || candidate.reasoning_summary) && <p>{candidate.explanation || candidate.reasoning_summary}</p>}
              {candidate.evidence_note && <p className="consultation-limitation">{candidate.evidence_note}</p>}
              <p className="consultation-limitation">
                {candidate.remaining_uncertainty || (swahili
                  ? 'Programu hii haiwezi kuthibitisha au kuondoa hali hii.'
                  : 'The app cannot confirm or rule out this possibility.')}
              </p>
              {hasScore && (
                <details className="consultation-model-details">
                  <summary>{swahili ? 'Maelezo ya alama ya modeli' : 'About the model ranking'}</summary>
                  <p>{swahili ? 'Alama ya modeli isiyorekebishwa' : 'Uncalibrated model score'}: {score}%.
                    {' '}{swahili ? 'Si uwezekano uliothibitishwa kwamba una hali hii.'
                      : 'This is not a validated probability that you have this condition.'}</p>
                </details>
              )}
            </article>
          </li>
        )
      })}
    </ol>
  )
}

