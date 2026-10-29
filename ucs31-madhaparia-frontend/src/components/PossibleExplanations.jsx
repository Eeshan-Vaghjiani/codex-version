function readableEvidence(item) {
  if (typeof item === 'string') return item
  return item?.display_name || item?.label || item?.text || ''
}

// This component accepts only the primary selected by the backend decision policy.
// It cannot choose a disease from an array. The only number it may display is
// the backend's rounded whole-percent match band, labelled as a model match,
// never as a probability.
export default function PossibleExplanations({ primary, language = 'en' }) {
  if (!primary) return null
  const swahili = language === 'sw'
  const support = Array.isArray(primary.supporting_symptoms)
    ? primary.supporting_symptoms.map(readableEvidence).filter(Boolean) : []
  const bandLabel = primary.match_band ? primary.match_band.charAt(0).toUpperCase() + primary.match_band.slice(1) : null
  const hasMatch = typeof primary.match_percent_rounded === 'number' && bandLabel
  return (
    <article className="consultation-candidate" aria-label={swahili ? 'Hali inayowezekana' : 'Possible explanation'}>
      <h3>{primary.dual_name || primary.display_name}</h3>
      {hasMatch && (
        <p className="consultation-match" role="status">
          <strong>{swahili ? `${bandLabel} match` : `${bandLabel} match`} — {swahili ? `karibu ${primary.match_percent_rounded}%` : `about ${primary.match_percent_rounded}%`}</strong>
          <br />
          <span>{primary.match_label || (swahili ? 'Hii ni alama ya modeli, si uwezekano kwamba una ugonjwa huu.' : 'Model match, not a probability.')}</span>
          {primary.match_label_detail && <><br /><span>{primary.match_label_detail}</span></>}
        </p>
      )}
      {primary.is_family_answer && primary.family_note && (
        <p className="consultation-limitation"><strong>{primary.family_note}</strong></p>
      )}
      {primary.tb_note && (
        <p className="consultation-limitation">{primary.tb_note}</p>
      )}
      {primary.description && <div className="consultation-meaning">
        <h4>{swahili ? 'Maana yake' : 'What this means'}</h4>
        <p>{primary.description}</p>
      </div>}
      {(primary.explanation || primary.reasoning_summary) && <p>{primary.explanation || primary.reasoning_summary}</p>}
      {support.length > 0 && (
        <details className="consultation-evidence">
          <summary>{swahili ? 'Dalili ulizoripoti' : 'Symptoms you reported'}</summary>
          <ul>{support.map((symptom) => <li key={symptom}>{symptom}</li>)}</ul>
        </details>
      )}
      {primary.evidence_note && <p className="consultation-limitation">{primary.evidence_note}</p>}
      {primary.remaining_uncertainty && <p className="consultation-limitation">{primary.remaining_uncertainty}</p>}
      <p className="consultation-limitation">{swahili
        ? 'Hii ni hali inayowezekana, si utambuzi. Programu haiwezi kuthibitisha au kuondoa ugonjwa.'
        : 'This is a possibility, not a diagnosis. The app cannot confirm or rule out an illness.'}</p>
    </article>
  )
}
