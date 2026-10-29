import {
  describe,
  expect,
  it,
} from 'vitest'

import { getApiErrorMessage } from '../api'

const validationError = {
  response: {
    status: 422,
    data: {
      detail: [
        {
          type: 'value_error',
          loc: ['body', 'email'],
          msg: 'value is not a valid email address',
          input: 'someone@localhost',
        },
        {
          type: 'string_too_short',
          loc: ['body', 'password'],
          msg: 'String should have at least 8 characters',
          input: 'abc',
        },
      ],
    },
  },
}

describe('getApiErrorMessage', () => {
  it('joins the messages of a FastAPI validation list', () => {
    expect(
      getApiErrorMessage(validationError),
    ).toBe(
      'value is not a valid email address String should have at least 8 characters',
    )
  })

  it('always returns a string', () => {
    expect(
      typeof getApiErrorMessage(validationError),
    ).toBe('string')
  })

  it('returns a string detail unchanged', () => {
    expect(
      getApiErrorMessage({
        response: {
          status: 400,
          data: {
            detail: 'Prediction session was not found.',
          },
        },
      }),
    ).toBe('Prediction session was not found.')
  })

  it('uses the fallback when there is no detail', () => {
    expect(
      getApiErrorMessage(
        {
          response: {
            status: 500,
            data: {},
          },
        },
        'Fallback message',
      ),
    ).toBe('Fallback message')
  })

  it('explains a network error in plain language', () => {
    expect(
      getApiErrorMessage({
        code: 'ERR_NETWORK',
        message: 'Network Error',
      }),
    ).toContain('could not connect to the backend')
  })
})
