import { AxiosError } from 'axios'
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import api from '../api'
import { AUTH_EXPIRED_EVENT } from '../authToken'

const TOKEN_KEY = 'respiracare_access_token'

// A fake adapter that answers every request with 401,
// so no real backend is needed.
function reject401(config) {
  return Promise.reject(
    new AxiosError(
      'Request failed with status code 401',
      'ERR_BAD_REQUEST',
      config,
      null,
      {
        status: 401,
        data: {
          detail: 'Authentication required.',
        },
        headers: {},
        config,
      },
    ),
  )
}

describe('401 handling in the shared API client', () => {
  let expiredListener

  beforeEach(() => {
    sessionStorage.clear()
    expiredListener = vi.fn()
    window.addEventListener(
      AUTH_EXPIRED_EVENT,
      expiredListener,
    )
  })

  afterEach(() => {
    window.removeEventListener(
      AUTH_EXPIRED_EVENT,
      expiredListener,
    )
  })

  it('signs out on a 401 even when no token was sent', async () => {
    await expect(
      api.get('/history', {
        adapter: reject401,
      }),
    ).rejects.toBeTruthy()

    expect(expiredListener).toHaveBeenCalledTimes(1)
  })

  it('clears the token on a 401 for a protected request', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'expired-token')

    await expect(
      api.get('/history', {
        adapter: reject401,
      }),
    ).rejects.toBeTruthy()

    expect(
      sessionStorage.getItem(TOKEN_KEY),
    ).toBeNull()

    expect(expiredListener).toHaveBeenCalledTimes(1)
  })

  it('does not sign out for a wrong password at login', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'current-token')

    await expect(
      api.post(
        '/auth/login',
        {},
        {
          skipAuth: true,
          adapter: reject401,
        },
      ),
    ).rejects.toBeTruthy()

    expect(
      sessionStorage.getItem(TOKEN_KEY),
    ).toBe('current-token')

    expect(expiredListener).not.toHaveBeenCalled()
  })
})
