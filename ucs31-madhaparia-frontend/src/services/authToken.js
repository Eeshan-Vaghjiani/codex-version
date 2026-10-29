const TOKEN_KEY = 'respiracare_access_token'

export const AUTH_EXPIRED_EVENT =
  'respiracare:auth-expired'

export function saveAuthToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function getAuthToken() {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function clearAuthToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}

export function hasAuthToken() {
  return Boolean(getAuthToken())
}

export function notifyAuthExpired() {
  if (typeof window === 'undefined') {
    return
  }

  window.dispatchEvent(
    new Event(AUTH_EXPIRED_EVENT),
  )
}