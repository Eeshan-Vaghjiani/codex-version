import api from './api'

import {
  getAuthToken,
} from './authToken'

export {
  AUTH_EXPIRED_EVENT,
  clearAuthToken,
  getAuthToken,
  hasAuthToken,
  saveAuthToken,
} from './authToken'

export async function registerPatient(
  email,
  password,
) {
  const response = await api.post(
    '/auth/register',
    {
      email,
      password,
    },
    {
      skipAuth: true,
    },
  )

  return response.data
}

export async function loginPatient(
  email,
  password,
) {
  const response = await api.post(
    '/auth/login',
    {
      email,
      password,
    },
    {
      skipAuth: true,
    },
  )

  return response.data
}

export async function getCurrentUser() {
  const token = getAuthToken()

  if (!token) {
    throw new Error(
      'Authentication token is unavailable.',
    )
  }

  const response =
    await api.get('/auth/me')

  return response.data
}