
import { useEffect, useRef, useState } from 'react'
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from 'react-router-dom'

import { useAuth } from '../context/useAuth'
import { clearPredictionResult } from '../services/predictions'
import {
  clearSymptomConfirmation,
  clearSymptomMapping,
} from '../services/symptoms'

const FOOTER_YEAR = new Date().getFullYear()

function BrandMark() {
  return (
    <svg
      width="43"
      height="43"
      viewBox="15 7 228 242"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="#b99bc9"
        d="M46 15 C34 15 24 28 23 40 V214 C23 230 34 239 52 240 C74 241 88 224 88 203 V178 C88 168 80 166 72 171 C52 181 39 194 28 212 C29 188 44 161 56 137 C76 101 88 74 88 40 C88 25 77 15 60 15 Z"
      />
      <path
        fill="#d1b7e1"
        d="M231 24 C225 22 190 21 172 24 C141 28 122 56 105 83 C89 107 76 135 66 148 C83 136 104 124 125 121 C148 117 172 116 194 103 C222 85 235 57 233 34 Z"
      />
      <path
        fill="#9677ad"
        d="M72 159 C97 155 105 162 122 181 L154 218 C171 238 183 241 205 240 C223 239 236 232 236 223 C237 214 223 201 210 185 L187 153 C164 123 140 126 117 134 C100 140 84 149 72 159 Z"
      />
      <path
        d="M181 47 V76 M166.5 61.5 H195.5"
        fill="none"
        stroke="#ffffff"
        strokeWidth="9"
        strokeLinecap="round"
      />
    </svg>
  )
}

