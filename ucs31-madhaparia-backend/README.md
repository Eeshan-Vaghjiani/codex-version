> Live model: **V3 partial-evidence, 21 conditions, 34 features; simulated DDXPlus only; not clinically validated for patients in Kenya. V2 is not live.** Names are currently withheld because a fresh-fold gap threshold cannot be validated with the missing datasets. Selected-result presentation supports a rounded whole-percent **model match**, never a patient probability or overall accuracy; no score is shown for withheld or urgent results. See the [current README](../README.md), [defence one-pager](../README_DEFENCE.md) and [validation record](../audit-artifacts/VALIDATION_2026-10-29.md). After migrations, seed the symptom catalogue and model version. Legacy sections below are historical, not the patient contract.

# Respiratory Health Awareness Backend

Backend API for the **Respiratory Health Awareness and Prediction System**.

The system accepts respiratory symptom descriptions in English, Kiswahili, or mixed-language text, maps and confirms symptoms, checks reported warning signs, and asks bounded follow-up questions. The active V3 likelihood model and a separately evaluated selection policy provide at most one possible condition. Earlier Random Forest models remain available for internal comparison.

The system also provides secure user authentication, patient-specific prediction history, role-based access control, administrator history access, and PostgreSQL data storage.

The system is designed for **health-awareness purposes only** and does not provide a medical diagnosis.

---

## Features

The backend provides:

- FastAPI REST API
- English and Kiswahili symptom mapping
- Mixed-language symptom input
- Fuzzy symptom matching
- Symptom confirmation and rejection
- Red-flag symptom detection
- Safety-only red-flag handling
- V3 partial-evidence ranking with selective abstention
- At most one patient condition, only when the checked V3 bucket + scope + gap
  policy permits; sparse patterns are withheld
- User-friendly disease names
- Plain-English condition descriptions
- Model-confidence explanation
- Health-awareness guidance
- PostgreSQL prediction storage
- User account registration and login
- Secure Argon2 password hashing
- JWT-based authentication
- Patient-specific prediction ownership
- Patient-specific prediction history
- Role-based access control
- Administrator access to all prediction histories
- Administrator access to feedback records
- User feedback storage
- Duplicate feedback protection
- API validation and error handling
- Alembic database migrations
- Automated backend tests

---

## Technology Stack

- Python 3.11
- FastAPI
- Uvicorn
- Pydantic
- Pydantic Settings
- scikit-learn
- pandas
- NumPy
- joblib
- RapidFuzz
- SQLAlchemy
- Alembic
- PostgreSQL
- Neon PostgreSQL
- Psycopg
- PyJWT
- pwdlib
- Argon2 password hashing
- email-validator
- pytest
- HTTPX

---

## Project Structure

