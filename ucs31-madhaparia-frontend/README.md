# RespiraCare Frontend

> Current patient results use an explicit **single-primary selection decision**, with no condition name when evidence remains uncertain and no patient confidence percentages. See [UI validation and screenshots](docs/frontend_kenya_validation.md), the [full Kenya patient experience report](../KENYA_PATIENT_EXPERIENCE_REPORT.md), and [manual test cases](../RESPIRACARE_MANUAL_TEST_CASES.md). Model results have not been clinically validated for Kenyan patients.

Frontend application for the **Respiratory Health Awareness and Prediction System**.

RespiraCare is a health-awareness web application that allows users to enter respiratory symptoms, review recognised symptoms, confirm them, receive respiratory condition pattern predictions, view previous prediction sessions and provide feedback.

The application is intended for **health-awareness and educational purposes only**. It does not provide a medical diagnosis.

---

## Features

### Patient Features

- Patient account registration
- Secure patient login
- Session-based authentication
- Protected patient routes
- Respiratory symptom entry
- English, Kiswahili and mixed-language symptom input
- NLP symptom mapping
- Recognised symptom review
- Symptom confirmation
- Red-flag symptom handling
- Respiratory prediction workflow
- Ranked prediction results
- Prediction confidence information
- Patient-specific prediction history
- Prediction history detail view
- Prediction feedback submission
- Automatic expired-session handling
- Friendly network and API error states

### Administrator Features

- Administrator-only route protection
- Administrator dashboard
- Prediction session statistics
- Normal and urgent-review session counts
- Patient feedback statistics
- Cross-user prediction history review
- Prediction session detail view
- Urgent-review session inspection
- Patient feedback review

### Application Quality

- Shared Axios API client
- Automatic Bearer token authentication
- Centralised expired-session handling
- Protected route validation
- Administrator access-control validation
- Automated frontend tests
- Responsive interface
- Production build support

---

## Technology Stack

- React
- Vite
- JavaScript
- React Router
- Axios
- CSS
- Vitest
- React Testing Library
- jsdom
- Oxlint

The frontend communicates with the RespiraCare FastAPI backend through REST API endpoints.

---

## Repository

Frontend repository:

```text
ucs31-madhaparia-frontend

```

Backend repository:

```text
ucs31-madhaparia-backend
```

---

## Prerequisites

Before running RespiraCare, install:

- Node.js
- npm
- Git

The FastAPI backend must also be available for API-dependent features.

---

## Installation

Clone the frontend repository:

```bash
git clone https://github.com/RAM-AS-RAP/ucs31-madhaparia-frontend.git
```

Enter the project:

```bash
cd ucs31-madhaparia-frontend
```

Install dependencies:

```bash
npm install
```

---

## Environment Configuration

RespiraCare uses the following frontend environment variable:

```text
VITE_API_BASE_URL
```

The provided `.env.example` contains:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For local development, create a `.env` file using the same configuration when required.

