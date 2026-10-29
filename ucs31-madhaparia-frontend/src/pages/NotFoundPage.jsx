import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <section className="not-found-page">
      <div className="not-found-content">
        <span>404</span>

        <h1>
          Page not found
        </h1>

        <p>
          The page you are looking for does not exist.
        </p>

        <Link
          to="/"
          className="button button-primary"
        >
          Return home
        </Link>
      </div>
    </section>
  )
}

export default NotFoundPage