```text
ucs31-madhaparia-backend/
│
├── alembic/
│   ├── versions/
│   │   ├── cbf545f55898_baseline_existing_schema.py
│   │   ├── 7e65fb049ca7_add_users_table.py
│   │   ├── c789b43ef979_link_prediction_sessions_to_users.py
│   │   ├── 15b0fe7743ef_add_symptom_catalog_tables.py
│   │   ├── b686b7b5730a_add_model_version_tracking.py
│   │   └── a3f1c9d27b64_add_unique_feedback_per_prediction.py
│   │
│   ├── env.py
│   ├── README
│   └── script.py.mako
│
├── app/
│   ├── core/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── errors.py
│   │   └── security.py
│   │
│   ├── data/
│   │   └── condition_information.json
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── create_admin.py
│   │   ├── models.py
│   │   ├── seed_model_version.py
│   │   └── seed_symptom_catalog.py
│   │
│   ├── ml/
│   │   ├── artifacts/
│   │   │   ├── disease_classes.json
│   │   │   ├── model_features.json
│   │   │   ├── model_metadata.json
│   │   │   └── respiratory_random_forest_v1.joblib
│   │   │
│   │   └── model_loader.py
│   │
│   ├── nlp/
│   │   ├── canonical_symptoms.json
│   │   ├── english_aliases.json
│   │   ├── feature_catalog.json
│   │   ├── swahili_aliases.json
│   │   └── symptom_mapper.py
│   │
│   ├── services/
│   │   ├── auth.py
│   │   ├── health_guidance.py
│   │   ├── history.py
│   │   ├── model_versions.py
│   │   ├── prediction.py
│   │   └── symptom_confirmation.py
│   │
│   └── main.py
│
├── tests/
│   ├── conftest.py
│   ├── test_admin_access.py
│   ├── test_authentication.py
│   ├── test_basic_endpoints.py
│   ├── test_end_to_end.py
│   ├── test_history_feedback.py
│   ├── test_nlp_confirmation.py
│   ├── test_prediction_validation.py
│   ├── test_service_readiness.py
│   └── test_symptom_catalog.py
│
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Machine Learning Model

The backend integrates the trained production Random Forest model from the machine-learning repository.

The model uses:

- 198 model input features
- Age
- Sex
- 196 selected symptom/evidence features
- 21 respiratory-related condition classes

The following production artifacts are stored in:

```text
app/ml/artifacts/
```

Artifacts:

```text
disease_classes.json
model_features.json
model_metadata.json
respiratory_random_forest_v1.joblib
```

The backend loads and validates these artifacts when the application starts.

The prediction endpoint returns the top three model condition patterns.

Model confidence values describe how strongly the supplied symptom pattern matched patterns learned by the model. They are **not probabilities that the patient has a particular disease**.

---

## NLP Symptom Processing

The NLP component supports:

- English symptom descriptions
- Kiswahili symptom descriptions
- Mixed English/Kiswahili input
- Symptom aliases
- Fuzzy spelling matching
- Unmatched wording detection
- Red-flag symptom detection
- Symptom confirmation before prediction

Example input:

```text
I have fever na kikohozi
```

The NLP system can recognise symptoms such as:

```text
fever
cough
```

The user must confirm recognised symptoms before they are used for prediction.

---

## Red-Flag Safety Handling

Some symptom patterns are treated as red flags.

If a confirmed red-flag symptom is detected:

- Normal prediction output is suppressed
- The session status becomes `urgent_review`
- Health-awareness guidance recommends urgent medical assessment

The red-flag mapping is part of the project safety logic and is not intended to represent a complete clinical triage system.

---

## Authentication

The backend provides user registration and login using JWT-based authentication.

Authentication endpoints:

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

Passwords are never stored in plain text.

Passwords are hashed using Argon2 before being stored in PostgreSQL.

JWT access tokens contain:

- User ID
- User role
- Expiration time

The JWT secret is loaded from the local `.env` file and is not committed to Git.

`JWT_SECRET_KEY` is required. The application refuses to start if it is missing, shorter than 32 characters, or still set to a placeholder value.

---

## User Roles

The backend currently supports:

```text
patient
admin
```

### Patient

A patient can:

- Register
- Login
- Submit authenticated predictions
- View their own prediction history
- Retrieve their own individual prediction records

A patient cannot:

- View another patient's prediction history
- Retrieve another patient's prediction by UUID
- Access administrator endpoints

### Administrator

An administrator can:

- View all stored prediction histories
- Retrieve any stored prediction by ID
- View all stored feedback records

Public registration always creates:

```text
role = patient
```

The public registration endpoint does not allow a user to create an administrator account.

Administrator accounts are created from the command line:

```bash
python -m app.db.create_admin admin@example.com
```

If the email already belongs to a registered user, that user is promoted to `admin` and keeps their password. Otherwise a new administrator account is created and the password is asked for interactively (or read from the `ADMIN_PASSWORD` environment variable).

---

## Prediction Ownership

Every new authenticated prediction is linked to the logged-in patient using:

```text
prediction_sessions.user_id
```

Database relationship:

```text
users.id
   ↓
