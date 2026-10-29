import api from './api'

export async function getPatientHistory(
  limit = 20,
) {
  const response = await api.get(
    '/history',
    {
      params: {
        limit,
      },
    },
  )

  return response.data
}

export async function getPatientHistoryItem(
  predictionId,
) {
  const response = await api.get(
    `/history/${predictionId}`,
  )

  return response.data
}