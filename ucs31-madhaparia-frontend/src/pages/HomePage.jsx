import { Link } from 'react-router-dom'

function ArrowIcon() {
  return (
    <svg
      aria-hidden="true"
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  )
}

function MessageIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" fill="none">
      <path d="M7 8.5h18a2.5 2.5 0 0 1 2.5 2.5v11a2.5 2.5 0 0 1-2.5 2.5H14l-7 4v-4A2.5 2.5 0 0 1 4.5 22V11A2.5 2.5 0 0 1 7 8.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M10 15h12M10 19h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" fill="none">
      <rect x="5" y="5" width="22" height="22" rx="6" stroke="currentColor" strokeWidth="1.8" />
      <path d="m10.5 16 4 4 7-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CompassIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="11" stroke="currentColor" strokeWidth="1.8" />
      <path d="m20.8 11.2-3 6.6-6.6 3 3-6.6 6.6-3Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  )
}

function SymptomIllustration() {
  return (
    <figure className="hp-visual m-0">
      <div className="hp-visual-frame">
        <svg
          className="hp-illustration"
          viewBox="0 0 580 490"
          fill="none"
          role="img"
          aria-labelledby="hp-illustration-title hp-illustration-description"
        >
          <title id="hp-illustration-title">From your words to recognised symptoms</title>
          <desc id="hp-illustration-description">
            An example showing a mixed English and Kiswahili symptom description,
            followed by the symptoms Fever, Cough and Fatigue ready for review.
          </desc>

          <circle cx="476" cy="77" r="48" fill="#EDE3F5" />
          <circle cx="70" cy="414" r="35" fill="#F4EDF8" />
          <path d="M448 40v24M436 52h24" stroke="#70549A" strokeWidth="2.8" strokeLinecap="round" />
          <path d="M85 395l7 7 12-15" stroke="#70549A" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />

          <rect x="43" y="89" width="494" height="322" rx="22" fill="white" stroke="#DED6E8" strokeWidth="2" />
          <path d="M43 149h494" stroke="#DED6E8" strokeWidth="2" />
          <rect x="69" y="111" width="22" height="22" rx="6" fill="#70549A" />
          <path d="M80 116v12M74 122h12" stroke="white" strokeWidth="2" strokeLinecap="round" />
          <text x="102" y="127" fill="#2D2933" fontSize="18" fontWeight="700">Symptom understanding</text>
          <circle cx="498" cy="120" r="4" fill="#A78BC7" />
          <circle cx="514" cy="120" r="4" fill="#DED6E8" />

          <text x="75" y="183" fill="#70549A" fontSize="13" fontWeight="700" letterSpacing="1.2">YOUR WORDS</text>
          <path d="M88 204h348a13 13 0 0 1 13 13v68a13 13 0 0 1-13 13H162l-18 17v-17H88a13 13 0 0 1-13-13v-68a13 13 0 0 1 13-13Z" fill="#F4EDF8" stroke="#DED6E8" strokeWidth="1.4" />
          <text x="96" y="242" fill="#2D2933" fontSize="19" fontWeight="600">“I have fever na kikohozi</text>
          <text x="96" y="270" fill="#2D2933" fontSize="19" fontWeight="600">and I feel tired.”</text>

          <path d="M461 241h37M486 230l12 11-12 11" stroke="#70549A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          <text x="75" y="350" fill="#70549A" fontSize="13" fontWeight="700" letterSpacing="1.2">RECOGNISED FOR REVIEW</text>
          <rect x="75" y="361" width="105" height="32" rx="8" fill="#EDE3F5" />
          <rect x="190" y="361" width="108" height="32" rx="8" fill="#EDE3F5" />
          <rect x="308" y="361" width="109" height="32" rx="8" fill="#EDE3F5" />
          <text x="106" y="382" fill="#5D427F" fontSize="15" fontWeight="700">Fever</text>
          <text x="221" y="382" fill="#5D427F" fontSize="15" fontWeight="700">Cough</text>
          <text x="334" y="382" fill="#5D427F" fontSize="15" fontWeight="700">Fatigue</text>

          <circle cx="499" cy="376" r="20" fill="#70549A" />
          <path d="m490 376 6 6 12-13" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>

        {/* On narrow screens, use readable HTML instead of shrinking SVG text. */}
        <div className="hp-mobile-example">
          <div className="hp-mobile-example-header">
            <span className="hp-mobile-example-mark" aria-hidden="true">+</span>
            <strong>Symptom understanding</strong>
          </div>
          <div className="hp-mobile-example-body">
            <p className="hp-mobile-example-label">Your words</p>
            <p className="hp-mobile-example-words">
              “I have fever na kikohozi and I feel tired.”
            </p>
            <p className="hp-mobile-example-label">Recognised for review</p>
            <div className="hp-mobile-example-tags">
              <span>Fever</span>
              <span>Cough</span>
              <span>Fatigue</span>
            </div>
            <p className="hp-mobile-example-note">
              Review these symptoms before continuing.
            </p>
          </div>
        </div>
      </div>
      <figcaption className="hp-visual-caption">
        Illustrated example of symptom recognition — not a medical result.
      </figcaption>
    </figure>
  )
}