prediction_sessions.user_id
```

The foreign key uses:

```text
ON DELETE SET NULL
```

This allows historical prediction records to remain available even if a user account is removed.

Older prediction records created before authentication was introduced may contain:

```text
user_id = NULL
```

---

## Patient Prediction History

Authenticated patients can access:

```text
GET /history
GET /history/{prediction_id}
```

`GET /history` returns only records belonging to the authenticated patient.

Patients cannot view another user's records.

If a patient attempts to access another patient's prediction UUID, the API returns:

```text
404 Not Found
```

This avoids revealing whether another user's prediction record exists.

Unauthenticated history requests return:

```text
401 Unauthorized
```

---

## Administrator Access

Administrator-only endpoints:

```text
GET /admin/history
GET /admin/history/{prediction_id}
GET /admin/feedback
```

Access rules:

```text
Guest   → 401 Unauthorized
Patient → 403 Forbidden
Admin   → Allowed
```

Administrators can view all prediction sessions, including older records that have no linked user.

---

## Feedback

Feedback can be submitted using:

```text
POST /feedback
```

Feedback requires authentication. A patient can only submit feedback for their own prediction sessions.

For a prediction that does not exist or belongs to another user, the API returns:

```text
404 Not Found
```

Feedback contains:

- Prediction session ID
- Whether the information was helpful
- Optional comment
- Creation timestamp

Only one feedback record can be submitted for a prediction session.

Duplicate feedback submissions are rejected.

Administrators can retrieve stored feedback through:

```text
GET /admin/feedback
```

---

## Database

The backend uses PostgreSQL.

Development and project testing use a hosted Neon PostgreSQL database.

Main tables:

### `users`

Stores:

- User ID
- Email
- Password hash
- Role
- Account creation time

### `prediction_sessions`

Stores:

- Prediction ID
- User ID
- Age
- Sex
- Original symptom text
- Confirmed symptom codes
- Model features
- Prediction status
- Red-flag status
- Prediction results
- Creation time

### `feedback`

Stores:

- Feedback ID
- Prediction session ID
- Helpful/not helpful value
- Optional comment
- Creation time

### `symptoms`

Stores the canonical symptom catalogue:

- Symptom code
- Display name
- Model features
- Kind
- Red-flag status

### `symptom_aliases`

Stores the English and Kiswahili wording for each symptom.

### `model_versions`

Stores the trained model versions and which one is active.

The `symptoms`, `symptom_aliases` and `model_versions` tables are filled by the seed commands described in the installation steps.

### `alembic_version`

Stores the currently applied database migration revision.

---

## Database Migrations

Database schema changes are managed using Alembic.

Current migration history includes:

```text
cbf545f55898
Baseline existing schema

7e65fb049ca7
Add users table

c789b43ef979
Link prediction sessions to users

15b0fe7743ef
Add symptom catalog tables

b686b7b5730a
Add model version tracking

a3f1c9d27b64
Add unique feedback per prediction
```

Alembic is the only place where tables are created. The application does not create tables on startup; if the migrations have not been applied it stops with a message asking you to run `python -m alembic upgrade head`.

The baseline migration creates `prediction_sessions` and `feedback` only when they are missing, so the same command works on an empty database and on a database that already contains those tables.

Check the current migration:

```bash
python -m alembic current
```

Apply migrations:

```bash
python -m alembic upgrade head
```

Check whether model changes require another migration:

```bash
python -m alembic check
```

A clean schema should return:

```text
No new upgrade operations detected.
```

---

## Environment Configuration

Create a local:

```text
.env
```

file in the project root.

Example:

```env
APP_NAME=Respiratory Health Awareness API
APP_ENV=development

DATABASE_URL=postgresql+psycopg://user:password@host/database_name?sslmode=require

JWT_SECRET_KEY=replace_with_a_secure_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`JWT_SECRET_KEY` must be replaced with a random value of at least 32 characters. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`FRONTEND_ORIGINS` is a comma-separated list of the frontend addresses that are allowed to call the API (CORS).

Do not commit the real `.env` file.

The repository contains:

```text
.env.example
```

with safe placeholder values only.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/RAM-AS-RAP/ucs31-madhaparia-backend.git
```

Move into the project:

```bash
cd ucs31-madhaparia-backend
```

---

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it.

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
source .venv/bin/activate
```

On Linux / macOS use `python3 -m venv .venv` if `python` is not available. All remaining commands are the same on every platform once the virtual environment is active.

---

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

For development and testing:

```bash
python -m pip install -r requirements-dev.txt
```

---

### 4. Configure environment variables

Create:

```text
.env
```

from:

