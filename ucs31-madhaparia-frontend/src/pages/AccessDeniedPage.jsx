import { Link } from 'react-router-dom'

function AccessDeniedPage() {
  return (
    <section className="access-denied-page">
      <div className="access-denied-card">
        <div className="access-denied-icon">
          !
        </div>

        <span>
          Access restricted
        </span>

        <h1>
          Administrator access required.
        </h1>

        <p>
          Your RespiraCare account does not have
          permission to access this area.
        </p>

        <Link
          to="/dashboard"
          className="button button-primary"
        >
          Return to dashboard
        </Link>
      </div>
    </section>
  )
}

export default AccessDeniedPage