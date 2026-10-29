
import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'

import AdminRoute from './components/AdminRoute'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './layouts/AppLayout'
import AccessDeniedPage from './pages/AccessDeniedPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import PatientDashboardPage from './pages/PatientDashboardPage'
import RegisterPage from './pages/RegisterPage'
import SymptomInputPage from './pages/SymptomInputPage'
import SymptomConfirmationPage from './pages/SymptomConfirmationPage'
import PredictionPage from './pages/PredictionPage'
import PatientHistoryPage from './pages/PatientHistoryPage'
import PatientHistoryDetailPage from './pages/PatientHistoryDetailPage'

// Load administrator pages only when they are needed.
const AdminDashboardPage = lazy(
  () => import('./pages/AdminDashboardPage'),
)

const AdminHistoryDetailPage = lazy(
  () => import('./pages/AdminHistoryDetailPage'),
)

function AdminPageLoading() {
  return (
    <section
      className="rc-container"
      role="status"
      aria-live="polite"
      style={{ padding: '48px 0' }}
    >
      <p>Loading administrator page...</p>
    </section>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />

        <Route path="/login" element={<LoginPage />} />

        <Route path="/register" element={<RegisterPage />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <PatientDashboardPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/symptoms"
          element={
            <ProtectedRoute>
              <SymptomInputPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/symptoms/confirm"
          element={
            <ProtectedRoute>
              <SymptomConfirmationPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/prediction"
          element={
            <ProtectedRoute>
              <PredictionPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <PatientHistoryPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/history/:predictionId"
          element={
            <ProtectedRoute>
              <PatientHistoryDetailPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin"
          element={
            <AdminRoute>
              <Suspense fallback={<AdminPageLoading />}>
                <AdminDashboardPage />
              </Suspense>
            </AdminRoute>
          }
        />

        <Route
          path="/admin/history/:predictionId"
          element={
            <AdminRoute>
              <Suspense fallback={<AdminPageLoading />}>
                <AdminHistoryDetailPage />
              </Suspense>
            </AdminRoute>
          }
        />

        <Route
          path="/access-denied"
          element={
            <ProtectedRoute>
              <AccessDeniedPage />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