```text
.env.example
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Linux / macOS:

```bash
cp .env.example .env
```

Then provide the real PostgreSQL connection string and a real JWT secret (see "Environment Configuration" above). The application will not start with the placeholder secret.

---

### 5. Apply database migrations

```bash
python -m alembic upgrade head
```

This creates all tables, including on a completely empty database.

---

### 6. Load the reference data

```bash
python -m app.db.seed_symptom_catalog
python -m app.db.seed_model_version
```

The first command loads the symptom catalogue and the English/Kiswahili aliases into the database. The second registers the bundled model as the active model version.

Both commands are safe to run again.

Until they have been run, `POST /nlp/map`, `POST /symptoms/confirm` and `POST /predict` return `503 Service Unavailable` with a message naming the command that is missing.

---

### 7. Create an administrator (optional)

```bash
python -m app.db.create_admin admin@example.com
```

---

## Running the Backend

Start the FastAPI server:

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

---

## API Endpoints

### General

```text
GET /
GET /health
GET /database/status
GET /model/status
```

### Authentication

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

### NLP and Symptom Confirmation

```text
POST /nlp/map
POST /symptoms/confirm
```

### Prediction

```text
POST /predict
```

`POST /predict` requires authentication.

New predictions are linked to the authenticated patient's user ID.

### Patient History

```text
GET /history
GET /history/{prediction_id}
```

Both endpoints require authentication.

Patients can access only their own prediction records.

### Administrator

```text
GET /admin/history
GET /admin/history/{prediction_id}
GET /admin/feedback
```

These endpoints require an authenticated administrator account.

### Feedback

```text
POST /feedback
```

`POST /feedback` requires authentication and only accepts the caller's own predictions.

---

## Example Authentication Flow

### 1. Register

```text
POST /auth/register
```

Example:

```json
{
  "email": "patient@example.com",
  "password": "TestPassword123!"
}
```

The new account is created with:

```text
role = patient
```

---

### 2. Login

```text
POST /auth/login
```

Example:

```json
{
  "email": "patient@example.com",
  "password": "TestPassword123!"
}
```

Successful login returns:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in_minutes": 60
}
```

---

### 3. Use the Access Token

Protected routes require:

```text
Authorization: Bearer <access_token>
```

Examples of protected routes:

```text
POST /predict
POST /feedback
GET /history
GET /history/{prediction_id}
GET /auth/me
```

---

## Example Prediction Request

```text
POST /predict
```

Example:

```json
{
  "age": 25,
  "sex": "M",
  "text": "I have fever na kikohozi",
  "confirmed_codes": [
    "fever",
    "cough"
  ]
}
```

The request requires a valid authenticated user.

A successful response includes:

- Prediction ID
- Status
- Confirmed symptoms
- Model features
- Red-flag status
- Top-three condition patterns
- Model-confidence explanation
- Health-awareness guidance
- Disclaimer

---

## Automated Tests

Tests are located in:

```text
tests/
```

Current test files:

```text
conftest.py
test_admin_access.py
test_authentication.py
test_basic_endpoints.py
test_end_to_end.py
test_history_feedback.py
test_nlp_confirmation.py
test_prediction_validation.py
test_service_readiness.py
test_symptom_catalog.py
```

### Test database

The tests never use the database configured in `.env`.

They need `TEST_DATABASE_URL` to point at a PostgreSQL database that is safe to use for testing, for example a local one:

