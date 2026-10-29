import {
  fireEvent,
  render,
  screen,
} from '@testing-library/react'
import {
  describe,
  expect,
  it,
} from 'vitest'

import PredictionFeedback from '../PredictionFeedback'

describe('PredictionFeedback', () => {
  it('tells assistive technology which answer is selected', () => {
    render(
      <PredictionFeedback predictionId="abc" />,
    )

    const yes = screen.getByRole('button', {
      name: /Yes/,
    })

    const no = screen.getByRole('button', {
      name: /No/,
    })

    expect(yes).toHaveAttribute('aria-pressed', 'false')
    expect(no).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(yes)

    expect(yes).toHaveAttribute('aria-pressed', 'true')
    expect(no).toHaveAttribute('aria-pressed', 'false')
  })

  it('announces a missing answer as an alert', () => {
    render(
      <PredictionFeedback predictionId="abc" />,
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Submit feedback',
      }),
    )

    expect(
      screen.getByRole('alert'),
    ).toHaveTextContent(
      'Please tell us whether this result was helpful.',
    )
  })
})
