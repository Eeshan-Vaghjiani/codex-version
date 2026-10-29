
import { Link } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

function ArrowIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 12h16M14 6l6 6-6 6" />
    </svg>
  )
}

function PatientDashboardPage() {
  const { user } = useAuth()

  return (
    <section
      className="patient32-page"
      aria-labelledby="patient32-title"
    >
      <div className="rc-container">

        {/* Welcome and account information */}
        <div className="row align-items-end g-4 patient32-header">
          <div className="col-12 col-lg-8">
            <p className="patient32-eyebrow">
              Patient dashboard
            </p>

            <h1 id="patient32-title">
              Welcome back.
              <span>What would you like to do today?</span>
            </h1>

            <p className="patient32-intro">
              Start a new symptom check or look back at
              your previous sessions. Everything you
              need is right here.
            </p>
          </div>

          <div className="col-12 col-lg-4">
            <div className="patient32-account">
              <span className="patient32-account-label">
                Signed in as
              </span>

              <strong>
                {user?.email || 'Email unavailable'}
              </strong>

              <span className="patient32-account-role">
                Account role: {user?.role || 'Unavailable'}
              </span>
            </div>
          </div>
        </div>

        {/* Main dashboard actions */}
        <div className="row g-4 patient32-actions">

          {/* Primary action */}
          <div className="col-12 col-lg-7">
            <article className="patient32-primary-panel">

              <div className="patient32-panel-top">
                <span>01 / START A NEW CHECK</span>
              </div>

              <div className="patient32-panel-content">
                <h2>Check your symptoms</h2>

                <p>
                  Describe how you're feeling in English,
                  Kiswahili, or a mix of both. Review the
                  symptoms the system recognises before
                  receiving health-awareness guidance and,
                  where appropriate, tentative possible explanations.
                </p>

                <Link
                  to="/symptoms"
                  className="patient32-primary-button"
                >
                  Check symptoms
                  <ArrowIcon />
                </Link>
              </div>

              <div className="patient32-panel-footer">
                <span>English + Kiswahili</span>
                <span>Review symptoms before continuing</span>
              </div>

            </article>
          </div>

          {/* History action */}
          <div className="col-12 col-lg-5">
            <article className="patient32-history-panel">

              <div className="patient32-panel-top">
                <span>02 / YOUR RECORDS</span>
              </div>

              <div className="patient32-history-content">
                <h2>Pick up where you left off.</h2>

                <p>
                  Your previous symptom checks are saved
                  to your account. Return to earlier sessions
                  to review the recorded results and
                  health-awareness guidance.
                </p>
              </div>

              <Link
                to="/history"
                className="patient32-history-link"
              >
                View prediction history
                <ArrowIcon />
              </Link>

            </article>
          </div>

        </div>

        {/* How the symptom process works */}
        <section
          className="patient32-guide"
          aria-labelledby="patient32-guide-title"
        >
          <div className="row g-4">
            <div className="col-12 col-lg-4">
              <p className="patient32-eyebrow">
                How it works
              </p>

              <h2 id="patient32-guide-title">
                Three simple steps.
              </h2>

              <p className="patient32-guide-intro">
                You'll have a chance to review your
                information before proceeding.
              </p>
            </div>

            <div className="col-12 col-lg-8">
              <ol className="patient32-steps">

                <li>
                  <span className="patient32-step-number">
                    01
                  </span>

                  <div>
                    <strong>Describe your symptoms</strong>
                    <p>
                      Tell the system how you're feeling
                      using supported language input.
                    </p>
                  </div>
                </li>

                <li>
                  <span className="patient32-step-number">
                    02
                  </span>

                  <div>
                    <strong>Review what was recognised</strong>
                    <p>
                      Check and confirm the symptoms
                      identified from your description.
                    </p>
                  </div>
                </li>

                <li>
                  <span className="patient32-step-number">
                    03
                  </span>

                  <div>
                    <strong>Receive health-awareness guidance</strong>
                    <p>
                      View appropriate guidance. Cases
                      requiring urgent attention are handled
                      separately from prediction.
                    </p>
                  </div>
                </li>

              </ol>
            </div>
          </div>
        </section>

        {/* Medical information */}
        <aside
          className="patient32-safety"
          aria-label="Important health information"
        >
          <strong>Important to know</strong>

          <p>
            RespiraCare is for health awareness, not medical
            diagnosis. Predictions are preliminary and should
            not replace professional medical advice. Seek
            prompt medical attention for severe or rapidly
            worsening symptoms.
          </p>
        </aside>

      </div>
    </section>
  )
}

export default PatientDashboardPage