Windows (PowerShell):

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/respiratory_test"
```

Linux / macOS:

```bash
export TEST_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/respiratory_test"
```

For each run, `tests/conftest.py` creates a temporary schema inside that database, applies the Alembic migrations, seeds the symptom catalogue and model version, and drops the schema again at the end. No `.env` file and no manual seeding are needed to run the tests.

The automated test suite covers:

### Authentication

- Email normalisation
- Password hashing
- Correct password verification
- Incorrect password rejection
- JWT creation
- JWT decoding
- JWT expiration
- Invalid JWT rejection
- Patient registration
- Duplicate registration protection
- Invalid email validation
- Password length validation
- Login success
- Invalid login
- `/auth/me` authentication

### Prediction

- Normal prediction
- Red-flag prediction handling
- Authentication requirement
- Invalid age
- Invalid sex
- Invalid confirmed symptoms
- Required confirmed model features
- Patient prediction ownership

### Patient History

- Guest history rejection
- Patient history access
- Patient-specific history filtering
- Individual history retrieval
- Cross-user prediction blocking

### Administrator Access

- Guest admin-access rejection
- Patient admin-access rejection
- Administrator history access
- Administrator individual prediction access
- Administrator feedback access
- Missing admin history record handling

### NLP

- Mixed English/Kiswahili input
- Fuzzy spelling
- Unmatched wording
- Symptom confirmation
- Partial confirmation
- Red-flag confirmation
- Safety-only red flags
- Invalid confirmation

### Feedback

- Feedback submission
- Authentication requirement
- Unknown prediction handling
- Duplicate feedback rejection
- Comment length validation

### End-to-end

- Register, login, symptom mapping, prediction, history and feedback against a real database, with nothing mocked

### Service readiness and limits

- `503` when the symptom catalogue has not been seeded
- `503` when no active model version is configured
- Symptom text length limit
- Confirmed symptom count limit
- Rejection of missing, placeholder or short JWT secrets

Run the full suite with:

```bash
python -m pytest -v
```

Latest verified result:

```text
74 passed
0 failed
1 warning
```

The warning is an existing FastAPI/Starlette TestClient deprecation warning and does not cause a test failure.

---

## Security

The backend currently provides:

- Argon2 password hashing
- JWT authentication
- Token expiration
- Authentication requirements on private routes
- Patient-specific prediction ownership
- Patient-specific history filtering
- Role-based administrator access
- Cross-user history protection
- Unique user emails
- Environment-based JWT secret configuration
- Environment-based database credentials

Sensitive values such as:

```text
DATABASE_URL
JWT_SECRET_KEY
```

must remain in `.env` and must not be committed to Git.

---

## Validation and Reproducibility

The backend has been validated through:

- Automated pytest tests
- Manual Swagger API testing
- PostgreSQL database checks
- Authentication tests
- Patient ownership tests
- Cross-user access tests
- Administrator role tests
- Alembic migration checks
- Model artifact validation
- Existing database record preservation checks

The API can be reproduced using:

1. Python 3.11
2. Dependencies from `requirements.txt`
3. A PostgreSQL database
4. Environment variables in `.env`
5. Alembic migrations
6. The two seed commands
7. The included trained model artifacts

---

## Limitations

The system has several important limitations:

- The machine-learning model was trained using the project dataset and has not been clinically validated for real-world diagnosis.
- Model-confidence values are not diagnostic probabilities.
- The system does not replace medical professionals.
- Red-flag logic is a controlled project safety mapping and is not a complete emergency triage system.
- NLP symptom recognition is limited to the supported symptom vocabulary and aliases.
- Older prediction records created before authentication may have no associated user ID.
- Administrator accounts are not created through public registration; they are created with `python -m app.db.create_admin`.

---

## Health Disclaimer

This system is intended for **health-awareness and educational purposes only**.

It does not:

- Diagnose medical conditions
- Replace a doctor or healthcare professional
- Provide treatment decisions
- Provide emergency medical services

Users with severe, urgent, or rapidly worsening symptoms should seek appropriate professional medical care.

---

## Related Repository

Machine-learning development and NLP preparation are maintained separately in:

```text
ucs31-madhaparia-ml
```

The backend repository contains only the production model artifacts required for inference.

---

## Current Backend Status

Implemented:

```text
Machine-learning integration             COMPLETE
NLP symptom mapping                      COMPLETE
Symptom confirmation                     COMPLETE
Red-flag handling                        COMPLETE
Prediction endpoint                      COMPLETE
Health-awareness guidance                COMPLETE
PostgreSQL database                      COMPLETE
Alembic migrations                       COMPLETE
User authentication                      COMPLETE
JWT security                             COMPLETE
Patient prediction ownership             COMPLETE
Patient-specific history                 COMPLETE
Administrator history access             COMPLETE
Administrator feedback access            COMPLETE
Automated authentication testing         COMPLETE
Role-based access testing                COMPLETE
```

Current automated test result:

```text
74 passed
0 failed
```

The backend is ready for integration with the frontend application.
