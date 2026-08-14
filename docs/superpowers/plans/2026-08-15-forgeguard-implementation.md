# ForgeGuard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete deployable ForgeGuard MVP described in the approved product design.

**Architecture:** A typed Next.js 14 frontend talks only to a FastAPI service. FastAPI persists state in async SQLite, operates on isolated git worktrees, orchestrates provider-backed or deterministic demo agents, and exposes evidence artifacts through narrow REST endpoints.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn-style primitives, React Flow, Monaco, Vitest, Playwright, FastAPI, Python 3.11, SQLAlchemy async, SQLite, OpenAI, Groq, GitPython, PyGithub, pytest.

## Global Constraints

- Implement exactly three reviewers: Security, Scope, and Adversarial.
- Keep all provider and GitHub credentials server-side.
- Use the exact supplied risk formula and at most two automatic repair cycles.
- Preserve the approved graphite/mint visual system and locked above-the-fold copy.
- No authentication, billing, teams, MCP, multimodal review, human gates, or real PR creation.
- All unhandled task failures must become terminal and be recorded.
- Every repository write must be path-contained inside an isolated worktree.

---

### Task 1: Foundation, domain contracts, and risk engine

**Files:**
- Create: `backend/pyproject.toml`, `backend/requirements.txt`, `backend/requirements-dev.txt`
- Create: `backend/tests/test_risk_engine.py`, `backend/tests/test_schemas.py`
- Create: `backend/app/config.py`, `backend/app/schemas.py`, `backend/app/core/risk_engine.py`

**Interfaces:**
- Produces `compute_risk(security, scope, adversarial, tests_passed, tests_total) -> RiskResult` and validated request/response schemas.

- [ ] Write boundary and validation tests first.
- [ ] Run targeted pytest and confirm missing-module failures.
- [ ] Implement typed settings, schemas, and exact weighted risk logic.
- [ ] Run targeted pytest until green, then run the backend suite.

### Task 2: Persistence and REST lifecycle

**Files:**
- Create: `backend/app/db.py`, `backend/app/models.py`, `backend/app/main.py`
- Create: `backend/app/routers/health.py`, `backend/app/routers/tasks.py`
- Create: `backend/tests/test_api.py`

**Interfaces:**
- Produces task create/read/log/diff/proof/repair endpoints under `/api` and async session helpers.

- [ ] Write API tests for health, validation, creation, 404s, and repair guards.
- [ ] Run them to confirm routes are absent.
- [ ] Implement models, startup lifespan, CRUD serialization, CORS, and background scheduling boundary.
- [ ] Run API tests and full backend suite.

### Task 3: Safe repository and deterministic verification

**Files:**
- Create: `backend/app/core/worktree.py`, `backend/app/core/repository.py`, `backend/app/core/deterministic_verifier.py`
- Create: `backend/tests/test_worktree.py`, `backend/tests/test_verifier.py`
- Create: `demo-repo/checkout.py`, `demo-repo/auth.py`, `demo-repo/main.py`, `demo-repo/tests/test_checkout.py`, `demo-repo/tests/test_auth.py`, `demo-repo/requirements.txt`

**Interfaces:**
- Produces `WorktreeManager`, safe file application, staged unified diff capture, and `VerificationResult`.

- [ ] Write traversal/symlink, command-detection, and test-result parsing tests.
- [ ] Confirm expected failures.
- [ ] Implement containment checks, non-shell subprocess execution, repository cloning/worktree creation, and test detection.
- [ ] Build and initialize the standalone demo git repository and run its tests.
- [ ] Run all backend tests.

### Task 4: Provider adapters and agents

**Files:**
- Create: `backend/app/providers/base.py`, `backend/app/providers/openai_client.py`, `backend/app/providers/groq_client.py`
- Create: `backend/app/agents/prompts.py`, `engineer.py`, `security_agent.py`, `scope_agent.py`, `adversarial_agent.py`, `repair.py`, `demo.py`
- Create: `backend/tests/test_providers.py`, `backend/tests/test_agents.py`

