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

  it('shows the dual name as the single title, with no separate medical line', () => {
    // Dual format (simple + medical in one title) replaced the old
    // separate "Medical name:" line in 2026-10-29.
    render(<PossibleExplanations primary={{ ...primary, dual_name: 'Chest infection (bronchitis)' }} />)
    expect(screen.getByText('Chest infection (bronchitis)')).toBeInTheDocument()
    expect(screen.queryByText(/Medical name:/)).not.toBeInTheDocument()
  })

  it('renders the TB note and the family note when present', () => {
    render(<PossibleExplanations primary={{ ...primary, dual_name: 'TB (tuberculosis)', tb_note: 'Having TB does not mean having HIV.' }} />)
    expect(screen.getByText('Having TB does not mean having HIV.')).toBeInTheDocument()
    render(<PossibleExplanations primary={{ ...primary, dual_name: 'Flu-like illness / common cold (viral upper respiratory infection)', is_family_answer: true, family_note: 'Family answer, not a diagnosis.' }} />)
    expect(screen.getByText('Family answer, not a diagnosis.')).toBeInTheDocument()
  })

  it('uses short Swahili labels', () => {
    render(<PossibleExplanations primary={primary} language="sw" />)
    expect(screen.getByText('Maana yake')).toBeInTheDocument()
    expect(screen.getByText('Dalili ulizoripoti')).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Hali inayowezekana' })).toBeInTheDocument()
  })
})