- `npm run dev`: if `VITE_API_BASE_URL` is not set, the app uses `http://127.0.0.1:8000`.
- `npm run build`: `VITE_API_BASE_URL` **must** be set (in `.env` or in the hosting provider's environment settings). The build stops with an error if it is missing, so a deployed site never tries to call `127.0.0.1` on the visitor's own computer.

---

## Running the Backend

From the backend repository:

```powershell
cd ucs31-madhaparia-backend
```

Activate the virtual environment:

```powershell
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
```

Start FastAPI:

```powershell
python -m uvicorn app.main:app --reload
```

The backend normally runs at:

```text
http://127.0.0.1:8000
```

---

## Running the Frontend

From the frontend repository:

```bash
npm run dev
```

The frontend normally runs at:

```text
http://localhost:5173
```

Keep both backend and frontend terminals running when testing the complete application.

### Backend CORS setting (`FRONTEND_ORIGINS`)

The backend only accepts browser requests from the addresses listed in its `FRONTEND_ORIGINS` setting. By default this is:

```env
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

If Vite starts on a different port (for example `http://localhost:5174` because 5173 is busy), add that address to `FRONTEND_ORIGINS` in the backend `.env` and restart the backend. Otherwise every request fails in the browser with a CORS error and the app shows "could not connect to the backend".

### Backend compatibility

This frontend works with the backend `main` branch and with backend pull request [#44](https://github.com/RAM-AS-RAP/ucs31-madhaparia-backend/pull/44). The two pull requests can be merged in either order. After #44, `POST /feedback` requires the login token; the frontend already sends it.

---

## Application Routes

### Public Routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page |
| `/login` | User login |
| `/register` | Patient registration |

### Patient Routes

| Route | Purpose |
| --- | --- |
| `/dashboard` | Patient dashboard |
| `/symptoms` | Enter respiratory symptoms |
| `/symptoms/confirm` | Confirm recognised symptoms |
| `/prediction` | Prediction workflow and results |
| `/history` | Patient prediction history |
| `/history/:predictionId` | Prediction session detail |
| `/access-denied` | Access-control information |

### Administrator Routes

| Route | Purpose |
| --- | --- |
| `/admin` | Administrator dashboard |
| `/admin/history/:predictionId` | Administrator prediction detail |

Unknown routes display the 404 page.

---

## Authentication and Access Control

Authentication tokens are stored in browser session storage.

The shared Axios API client automatically adds the Bearer token to authenticated requests.

If a token expires or becomes invalid, RespiraCare:

1. Detects the authentication error.
2. Removes the invalid token.
3. Clears the active user session.
4. Redirects protected access to the login page.

Patients cannot access administrator-only routes.

Administrator roles are controlled by the backend. Public registration creates patient accounts.

---

## RespiraCare Workflow

```text
Login
  |
  v
Enter symptoms
  |
  v
NLP symptom mapping
  |
  v
Review recognised symptoms
  |
  v
Confirm symptoms
  |
  v
Red-flag safety check
  |
  v
Prediction result
  |
  v
Prediction history
  |
  v
Optional feedback
```

RespiraCare supports supported English, Kiswahili and mixed-language symptom wording.

For normal sessions, ranked respiratory condition patterns and confidence information are displayed.

When a red-flag safety rule is triggered, urgent-review guidance is shown instead of treating the result as a routine prediction.

---

## Automated Testing

The frontend uses:

- Vitest
- React Testing Library
- jest-dom
- jsdom

Run the automated tests:

```bash
npm test
```

The test suite validates:

- Protected and administrator route access (loading, redirects, access denied)
- Session restore: a 401 signs out, a network error keeps the user signed in
- Any 401 from a protected request signs the user out
- Redirect back to the requested page after login, and logout to the home page
- A saved prediction is only shown again for the same symptoms
- FastAPI validation errors (422 lists) are shown as readable text
- Accessibility basics: `aria-pressed` on toggles, `role="alert"` on errors

Current result:

```text
10 test files
37 automated tests
```

---

## Linting

Run:

```bash
npm run lint
```

Expected result:

```text
0 warnings
0 errors
```

---

## Production Build

Set `VITE_API_BASE_URL` to the deployed backend URL first, then run:

```bash
npm run build
```

Without `VITE_API_BASE_URL` the build fails with:

```text
VITE_API_BASE_URL is not set. Set it to the backend URL before running "npm run build" ...
```

Production files are generated in:

```text
dist/
```

Preview the production build with:

```bash
npm run preview
```

---

## Reproducing the Frontend

A clean environment can be reproduced with:

```bash
git clone https://github.com/RAM-AS-RAP/ucs31-madhaparia-frontend.git
cd ucs31-madhaparia-frontend
npm install
```

Configure:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the backend, then run:

```bash
npm run dev
```

Validate the installation using (the build needs `VITE_API_BASE_URL`, see above):

```bash
npm test
npm run lint
npm run build
```

Expected:

```text
37 automated tests pass
0 lint warnings
0 lint errors
Production build succeeds
```

---

## Project Structure

```text
src/
|-- assets/
|-- components/
|   |-- __tests__/
|   |-- AdminRoute.jsx
|   `-- ProtectedRoute.jsx
|-- context/
|   |-- AuthContext.jsx
|   |-- AuthContextBase.js
|   `-- useAuth.js
|-- layouts/
|   `-- AppLayout.jsx
|-- pages/
|   |-- HomePage.jsx
|   |-- LoginPage.jsx
|   |-- RegisterPage.jsx
|   |-- PatientDashboardPage.jsx
|   |-- SymptomInputPage.jsx
|   |-- SymptomConfirmationPage.jsx
|   |-- PredictionPage.jsx
|   |-- PatientHistoryPage.jsx
|   |-- PatientHistoryDetailPage.jsx
|   |-- AdminDashboardPage.jsx
|   |-- AdminHistoryDetailPage.jsx
|   |-- AccessDeniedPage.jsx
|   `-- NotFoundPage.jsx
|-- services/
|   |-- api.js
|   |-- auth.js
|   |-- authToken.js
|   |-- symptoms.js
|   |-- predictions.js
|   |-- history.js
|   |-- feedback.js
|   `-- admin.js
|-- styles/
|   `-- global.css
|-- test/
|   `-- setup.js
|-- App.jsx
`-- main.jsx
```

---

## Available Commands

```bash
npm run dev
npm test
npm run lint
npm run build
npm run preview
```

---

## Health and Safety Disclaimer

RespiraCare is a respiratory health-awareness and educational system.

It does not provide medical diagnosis, treatment or emergency medical advice.

Users should seek appropriate professional medical care for concerning, severe, persistent or emergency symptoms.

Prediction outputs represent health-awareness patterns generated by the system and should not be treated as confirmation of a medical condition.
