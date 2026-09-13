# Repair Credits and Deployment Implementation Plan

> Completion review (2026-09-13): implementation and current acceptance results are recorded in [the completion report](../../qa/completion-2026-09-13.md). Historical test-first steps below are retained as planning history, not a current pending-work queue.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Dodo-backed Repair Credits to the existing ForgeGuard task lifecycle and make the full stack reproducibly deployable without replacing the current verification workflow.

**Architecture:** Existing `Task` rows remain repair jobs. New billing tables and services live under `backend/billing`; an atomic conditional update reserves one credit per task before the first repair cycle, and a unique usage row makes retries idempotent. New routers expose billing, authorization, GitHub webhook, readiness, and evidence contracts while current `/api/tasks` routes remain compatible.

**Tech Stack:** Python 3.11, FastAPI, async SQLAlchemy, Alembic, httpx, Standard Webhooks, SQLite/Postgres, Next.js 16, React 19, Vitest, Docker Compose, Render, GitHub Actions.

## Global Constraints

- One Repair Credit authorizes one repair job, regardless of internal retry count.
- Existing tables, routes, components, agent prompts, and risk semantics remain intact.
- Dodo secrets stay server-side and production startup names every missing required setting.
- Protected branches are never mutation targets; repair branches use `forgeguard/repair-{task_id}`.
- Every behavior change starts with a failing test and ends with the complete verification matrix.

---

### Task 1: Billing persistence and atomic entitlement service

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/billing/__init__.py`
- Create: `backend/billing/models.py`
- Create: `backend/billing/entitlement_service.py`
- Test: `backend/tests/test_billing.py`

**Interfaces:**
- Produces: `EntitlementService.reserve_for_job(user_id: str, repair_job_id: str) -> EntitlementResult`.
- Produces: `EntitlementService.record_repair_outcome(repair_job_id: str, status: str) -> None`.

- [ ] Write tests for success, exhaustion, idempotency, concurrent reservation, refund, and non-refunded cycle failure.
- [ ] Run `python -m pytest tests/test_billing.py -q` and confirm the missing-module failure.
- [ ] Add `User`, `Subscription`, `RepairCredit`, `RepairUsage`, and `AuditLog` models plus nullable task ownership/pending-plan fields.
- [ ] Implement reservation as `UPDATE repair_credits ... WHERE credits_remaining > 0`, followed by a unique usage insert in one transaction.
- [ ] Run the focused tests and Ruff.

### Task 2: Dodo client, billing webhooks, and repair authorization APIs

**Files:**
- Create: `backend/billing/dodo_client.py`
- Create: `backend/billing/service.py`
- Create: `backend/billing/router.py`
- Create: `backend/app/routers/repairs.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_billing_api.py`

**Interfaces:**
- Produces: `POST /api/billing/checkout`, `POST /api/billing/webhook`, `GET /api/billing/status/{user_id}`.
- Produces: `GET/POST /api/repairs/{task_id}/authorization|authorize`.

- [ ] Write failing API tests for signature rejection, subscription upsert, no-credit 402, and successful authorization.
- [ ] Implement the current Dodo `/checkouts`, `/customers`, and `/subscriptions/{id}` REST calls and Standard Webhooks verification.
- [ ] Normalize both supplied legacy event names and current Dodo subscription event names.
- [ ] Upsert subscriptions/period credits idempotently and wire authorization routes.
- [ ] Run focused API tests and Ruff.

### Task 3: Orchestrator ownership, audit evidence, and safety hardening

**Files:**
- Modify: `backend/app/core/orchestrator.py`
- Modify: `backend/app/core/flight_recorder.py`
- Modify: `backend/app/core/worktree.py`
- Modify: `backend/app/routers/tasks.py`
- Create: `backend/app/routers/webhooks.py`
- Test: `backend/tests/test_orchestrator.py`
- Test: `backend/tests/test_worktree.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Task creation accepts optional `user_id`; demo mode resolves a seeded free user.
- `GET /api/jobs/{task_id}/evidence` returns task, findings, plan, diff, tests, verdict, audit events, and credit usage.

- [ ] Write failing tests for protected branches, evidence serialization, webhook validation, and entitlement gating.
- [ ] Gate the first repair invocation through idempotent reservation and persist `awaiting_authorization` on exhaustion.
- [ ] Mark terminal usage consumed; refund only failures before any repair cycle starts.
- [ ] Mirror flight-recorder transitions into `audit_logs` and enforce unique work roots/protected branches/cycle ceiling.
- [ ] Run backend tests and Ruff.

### Task 4: Configuration, migrations, health, logging, and rate limiting

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/db.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/health.py`
- Create: `backend/app/observability.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/0001_forgeguard_schema.py`
- Modify: `backend/.env.example`

**Interfaces:**
- Produces: `/healthz`, `/readyz`, JSON request logs, webhook rate limiting, and `alembic upgrade head`.

- [ ] Write failing config/readiness tests.
- [ ] Validate production secrets while allowing deterministic demo mode.
- [ ] Add one additive migration chain for existing and billing schema.
- [ ] Add request IDs/job IDs to JSON access logs and a bounded in-memory webhook limiter.
- [ ] Run config, health, and migration tests.

### Task 5: Repair Credits dashboard and runtime backend configuration

**Files:**
- Create: `frontend/components/RepairCreditsCard.tsx`
- Create: `frontend/components/AuthorizationCard.tsx`
- Modify: `frontend/components/TaskForm.tsx`
- Modify: `frontend/components/TaskDashboard.tsx`
- Modify: `frontend/hooks/useTaskPolling.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/types.ts`
- Create: `frontend/app/api/config/route.ts`
- Test: `frontend/tests/TaskDashboard.test.tsx`

**Interfaces:**
- Main entry shows plan usage; awaiting tasks expose an explicit one-credit authorization action.
- Browser API resolution can use runtime `BACKEND_URL` through same-origin config.

- [ ] Write failing component tests for credits, loading/error states, and authorization.
- [ ] Add typed billing requests and polling for authorization state.
- [ ] Add the two cards in the existing graphite/mint component language.
- [ ] Run Vitest, lint, typecheck, and build.

### Task 6: Packaging, CI, seed data, deployment guide, and README

**Files:**
- Modify: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Modify: `render.yaml`
- Modify: `.github/workflows/ci.yml`
- Create: `.github/workflows/deploy.yml`
- Create: `.github/workflows/pr-checks.yml`
- Create: `scripts/seed_demo.py`
- Create: `DEPLOYMENT.md`
- Create: `backend/billing/README.md`
- Modify: `README.md`

**Interfaces:**
- Fresh demo: `docker compose up --build`, then `python scripts/seed_demo.py` when seeding outside Compose.

- [ ] Add non-root health-checked images, Compose persistence, Render settings, and SHA-tagged image workflow.
- [ ] Add idempotent Pro demo seed data and complete one-time GitHub/Dodo setup instructions.
- [ ] Rewrite README setup, architecture, billing, endpoint, deployment, and verification sections so every claim matches code.
- [ ] Run all backend/frontend/demo tests, lint, types, builds, migration upgrade, and repository status review.