**Interfaces:**
- Produces strict agent result objects and retrying JSON provider clients with 60-second engineering and 30-second review deadlines.

- [ ] Write tests for fenced/malformed JSON, one retry, empty engineer output, demo planted failure, and repaired output.
- [ ] Confirm failures before implementation.
- [ ] Implement prompt contracts, provider adapters, typed parsing, and deterministic demo agents.
- [ ] Run targeted and full backend suites.

### Task 5: Orchestration, recorder, and proof

**Files:**
- Create: `backend/app/core/flight_recorder.py`, `backend/app/core/proof_package.py`, `backend/app/core/orchestrator.py`
- Create: `backend/tests/test_proof_package.py`, `backend/tests/test_orchestrator.py`
- Modify: `backend/app/routers/tasks.py`

**Interfaces:**
- Produces `run_task(task_id)`, terminal-state guarantees, concurrent reviewer persistence, repair loop, diff/proof artifacts, and manual repair scheduling.

- [ ] Write proof snapshot and full demo-loop integration tests.
- [ ] Confirm missing implementation failures.
- [ ] Implement flight logs, agent-run lifecycle, concurrent review, exact risk decision, repair loop, and top-level failure handling.
- [ ] Run integration test repeatedly and full backend suite.

### Task 6: Frontend shell, entry workflow, and typed API

**Files:**
- Create: `frontend/package.json`, configs, `app/layout.tsx`, `app/globals.css`, `app/page.tsx`
- Create: `frontend/components/Brand.tsx`, `TaskForm.tsx`, `WorkflowRail.tsx`, UI primitives
- Create: `frontend/lib/api.ts`, `frontend/lib/types.ts`
- Create: `frontend/tests/TaskForm.test.tsx`, test setup

**Interfaces:**
- Produces accessible task submission and typed API helpers.

- [ ] Write form validation/submission/error tests.
- [ ] Run Vitest and confirm component/module failures.
- [ ] Implement the accepted entry concept and API client.
- [ ] Run tests, lint, and typecheck.

### Task 7: Live task dashboard

**Files:**
- Create: `frontend/app/task/[id]/page.tsx`
- Create: `frontend/components/TaskDashboard.tsx`, `AgentGraph.tsx`, `ReviewerCard.tsx`, `RiskPanel.tsx`, `DiffViewer.tsx`, `FlightRecorder.tsx`, `ProofPackage.tsx`, `StatusSummary.tsx`
- Create: `frontend/hooks/useTaskPolling.ts`, `frontend/tests/TaskDashboard.test.tsx`

**Interfaces:**
- Consumes task, diff, proof, and flight-log APIs; stops polling on verified or failed.

- [ ] Write rendering, disclosure, copy, error, and terminal-polling tests.
- [ ] Confirm failures.
- [ ] Implement task dashboard against the accepted task concept.
- [ ] Run frontend tests, lint, typecheck, and build.

### Task 8: Deployment, documentation, and end-to-end verification

**Files:**
- Create: `backend/Dockerfile`, `backend/.env.example`, `frontend/.env.example`, `render.yaml`, `.gitignore`, `README.md`
- Create: `frontend/e2e/forgeguard.spec.ts`, `frontend/playwright.config.ts`

**Interfaces:**
- Produces local and hosted runbooks plus deployment manifests.

- [ ] Write Playwright tests for desktop, mobile, form-to-verdict flow, and keyboard focus.
- [ ] Run the E2E test to expose integration gaps and fix them.
- [ ] Run backend tests, frontend tests, lint, typecheck, production build, demo tests, secret scan, and dependency audits.
- [ ] Build the backend Docker image when Docker is available.
- [ ] Capture entry and task screenshots at concept-native dimensions, inspect both concepts and renders with `view_image`, record the fidelity ledger, fix mismatches, and re-run checks.
- [ ] Finish README with architecture, setup, exact demo script, deployment steps, pitch, and required closing line.

