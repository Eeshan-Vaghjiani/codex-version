import api from './api'

export async function submitPredictionFeedback({
  predictionId,
  wasHelpful,
  comment,
}) {
  const cleanedComment = comment.trim()

  const response = await api.post(
    '/feedback',
    {
      prediction_id: predictionId,
      was_helpful: wasHelpful,
      comment:
        cleanedComment.length > 0
          ? cleanedComment
          : null,
    },
  )

  return response.data
}