function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const logoutPending = useRef(false)
  const menuToggleRef = useRef(null)

  // Remember the route where the menu was opened.
  // Changing routes automatically closes the menu.
  const [menuOpenAt, setMenuOpenAt] = useState(null)
  const menuOpen = menuOpenAt === location.key

  const {
    isAdmin,
    isAuthenticated,
    logout,
    user,
  } = useAuth()

  // Preserve the existing safe logout sequence.
  useEffect(() => {
    if (
      logoutPending.current &&
      location.pathname === '/'
    ) {
      logoutPending.current = false
      logout()
    }
  }, [location.pathname, logout])

  // Dismiss the mobile menu with Escape.
  // Return keyboard focus to its toggle button.
  useEffect(() => {
    if (!menuOpen) return undefined

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setMenuOpenAt(null)
        menuToggleRef.current?.focus()
      }
    }

    window.addEventListener('keydown', handleEscape)

    return () => {
      window.removeEventListener('keydown', handleEscape)
    }
  }, [menuOpen])

  function handleLogout() {
    setMenuOpenAt(null)

    clearSymptomMapping()
    clearSymptomConfirmation()
    clearPredictionResult()

    if (location.pathname === '/') {
      logout()
      return
    }

    logoutPending.current = true
    navigate('/')
  }

  const navigationItems = [
    { to: '/', label: 'Home', end: true },
    ...(isAuthenticated
      ? [{ to: '/dashboard', label: 'Dashboard', end: false }]
      : []),
    ...(isAdmin
      ? [{ to: '/admin', label: 'Admin', end: false }]
      : []),
  ]

  function navClass({ isActive }) {
    return `rc28-nav-link${isActive ? ' is-active' : ''}`
  }

  return (
    <div className="app-shell">
      {/* Navigation */}
      <header className="rc-navbar rc28-header">
        <div className="rc-container rc28-header-inner">
          <Link
            to="/"
            className="brand rc28-brand"
            onClick={() => setMenuOpenAt(null)}
          >
            <BrandMark />

            <span className="rc28-brand-copy">
              <span className="brand-name">
                RespiraCare
              </span>

              <span className="brand-subtitle">
                Respiratory Health Awareness
              </span>
            </span>
          </Link>

          {/* Desktop navigation */}
          <nav
            className="rc28-primary-nav d-none d-xl-flex"
            aria-label="Main navigation"
          >
            {navigationItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={navClass}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* Desktop account actions */}
          <div className="rc28-desktop-actions d-none d-xl-flex">
            {isAuthenticated ? (
              <>
                <div
                  className="rc28-account"
                  title={user?.email || undefined}
                >
                  <span>
                    {isAdmin ? 'Administrator' : 'Patient'}
                  </span>

                  <strong>{user?.email}</strong>
                </div>

                <button
                  type="button"
                  className="rc28-action rc28-action-outline"
                  onClick={handleLogout}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="rc28-action rc28-action-text"
                >
                  Log in
                </Link>

                <Link
                  to="/register"
                  className="rc28-action rc28-action-primary"
                >
                  Get started
                </Link>
              </>
            )}
          </div>

          {/* Tablet and mobile menu toggle */}
          <button
            type="button"
            ref={menuToggleRef}
            className="rc28-menu-toggle d-xl-none"
            aria-label={
              menuOpen
                ? 'Close navigation menu'
                : 'Open navigation menu'
            }
            aria-controls="rc28-mobile-menu"
            aria-expanded={menuOpen}
            onClick={() => {
              setMenuOpenAt((current) =>
                current === location.key ? null : location.key
              )
            }}
          >
            <svg
              viewBox="0 0 24 24"
              width="24"
              height="24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              {menuOpen ? (
                <path d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Tablet and mobile navigation */}
        <div
          id="rc28-mobile-menu"
          className="rc28-mobile-panel d-xl-none"
          hidden={!menuOpen}
        >
          <div className="rc-container rc28-mobile-panel-inner">
            <nav
              className="rc28-mobile-nav"
              aria-label="Mobile navigation"
            >
              {navigationItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={navClass}
                  onClick={() => setMenuOpenAt(null)}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            {isAuthenticated ? (
              <div className="rc28-mobile-account-actions">
                <div className="rc28-mobile-account">
                  <span>
                    {isAdmin
                      ? 'Administrator account'
                      : 'Patient account'}
                  </span>

                  <strong>{user?.email}</strong>
                </div>

                <button
                  type="button"
                  className="rc28-action rc28-action-outline"
                  onClick={handleLogout}
                >
                  Log out
                </button>
              </div>
            ) : (
              <div className="rc28-mobile-guest-actions">
                <Link
                  to="/login"
                  className="rc28-action rc28-action-outline"
                  onClick={() => setMenuOpenAt(null)}
                >
                  Log in
                </Link>

                <Link
                  to="/register"
                  className="rc28-action rc28-action-primary"
                  onClick={() => setMenuOpenAt(null)}
                >
                  Get started
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main page content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="footer rc28-footer">
        <div className="rc-container">
          <div className="row gy-4 gx-lg-5 rc28-footer-main">
            <div className="col-12 col-lg-5">
              <strong className="rc28-footer-brand">
                RespiraCare
              </strong>

              <p className="rc28-footer-description">
                Respiratory health awareness supported
                by intelligent symptom analysis.
              </p>
            </div>

            <div className="col-12 col-sm-6 col-lg-3">
              <h2 className="rc28-footer-heading">
                Explore
              </h2>

              <nav
                className="rc28-footer-links"
                aria-label="Footer navigation"
              >
                <Link to="/">
                  Explore RespiraCare
                </Link>

                {isAuthenticated ? (
                  <Link to="/dashboard">
                    Account overview
                  </Link>
                ) : (
                  <>
                    <Link to="/login">
                      Sign in
                    </Link>

                    <Link to="/register">
                      Create an account
                    </Link>
                  </>
                )}

                {isAdmin && (
                  <Link to="/admin">
                    Administration
                  </Link>
                )}
              </nav>
            </div>

            <div className="col-12 col-sm-6 col-lg-4">
              <h2 className="rc28-footer-heading">
                Important information
              </h2>

              <p className="rc28-footer-disclaimer">
                For health-awareness and educational
                purposes only. This system does not
                provide a medical diagnosis.
              </p>
            </div>
          </div>

          <div className="rc28-footer-bottom">
            <span>
              © {FOOTER_YEAR} RespiraCare
            </span>

            <span>
              Information for awareness, not diagnosis.
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default AppLayout
