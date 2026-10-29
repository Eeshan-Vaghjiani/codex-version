import api from './api'

export async function getAdminHistory(
  limit = 500,
) {
  const response = await api.get(
    '/admin/history',
    {
      params: {
        limit,
      },
    },
  )

  return response.data
}

export async function getAdminHistoryItem(
  predictionId,
) {
  const response = await api.get(
    `/admin/history/${predictionId}`,
  )

  return response.data
}

export async function getAdminFeedback(
  limit = 500,
) {
  const response = await api.get(
    '/admin/feedback',
    {
      params: {
        limit,
      },
    },
  )

  return response.data
}