function HomePage() {
  return (
    <>
      <section className="hp-hero" aria-labelledby="hp-heading">
        <div className="rc-container">
          <div className="row align-items-center gx-xl-5 gy-5">
            <div className="col-12 col-lg-7">
              <div className="hp-hero-copy">
                <p className="hp-kicker">
                  Clearer health awareness, one step at a time
                </p>

                <h1 id="hp-heading">
                  Describe how you feel.
                  <span> Understand what comes next.</span>
                </h1>

                <p className="hp-lead">
                  Share your respiratory symptoms in English, Kiswahili,
                  or a mix of both. Review what the system understands
                  before receiving health-awareness guidance and, when
                  appropriate, a few tentative possible explanations.
                </p>

                <div className="hp-actions d-flex flex-wrap align-items-center gap-3">
                  <Link to="/register" className="btn btn-primary hp-primary-action">
                    Get started <ArrowIcon />
                  </Link>
                  <a href="#how-it-works" className="hp-secondary-action">
                    See how it works <span aria-hidden="true">↓</span>
                  </a>
                </div>

                <div className="hp-supporting-points" aria-label="Supported features">
                  <span>English + Kiswahili</span>
                  <span>Review symptoms first</span>
                  <span>A few possible explanations</span>
                </div>
              </div>
            </div>

            <div className="col-12 col-lg-5">
              <SymptomIllustration />
            </div>
          </div>
        </div>
      </section>

      <section className="hp-process" id="how-it-works" aria-labelledby="hp-process-heading">
        <div className="rc-container">
          <div className="row align-items-end gy-3 hp-process-intro">
            <div className="col-12 col-lg-7">
              <p className="hp-section-kicker">How it works</p>
              <h2 id="hp-process-heading">A straightforward process, built around your words.</h2>
            </div>
            <div className="col-12 col-lg-5">
              <p className="hp-section-description">
                You stay involved throughout. The system helps organise
                your symptoms; it does not replace a healthcare professional.
              </p>
            </div>
          </div>

          <div className="row g-4 hp-process-grid">
            <div className="col-12 col-lg-4">
              <article className="hp-step h-100">
                <div className="hp-step-top">
                  <span className="hp-step-icon"><MessageIcon /></span>
                  <span className="hp-step-number">01 / 03</span>
                </div>
                <h3>Tell us what you're feeling</h3>
                <p>Describe your symptoms naturally, including English and Kiswahili in the same sentence.</p>
              </article>
            </div>
            <div className="col-12 col-lg-4">
              <article className="hp-step h-100">
                <div className="hp-step-top">
                  <span className="hp-step-icon"><CheckIcon /></span>
                  <span className="hp-step-number">02 / 03</span>
                </div>
                <h3>Check the recognised symptoms</h3>
                <p>Review the terms the system recognised and confirm them before continuing.</p>
              </article>
            </div>
            <div className="col-12 col-lg-4">
              <article className="hp-step h-100">
                <div className="hp-step-top">
                  <span className="hp-step-icon"><CompassIcon /></span>
                  <span className="hp-step-number">03 / 03</span>
                </div>
                <h3>Read your awareness guidance</h3>
                <p>For non-urgent cases, see one possible condition and how strongly it matched. Urgent signs lead to safety guidance instead.</p>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section className="hp-safety" aria-labelledby="hp-safety-heading">
        <div className="rc-container">
          <div className="row align-items-start gx-xl-5 gy-4">
            <div className="col-12 col-lg-5">
              <p className="hp-section-kicker">An important note</p>
              <h2 id="hp-safety-heading">Awareness is not a diagnosis.</h2>
            </div>
            <div className="col-12 col-lg-7">
              <div className="hp-safety-copy">
                <p>
                  RespiraCare is an educational health-awareness tool.
                  A predicted condition is a preliminary indication, not a
                  confirmed diagnosis or a substitute for clinical assessment.
                </p>
                <p>
                  If your symptoms are severe, rapidly worsening, or you
                  need urgent help, seek medical attention promptly rather
                  than relying on a prediction.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}

export default HomePage
