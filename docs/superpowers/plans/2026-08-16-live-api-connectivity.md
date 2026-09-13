# Live API Connectivity Implementation Plan

> Completion review (2026-09-13): implementation and current acceptance results are recorded in [the completion report](../../qa/completion-2026-09-13.md). Historical test-first steps below are retained as planning history, not a current pending-work queue.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ForgeGuard submit real repository tasks through a reliable same-origin API path, with live mode as the default and deterministic demo behavior available only by explicit opt-in.

**Architecture:** Browser code calls `/api/backend/*` on the Next.js origin. A catch-all Next.js Route Handler forwards the request to the runtime `BACKEND_URL`, preserves upstream status/body, and returns an actionable 503 JSON error when the backend cannot be reached. Backend selection uses real providers for every repository except the explicitly enabled `demo` repository.

**Tech Stack:** Next.js 16 Route Handlers, React 19, Vitest, FastAPI, Pydantic Settings, pytest.

## Global Constraints

- No mock or deterministic demo data in the default application flow.
- Do not expose private backend hostnames or credentials to the browser.
- Preserve the explicit local demo harness for opt-in development and its existing tests.
- Add no new runtime dependencies.

---

### Task 1: Same-origin API transport

**Files:**
- Create: `frontend/app/api/backend/[...path]/route.ts`
- Create: `frontend/tests/api-proxy.test.ts`
- Create: `frontend/tests/api-client.test.ts`
- Modify: `frontend/lib/api.ts`
- Delete: `frontend/app/api/config/route.ts`

**Interfaces:**
- Consumes: `BACKEND_URL` on the Next.js server, defaulting to `http://127.0.0.1:8000` locally.
- Produces: `proxyRequest(request: Request, context: { params: Promise<{ path: string[] }> }): Promise<Response>` and browser requests under `/api/backend/api/*`.

- [ ] **Step 1: Write failing transport tests**

```ts
it("uses the same-origin backend path", async () => {
  await createTask({ repo_url: "C:/repo", branch: "main", description: "Fix retries" });
  expect(observedUrl).toBe("/api/backend/api/tasks");
});

it("returns an actionable 503 when the backend is unreachable", async () => {
  const response = await proxyRequest(request, context);
  expect(response.status).toBe(503);
  expect(await response.json()).toEqual({ detail: "ForgeGuard API is unavailable. Start the backend and try again." });
});
```

- [ ] **Step 2: Run tests to verify RED**

Run: `cd frontend && npm test -- tests/api-client.test.ts tests/api-proxy.test.ts`
Expected: FAIL because requests still resolve `/api/config` and the proxy route does not exist.

- [ ] **Step 3: Implement the proxy and relative client base**

```ts
const API_BASE = "/api/backend";

export async function proxyRequest(request: Request, context: ProxyContext) {
  const { path } = await context.params;
  const upstream = new URL(`/api/${path.join("/")}`, backendUrl());
  upstream.search = new URL(request.url).search;
  // Forward method/body and return upstream status/body/content-type.
}
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `cd frontend && npm test -- tests/api-client.test.ts tests/api-proxy.test.ts`
Expected: PASS.

### Task 2: Explicit live/demo boundary

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/core/orchestrator.py`
- Modify: `backend/app/routers/tasks.py`
- Modify: `backend/billing/router.py`
- Modify: `backend/tests/test_config_health.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_orchestrator.py`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `render.yaml`

**Interfaces:**
- Consumes: `DEMO_MODE` boolean and repository identifier.
- Produces: `is_explicit_demo(repo_url: str) -> bool`, true only when `DEMO_MODE=true` and `repo_url == "demo"`.

- [ ] **Step 1: Write failing live-mode tests**

```py
def test_live_mode_is_the_default(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert Settings().demo_mode is False

def test_real_repository_never_selects_demo_agents(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert is_explicit_demo("https://github.com/acme/project") is False
```

- [ ] **Step 2: Run tests to verify RED**

Run: `cd backend && python -m pytest tests/test_config_health.py tests/test_orchestrator.py -q`
Expected: FAIL because demo mode defaults true and currently applies to all repositories.

- [ ] **Step 3: Implement the explicit demo predicate and live defaults**

```py
def is_explicit_demo(repo_url: str) -> bool:
    settings = get_settings()
    return settings.demo_mode and repo_url == "demo"
```

Use the predicate for engineer, reviewer, repair, and demo-user selection. Set deployment examples/defaults to `DEMO_MODE=false`.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `cd backend && python -m pytest tests/test_config_health.py tests/test_api.py tests/test_orchestrator.py -q`
Expected: PASS.

### Task 3: Remove mock defaults from the landing flow

**Files:**
- Modify: `frontend/components/TaskForm.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/tests/TaskForm.test.tsx`
- Modify: `README.md`

**Interfaces:**
- Consumes: operator-entered repository, branch, and engineering task.
- Produces: an empty live task form; no automatic request to demo billing data.

- [ ] **Step 1: Write a failing landing-flow test**

```tsx
it("starts with no fabricated repository or task", () => {
  render(<TaskForm />);
  expect(screen.getByLabelText("Repository")).toHaveValue("");
  expect(screen.getByLabelText("Engineering task")).toHaveValue("");
});
```

- [ ] **Step 2: Run test to verify RED**

Run: `cd frontend && npm test -- tests/TaskForm.test.tsx`
Expected: FAIL because the form contains the deterministic demo inputs.

- [ ] **Step 3: Remove demo defaults and homepage demo billing call**

Initialize repository and description to empty strings, add non-data placeholders, and render no credits component until a real authenticated user identity exists.

- [ ] **Step 4: Run test to verify GREEN**

Run: `cd frontend && npm test -- tests/TaskForm.test.tsx`
Expected: PASS.

### Task 4: Full verification and run instructions

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the completed backend and frontend changes.
- Produces: verified build/test results and exact local commands for live and opt-in demo modes.

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest -q`
Expected: all tests PASS.

- [ ] **Step 2: Run frontend quality gates**

Run: `cd frontend && npm test && npm run typecheck && npm run lint && npm run build`
Expected: all commands PASS.

- [ ] **Step 3: Run browser interaction validation**

Start backend and frontend, load `http://127.0.0.1:3000`, confirm meaningful content and no framework overlay, submit a real local repository task, and verify navigation to `/task/<id>` without console/network errors.

- [ ] **Step 4: Document exact commands**

Document live mode with required provider keys and an explicit `DEMO_MODE=true` command only for the bundled deterministic demo.
