function readableEvidence(item) {
  if (typeof item === 'string') return item
  return item?.display_name || item?.label || item?.text || ''
}

// This component accepts only the primary selected by the backend decision policy.
// It cannot choose a disease from an array or display model percentages.
export default function PossibleExplanations({ primary, language = 'en' }) {
  if (!primary) return null
  const swahili = language === 'sw'
  const support = Array.isArray(primary.supporting_symptoms)
    ? primary.supporting_symptoms.map(readableEvidence).filter(Boolean) : []
  return (
    <article className="consultation-candidate" aria-label={swahili ? 'Hali inayowezekana' : 'Possible explanation'}>
      <h3>{primary.display_name}</h3>
      {primary.medical_name && primary.medical_name !== primary.display_name &&
        !primary.display_name.toLowerCase().includes(primary.medical_name.toLowerCase()) && (
        <p className="consultation-medical-name">{swahili ? 'Jina la kitabibu' : 'Medical name'}: {primary.medical_name}</p>
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
