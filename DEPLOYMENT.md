# ForgeGuard Deployment Guide

This guide takes a fresh checkout to a demo or production-shaped Render deployment. Configuration precedence is **process environment → `.env` file → code defaults**.

## Prerequisites

- Docker Engine with Compose v2, or Python 3.11+ and Node.js 20.9+
- A GitHub App for repository webhooks and scoped branch/PR access
- OpenAI and Groq API keys when `DEMO_MODE=false`
- A Dodo Payments account with three subscription products

## Two-minute local demo

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
docker compose up --build
```

Open `http://localhost:3000`. The Compose backend runs `alembic upgrade head` before Uvicorn, persists SQLite under `/data`, and removes completed workspaces unless `WORKSPACE_RETENTION_HOURS` is non-zero.

For a local non-container seed, install backend dependencies and run:

```bash
pip install -r backend/requirements.txt
python scripts/seed_demo.py
```

## Database

SQLite is appropriate for the demo and a single backend instance:

```dotenv
DATABASE_URL=sqlite+aiosqlite:////data/forgeguard.db
```

Use Postgres for multiple instances and concurrent production traffic:

```dotenv
DATABASE_URL=postgresql+asyncpg://forgeguard:password@postgres:5432/forgeguard
```

The only schema setup command is:

```bash
cd backend
alembic upgrade head
```

## GitHub App setup

1. In GitHub Developer Settings, create a GitHub App named for your deployment.
2. Set the webhook URL to `https://YOUR_API/api/webhooks/github` and generate a strong secret matching `GITHUB_WEBHOOK_SECRET`.
3. Subscribe to **Push** events. Set repository permissions to **Contents: Read & write**, **Pull requests: Read & write**, and **Metadata: Read-only**.
4. Install the app only on intended repositories. Set `ALLOWED_REPOS=owner/repo,owner/second-repo` as an additional server-side boundary.
5. Provision `GITHUB_APP_ID` and the PEM value as `GITHUB_PRIVATE_KEY`. Push webhooks carry the installation ID; ForgeGuard exchanges it for a short-lived token restricted to contents, pull requests, and metadata. `GITHUB_TOKEN` is an optional local-development fallback only.

ForgeGuard creates and pushes only `forgeguard/repair-{job_id}` branches, then opens an evidence-backed PR against the original base branch. A runtime assertion rejects `main`, `master`, and `production` as write targets, and the app never merges the PR.

## Dodo Payments setup

1. Create monthly Developer, Pro, and Team subscription products in the Dodo dashboard.
2. Set their IDs as `DODO_PRODUCT_DEVELOPER`, `DODO_PRODUCT_PRO`, and `DODO_PRODUCT_TEAM`.
3. Add `https://YOUR_API/api/billing/webhook` under **Developer → Webhooks**.
4. Subscribe to subscription active/updated/renewed/cancelled events; ForgeGuard also accepts the legacy created/canceled and invoice-paid aliases.
5. Set the API and webhook credentials as `DODO_API_KEY` and `DODO_WEBHOOK_SECRET`.

## Render

Create a Blueprint from [render.yaml](render.yaml). It provisions the API, persistent SQLite disk, and dashboard. Set `BACKEND_URL` on the dashboard to the API's public URL, and set `FRONTEND_URL` plus `ALLOWED_ORIGINS` on the API to the dashboard's public URL.

For production provider-backed mode, set `DEMO_MODE=false`. Startup deliberately fails with a list of missing GitHub, model, Dodo, product, and session settings. Keep `DEMO_MODE=true` for a judge-facing deterministic deployment without paid model calls.

## CI/CD and release

- `ci.yml` runs backend tests/Ruff and frontend tests/lint/types/build on pushes to `main` or `master`.
- `pr-checks.yml` runs the same non-deploying checks for pull requests.
- `deploy.yml` publishes API and dashboard images to GHCR, tagged with the exact commit SHA, only after CI succeeds.
- Keep Render deployment behind its protected manual approval until the SHA-tagged images have been reviewed.

## Scripted judge walkthrough

1. Open the dashboard and point out the Pro Repair Credits balance.
2. Submit the bundled checkout retry task against `demo` / `main`.
3. Show deterministic tests passing while independent reviewers block the authorization regression.
4. Show the single credit authorization, bounded Repair cycle, and full re-verification.
5. Download the sealed receipt and open `/api/jobs/{job_id}/evidence` to show findings, plan, diff, tests, verdict, audit events, and credit usage together.

For the live GitHub path, set `DEMO_MODE=false`, push a vulnerable commit to an installed/allowlisted repository, follow the webhook-created job in the dashboard, authorize a blocked repair, and open the resulting PR from the green dashboard banner. The PR body is the same evidence package exposed by the evidence endpoint; merging always remains a human action.

## Manual one-time checklist

- [ ] Create and install the GitHub App with the permissions above.
- [ ] Create the three Dodo subscription products and webhook endpoint.
- [ ] Provision secrets in Render/GitHub; never commit a populated `.env`.
- [ ] Set frontend/backend public URLs and allowed origins.
- [ ] Decide SQLite single-instance or provision Postgres before scaling out.
- [ ] Run the full CI gate, approve deployment, and perform one signed webhook smoke test.
