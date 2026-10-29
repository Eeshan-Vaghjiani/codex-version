import api from './api'

const MAPPING_KEY = 'respiracare_symptom_mapping'
const CONFIRMATION_KEY = 'respiracare_symptom_confirmation'

export async function mapSymptoms(text, breathingCheck) {
  const response = await api.post('/nlp/map', {
    text,
    ...(breathingCheck && { breathing_check: breathingCheck }),
  })

  return response.data
}

export async function confirmSymptoms(
  text,
  confirmedCodes,
) {
  const response = await api.post(
    '/symptoms/confirm',
    {
      text,
      confirmed_codes: confirmedCodes,
    },
  )

  return response.data
}

export function saveSymptomMapping(mapping) {
  sessionStorage.setItem(
    MAPPING_KEY,
    JSON.stringify(mapping),
  )
}

export function getSavedSymptomMapping() {
  const stored =
    sessionStorage.getItem(MAPPING_KEY)

  if (!stored) {
    return null
  }

  try {
    return JSON.parse(stored)
  } catch {
    sessionStorage.removeItem(MAPPING_KEY)
    return null
  }
}

export function clearSymptomMapping() {
  sessionStorage.removeItem(MAPPING_KEY)
}

export function saveSymptomConfirmation(
  confirmation,
) {
  sessionStorage.setItem(
    CONFIRMATION_KEY,
    JSON.stringify(confirmation),
  )
}

export function getSavedSymptomConfirmation() {
  const stored =
    sessionStorage.getItem(CONFIRMATION_KEY)

  if (!stored) {
    return null
  }

  try {
    return JSON.parse(stored)
  } catch {
    sessionStorage.removeItem(
      CONFIRMATION_KEY,
    )

    return null
  }
}

export function clearSymptomConfirmation() {
  sessionStorage.removeItem(
    CONFIRMATION_KEY,
  )
}
