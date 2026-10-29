import axios from 'axios'

import {
  clearAuthToken,
  getAuthToken,
  notifyAuthExpired,
} from './authToken'

// During local development (npm run dev) the
// backend defaults to http://127.0.0.1:8000.
// Production builds have no default: vite.config.js
// stops `npm run build` if VITE_API_BASE_URL is
// not set, so a deployed site never calls localhost.
const DEV_API_BASE_URL = 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.DEV
      ? DEV_API_BASE_URL
      : undefined),

  headers: {
    'Content-Type': 'application/json',
  },
})

function setAuthorizationHeader(
  config,
  token,
) {
  if (!config.headers) {
    config.headers = {}
  }

  if (
    typeof config.headers.set ===
    'function'
  ) {
    config.headers.set(
      'Authorization',
      `Bearer ${token}`,
    )

    return
  }

  config.headers.Authorization =
    `Bearer ${token}`
}

api.interceptors.request.use(
  (config) => {
    if (config.skipAuth === true) {
      return config
    }

    const token = getAuthToken()

    if (token) {
      setAuthorizationHeader(
        config,
        token,
      )
    }

    return config
  },
)

api.interceptors.response.use(
  (response) => response,

  (error) => {
    const status =
      error.response?.status ?? null

    // Any 401 on a protected request means the
    // session is no longer valid, including when
    // the token was removed and no Authorization
    // header was sent. Login and registration use
    // skipAuth, so a wrong password does not count.
    if (
      status === 401 &&
      error.config?.skipAuth !== true
    ) {
      clearAuthToken()
      notifyAuthExpired()
    }

    error.respiracare = {
      status,
      networkError:
        isNetworkError(error),

      message:
        getApiErrorMessage(error),
    }

    return Promise.reject(error)
  },
)

export function getApiErrorStatus(
  error,
) {
  return error.response?.status ?? null
}

export function isNetworkError(
  error,
) {
  return (
    error.code === 'ERR_NETWORK' ||
    (
      error.request &&
      !error.response
    )
  )
}

export function getApiErrorMessage(
  error,
  fallback = (
    'Something went wrong. Please try again.'
  ),
) {
  if (isNetworkError(error)) {
    return (
      'RespiraCare could not connect to the ' +
      'backend. Please make sure the API is ' +
      'running and try again.'
    )
  }

  const detail =
    error.response?.data?.detail

  if (
    typeof detail === 'string' &&
    detail.trim()
  ) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter(Boolean)

    if (messages.length > 0) {
      return messages.join(' ')
    }
  }

  return fallback
}

export default api