import api from './api'

// Keep the cache structure while rejecting results/questions from older policies.
const PREDICTION_CACHE_VERSION = 'kenya-single-primary-2026-10-29-family-gathering'

const PREDICTION_KEY =
  'respiracare_prediction_result'

export async function createPrediction({
  age,
  sex,
  text,
  confirmedCodes,
  followUpAnswers = [],
  language,
  breathingCheck,
}) {
  const response = await api.post(
    '/predict',
    {
      age,
      sex,
      text,
      confirmed_codes: confirmedCodes,
      ...(breathingCheck && { breathing_check: breathingCheck }),
      ...(followUpAnswers.length > 0 && {
        follow_up_answers: followUpAnswers,
      }),
      ...(language && { language }),
    },
  )

  return response.data
}

export function savePredictionResult(
  prediction,
  inputText,
  requestContext,
) {
  // The backend response does not include the
  // symptom text, so it is stored alongside the
  // result. This lets the prediction page check
  // that a saved result belongs to the current
  // symptoms before showing it.
  sessionStorage.setItem(
    PREDICTION_KEY,
    JSON.stringify({
      ...prediction,
      cache_version: PREDICTION_CACHE_VERSION,
      input_text: inputText,
      ...(requestContext && { request_context: requestContext }),
    }),
  )
}

function sameCodes(first, second) {
  if (
    !Array.isArray(first) ||
    !Array.isArray(second) ||
    first.length !== second.length
  ) {
    return false
  }

  const sortedFirst = [...first].sort()
  const sortedSecond = [...second].sort()

  return sortedFirst.every(
    (code, index) =>
      code === sortedSecond[index],
  )
}

export function isPredictionForConfirmation(
  prediction,
  inputText,
  confirmedCodes,
) {
  if (!prediction) {
    return false
  }

  return (
    prediction.input_text === inputText &&
    sameCodes(
      prediction.confirmed_codes,
      confirmedCodes,
    )
  )
}

export function getSavedPredictionResult() {
  const stored =
    sessionStorage.getItem(
      PREDICTION_KEY,
    )

  if (!stored) {
    return null
  }

  try {
    const result = JSON.parse(stored)
    if (result?.cache_version !== PREDICTION_CACHE_VERSION) {
      sessionStorage.removeItem(PREDICTION_KEY)
      return null
    }
    return result
  } catch {
    sessionStorage.removeItem(
      PREDICTION_KEY,
    )

    return null
  }
}

export function clearPredictionResult() {
  sessionStorage.removeItem(
    PREDICTION_KEY,
  )
}
