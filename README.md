# CRNCY – USD FX Dashboard (FastAPI + Cloud Run)

CRNCY is a demo web dashboard that shows FX rates vs USD, converts amounts between currencies (USD-based cross-rate), and displays a recent trend chart. It is built with **FastAPI**, **Jinja2** templates, and static **CSS/JS**, and is deployed automatically to **Google Cloud Run** using **GitHub Actions + Workload Identity Federation (WIF)** and **Artifact Registry**.

---

## What it does

- Web UI:
  - “Latest Rates vs USD” table
  - FX Converter (From/To) with on-screen result
  - “Trend” modal with last N working days time series
- API:
  - `GET /health` – healthcheck
  - `GET /api/rates` – latest rates vs USD (server-side cache)
  - `GET /api/convert?amount=100&from=USD&to=MXN` – cross-rate conversion
  - `GET /api/trend?symbol=MXN&days=30` – 30-day trend
- Server-side caching to reduce calls to the public FX source.
- CI/CD:
  - PR: runs CI (tests + SonarCloud)
  - Push to `develop`: build + push image + deploy to DEV
  - Push to `staging`: build + push image + deploy to TEST
  - Push to `main`: build + push image + deploy to PROD

> FX source: **Frankfurter** public API. Currencies are validated against the supported list.

---

## High-level architecture

1. **FastAPI** serves HTML from `src/app/templates` and static assets from `src/app/static`.
2. **httpx** calls Frankfurter API:
   - Latest: `https://api.frankfurter.dev/v1/latest`
   - Currencies: `https://api.frankfurter.dev/v1/currencies`
   - Timeseries: `https://api.frankfurter.dev/v1/{start}..{end}`
3. **GitHub Actions**:
   - Builds a Docker image
   - Pushes to **Artifact Registry**
   - Deploys to **Cloud Run** based on branch
4. **Workload Identity Federation (WIF)** avoids storing GCP service account keys in GitHub.

---

## Repository structure

```txt
.
├─ .github/workflows/
│  └─ deploy-cloudrun.yml
├─ src/
│  └─ app/
│     ├─ main.py
│     ├─ templates/
│     │  └─ index.html
│     └─ static/
│        ├─ styles.css
│        └─ app.js
├─ tests/
│  └─ test_smoke.py
├─ Dockerfile
├─ requirements.txt
├─ requirements-dev.txt
└─ README.md


Requirements

Python 3.11+

pip

(Optional) Docker to run locally in a container

Run locally (instructions in Spanish)
1) Crear entorno virtual e instalar dependencias
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

2) Levantar la app

Opción A: uvicorn

uvicorn src.app.main:app --host 0.0.0.0 --port 8080 --reload


Abrir:

UI: http://localhost:8080

Health: http://localhost:8080/health

Rates: http://localhost:8080/api/rates

3) Ejecutar tests
pytest -q

API endpoints
Health

GET /health

Response:

{ "status": "ok" }

Latest rates

GET /api/rates

Returns latest rates vs USD (filtered to configured currencies that are supported) + cache metadata.

Convert

GET /api/convert?amount=100&from=USD&to=MXN

Example response:

{
  "amount": 100,
  "from": "USD",
  "to": "MXN",
  "result": 1798.1,
  "base": "USD",
  "fx_date": "2026-01-07"
}

Trend

GET /api/trend?symbol=MXN&days=30

Returns points (date, rate) to plot a time series.

CI/CD (GitHub Actions → Cloud Run)

Workflow file:

.github/workflows/deploy-cloudrun.yml

Triggers

pull_request to: develop, staging, main → runs CI (tests + SonarCloud)

push to: develop, staging, main → runs CI + build/push + deploy (depending on branch)

Recommended branch flow (instructions in Spanish)

Trabajar en develop y validar en DEV.

Crear PR develop → staging para desplegar a TEST.

Crear PR staging → main para producción.

Required GitHub secrets
Repository secrets (Actions)

Set in: Settings → Secrets and variables → Actions → Secrets

GCP_PROJECT_ID – GCP Project ID

GCP_REGION – region (e.g. us-central1)

GAR_REPO – Artifact Registry repository name (e.g. crncy-repo)

WIF_PROVIDER – Workload Identity Provider resource name

WIF_SERVICE_ACCOUNT – GitHub Actions deploy service account (email or resource)

CLOUD_RUN_RUNTIME_SA – Cloud Run runtime service account email

SONAR_TOKEN – SonarCloud token

SONAR_ORG – SonarCloud organization

SONAR_PROJECT_KEY – SonarCloud project key

Environment secrets (GitHub Environments)

Set in: Settings → Environments

DEV

CLOUD_RUN_SERVICE_DEV – Cloud Run service name for DEV

TEST

CLOUD_RUN_SERVICE_TEST – Cloud Run service name for TEST

PROD

CLOUD_RUN_SERVICE_PROD – Cloud Run service name for PROD

Important: environment secrets are only available when the workflow job sets environment: DEV/TEST/PROD.

Operational notes

Server-side cache is enabled (default 600s) to reduce calls to the public API.

Cross-rate conversion uses USD as base:

USD→X: rate[X]

X→USD: 1/rate[X]

X→Y: (amount / rate[X]) * rate[Y]

The dropdown only lists currencies supported by Frankfurter/ECB.

Quick troubleshooting

Static files not loading (CSS/JS):

Ensure src/app/static/styles.css and src/app/static/app.js exist

Confirm app.mount("/static", StaticFiles(...)) is configured

Deploy does not run:

Verify all required secrets exist

Confirm the branch is one of: develop, staging, main

SonarCloud only shows analysis on main:

This can depend on the SonarCloud plan. PR decoration should still work.

License

Demo project for learning/reference purposes.

::contentReference[oaicite:0]{index=0}

