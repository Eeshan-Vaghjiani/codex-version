// Shown by the route guards when a saved session
// exists but the backend could not be reached to
// check it. The user stays signed in and can retry.
function SessionUnavailable({
  message,
  onRetry,
}) {
  return (
    <div className="auth-loading-page">
      <p role="alert">
        {message}
      </p>

      <button
        type="button"
        className="button button-primary"
        onClick={onRetry}
      >
        Try again
      </button>
    </div>
  )
}

export default SessionUnavailable
