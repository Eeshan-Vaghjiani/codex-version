# Local audit evidence

Open RESPIRACARE_AUDIT_REPORT.md for results and limitations. All test databases contain synthetic users/assessments only. The configured application .env files were not changed.

The retained portable PostgreSQL 16.15 runtime came from the official EDB binaries page (https://www.enterprisedb.com/download-postgresql-binaries), Windows x64 fileid1260623. The redundant downloaded ZIP was removed; its SHA-256 is recorded in postgres-download-sha256.json. No global service was installed. PostgreSQL and the audit API are stopped.

From the workspace root, start only the retained local audit cluster with:

```powershell
& '.\audit-artifacts\postgres-runtime\pgsql\bin\pg_ctl.exe' -D '.\audit-artifacts\postgres-data' -l '.\audit-artifacts\postgres-server.log' -o '-h 127.0.0.1 -p 55432' -w start
```

To run backend tests, use TEST_DATABASE_URL=postgresql+psycopg://audit_user@127.0.0.1:55432/respiracare_test. Pytest creates and cleans its own schema. For manual local API/browser tests, set DATABASE_URL to postgresql+psycopg://audit_user@127.0.0.1:55432/respiracare_audit and use a local-only JWT secret of at least32 characters before starting Uvicorn. The audit database currently has V1 active. V2 browser tests require explicitly selecting V2 in that audit database. Never reuse these development settings for deployment.

The baseline-backend directory preserves the original tracked backend state (including original model files) plus the user's preexisting condition-information edit. Backend preexisting diff and initial/final statuses are retained. Model datasets were not copied, rewritten or removed.

Stop this cluster after testing:

```powershell
& '.\audit-artifacts\postgres-runtime\pgsql\bin\pg_ctl.exe' -D '.\audit-artifacts\postgres-data' -m fast -w stop
```
