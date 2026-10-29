import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import PossibleExplanations from '../PossibleExplanations'

const primary = { condition: 'example', display_name: 'Familiar name (medical name)',
  medical_name: 'Medical name', description: 'A short backend description.',
  explanation: 'Your symptoms may fit this condition.', supporting_symptoms: ['Cough'],
  model_confidence_percent: 99, confidence_explanation: 'A score of 99%.',
}

describe('One possible explanation', () => {
  it('uses backend wording and reported symptoms with a clear uncertainty statement', () => {
    render(<PossibleExplanations primary={primary} />)
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(1)
    expect(screen.getByText(primary.display_name)).toBeInTheDocument()
    expect(screen.getByText(primary.description)).toBeInTheDocument()
    expect(screen.getByText(primary.explanation)).toBeInTheDocument()
    expect(screen.getByText('Cough')).toBeInTheDocument()
    expect(screen.getByText(/This is a possibility, not a diagnosis/)).toBeInTheDocument()
    expect(screen.queryByText(/99%/)).not.toBeInTheDocument()
  })

  it('cannot select a disease from a legacy candidate array', () => {
    render(<PossibleExplanations predictions={[primary]} />)
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })

  it('labels a family answer without showing a match percentage', () => {
    render(<PossibleExplanations primary={{ ...primary, is_family_answer: true,
      display_name: 'Flu-like illness / common cold',
      score_kind: 'v3_relative_model_match', model_match_percent: 99 }} />)
    expect(screen.getByText(/family of possible illnesses/)).toBeInTheDocument()
    expect(screen.queryByText(/99%|Strong match/)).not.toBeInTheDocument()
  })

  it('retains a medical name when it differs from the familiar name', () => {
    render(<PossibleExplanations primary={{ ...primary, display_name: 'Familiar name' }} />)
    expect(screen.getByText('Medical name: Medical name')).toBeInTheDocument()
  })

  it('uses short Swahili labels', () => {
    render(<PossibleExplanations primary={primary} language="sw" />)
    expect(screen.getByText('Maana yake')).toBeInTheDocument()
    expect(screen.getByText('Dalili ulizoripoti')).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Hali inayowezekana' })).toBeInTheDocument()
  })
})
