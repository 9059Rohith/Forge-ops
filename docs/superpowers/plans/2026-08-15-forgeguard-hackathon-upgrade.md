# ForgeGuard Hackathon Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tamper-evident downloadable verification receipt, a custom opening poster, and a judge-ready README without weakening ForgeGuard’s deterministic live demo.

**Architecture:** Receipt construction is a pure backend function that hashes a canonical JSON payload and is exposed through the existing proof endpoint. The frontend consumes that payload through the existing polling request and renders a compact identity/download control inside the existing proof surface. Documentation remains repository-native Markdown with Mermaid diagrams and local raster assets.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SHA-256/JSON standard library, pytest, Next.js 14, React 18, TypeScript, Vitest, Testing Library, Playwright, Markdown, Mermaid, Image Gen.

## Global Constraints

- Preserve exactly three reviewers: Security, Scope, and Adversarial.
- Preserve the exact weighted risk formula and maximum two automatic repair cycles.
- Preserve the accepted graphite/mint dashboard hierarchy and existing above-the-fold copy.
- Never print, commit, or send provider credentials to the browser.
- Keep the existing `markdown` proof response field backwards-compatible.
- Use deterministic canonical JSON with sorted keys and compact separators.
- The receipt ID is `fg_` plus the first 16 hexadecimal characters of the evidence payload SHA-256; derived `receipt_id` and `integrity` fields are excluded from that hash input.
- Implement behavior changes test-first and observe the expected failure before production edits.

---

### Task 1: Deterministic verification receipt and API contract

**Files:**
- Modify: `backend/tests/test_proof_package.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/core/proof_package.py`
- Modify: `backend/app/routers/tasks.py`
- Modify: `backend/app/schemas.py`

**Interfaces:**
- Produces: `build_verification_receipt(*, task_id: str, description: str, repo_url: str, branch: str, changed_files: Sequence[str], tests_passed: int, tests_total: int, evaluations: Mapping[str, Mapping[str, Any]], confidence: float | None, risk_level: str | None, repair_cycles: int, decision: str, agent_runs: Sequence[Mapping[str, Any]], flight_logs: Sequence[Mapping[str, Any]], diff_text: str, proof_text: str) -> dict[str, Any]`.
- Extends: `GET /api/tasks/{task_id}/proof` from `{ markdown }` to `{ markdown, receipt }`.

- [ ] **Step 1: Write the failing deterministic-builder test**

  Add a test that calls `build_verification_receipt` twice with the same literal evidence and asserts identical dictionaries, `schema_version == "1.0"`, `receipt_id` matches `^fg_[0-9a-f]{16}$`, diff/proof hashes equal hand-computed `hashlib.sha256(...).hexdigest()` values, and `integrity.digest` equals a fresh hash of the returned evidence payload after removing the derived `receipt_id` and `integrity` fields.

- [ ] **Step 2: Run the focused proof test and confirm RED**

  Run: `python -m pytest tests/test_proof_package.py -q`

  Expected: import failure because `build_verification_receipt` does not exist.

- [ ] **Step 3: Implement the minimal canonical receipt builder**

  Add `_sha256_text(value: str) -> str`, `_canonical_json(value: Mapping[str, Any]) -> str`, and `build_verification_receipt(...)`. Build one JSON-compatible payload, hash it without an integrity field, derive the ID, then return the payload plus `{ "algorithm": "sha256", "digest": digest }`.

- [ ] **Step 4: Run the focused proof test and confirm GREEN**

  Run: `python -m pytest tests/test_proof_package.py -q`

- [ ] **Step 5: Write the failing proof-endpoint receipt test**

  Create a task through the existing API fixture, persist literal terminal evidence and proof text through the SQLAlchemy session, request `/api/tasks/{id}/proof`, and assert the existing Markdown remains unchanged while `receipt.task.id`, `receipt.decision`, and `receipt.integrity.digest` are present.

- [ ] **Step 6: Run the focused API test and confirm RED**

  Run: `python -m pytest tests/test_api.py -q`

  Expected: the response has no `receipt` field.

- [ ] **Step 7: Extend the proof endpoint and response schema**

  Add receipt view types to `schemas.py`. In `get_proof`, return `receipt: null` when `proof_text` is empty; otherwise serialize task evaluations, runs, and flight logs into `build_verification_receipt` and return the receipt beside the unchanged Markdown.

- [ ] **Step 8: Run backend verification**

  Run: `python -m pytest && python -m ruff check app tests`

- [ ] **Step 9: Commit the backend receipt**

  Run: `git add backend/app backend/tests && git commit -m "feat: add tamper-evident verification receipts"`

### Task 2: Receipt identity and download interaction

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/hooks/useTaskPolling.ts`
- Modify: `frontend/components/TaskView.tsx`
- Modify: `frontend/components/TaskDashboard.tsx`
- Modify: `frontend/components/ProofPackage.tsx`
- Modify: `frontend/tests/TaskDashboard.test.tsx`
- Modify: `frontend/tests/useTaskPolling.test.tsx`

**Interfaces:**
- Produces: `VerificationReceipt` TypeScript interface matching the backend payload.
- Changes: `ProofPackage({ proof, receipt })` and `TaskDashboard({ ..., receipt })`.

- [ ] **Step 1: Write the failing receipt-UI test**

  Render `TaskDashboard` with a complete literal `VerificationReceipt`. Assert the ForgeGuard receipt ID is visible, click `Download receipt`, and assert `URL.createObjectURL`, a generated anchor with `download="forgeguard-fg_deadbeefdeadbeef.json"`, and `URL.revokeObjectURL` are exercised.

- [ ] **Step 2: Run the focused dashboard test and confirm RED**

  Run: `npm test -- tests/TaskDashboard.test.tsx --run`

  Expected: TypeScript/runtime failure because the receipt prop and download control do not exist.

- [ ] **Step 3: Add receipt types and proof-response parsing**

  Define typed task, verification, provenance, artifact, and integrity fields under `VerificationReceipt`. Change `getProof` to return `{ markdown: string; receipt: VerificationReceipt | null }`, store receipt state in `useTaskPolling`, and pass it through `TaskView` and `TaskDashboard`.

- [ ] **Step 4: Implement the minimal proof receipt control**

  Add a compact mint seal identity and a `Download receipt` button to `ProofPackage`. Serialize with `JSON.stringify(receipt, null, 2)`, create an `application/json` Blob, trigger the filename derived from `receipt.receipt_id`, remove the anchor, and revoke the object URL.

- [ ] **Step 5: Run the focused test and confirm GREEN**

  Run: `npm test -- tests/TaskDashboard.test.tsx --run`

- [ ] **Step 6: Update the polling behavior test**

  Extend the complete proof mock to include `receipt: null`; assert the hook exposes receipt without changing terminal polling behavior.

- [ ] **Step 7: Run frontend verification**

  Run: `npm test -- --run && npm run lint && npm run build && npm run typecheck`

- [ ] **Step 8: Commit the frontend receipt**

  Run: `git add frontend && git commit -m "feat: make verification evidence portable"`

### Task 3: Custom poster and top-tier README

**Files:**
- Create: `docs/assets/forgeguard-poster.png`
- Modify: `README.md`

**Interfaces:**
- Consumes: accepted dashboard render at `docs/qa/forgeguard-task-render.png` and the receipt API contract from Task 1.
- Produces: a self-contained GitHub project page with local images and Mermaid diagrams.

- [ ] **Step 1: Generate the wide README poster**

  Use built-in Image Gen with a 16:9 cinematic cybersecurity/developer-tool brief, exact text `ForgeGuard` and `Autonomous engineering, with proof.`, graphite/slate background, electric-mint verified path, restrained red unsafe path, and no other text, logos, watermarks, glass cards, or generic padlock stock imagery.

- [ ] **Step 2: Inspect and place the poster**

  Use `view_image` to confirm spelling, composition, contrast, and GitHub legibility. Copy the accepted image to `docs/assets/forgeguard-poster.png` and report the final prompt and path.

- [ ] **Step 3: Rewrite the README**

  Open with the poster and value proposition. Add the exact demo story, judge-facing differentiators, current dashboard screenshot, architecture/verification/sequence Mermaid diagrams, risk formula, receipt contract, setup modes, API table, repository tree, security model, test matrix, deployment, Codex build story, roadmap, and three-minute pitch. Keep commands executable from repository paths and avoid fabricated claims.

- [ ] **Step 4: Validate README assets and structure**

  Run a local Markdown-link checker script that resolves every relative image/link target, parse every Mermaid fence for a non-empty diagram body and supported diagram header, and inspect the file for placeholder language.

- [ ] **Step 5: Commit documentation**

  Run: `git add README.md docs/assets/forgeguard-poster.png && git commit -m "docs: present ForgeGuard as a proof-first Codex workflow"`

### Task 4: Full-system, security, and visual verification

**Files:**
- Modify: `frontend/e2e/forgeguard.spec.ts`
- Modify: `docs/qa/fidelity-ledger.md`
- Create or update: `docs/qa/forgeguard-entry-render.png`
- Create or update: `docs/qa/forgeguard-task-render.png`

**Interfaces:**
- Verifies the complete deterministic lifecycle and the real receipt download.

- [ ] **Step 1: Extend Playwright acceptance test first**

  After the terminal proof appears, assert an evidence seal matching `/fg_[0-9a-f]{16}/`, click `Download receipt`, save the download, parse it as JSON, and assert the downloaded `receipt_id` matches the visible ID.

- [ ] **Step 2: Run E2E and confirm RED before production wiring is complete**

  Run: `npm run test:e2e`

- [ ] **Step 3: Run the final deterministic test matrix**

  Run backend pytest/Ruff, demo-repo pytest, frontend Vitest/lint/build/typecheck, and desktop/mobile Playwright in sequence.

- [ ] **Step 4: Validate live credentials safely**

  Load credentials from ignored `backend/.env`; ask OpenAI and Groq for one minimal structured JSON response and call GitHub `/user`. Print only PASS/FAIL, HTTP status, configured model name, and response-shape validity.

- [ ] **Step 5: Run supply-chain and secret checks**

  Run `npm audit --omit=dev`, `python -m pip check`, tracked-file secret filename scans, and current-content secret-pattern scans. Never print matching secret values.

- [ ] **Step 6: Build the backend container when Docker is available**

  Run: `docker build -f backend/Dockerfile -t forgeguard-api .`

- [ ] **Step 7: Capture and inspect final visuals**

  Use Playwright at 1584×1024 and 1516×1045 plus Pixel 7. Inspect accepted concepts and fresh renders with `view_image`, then update the fidelity ledger with at least five comparison points and any intentional deviation.

- [ ] **Step 8: Final repository audit**

  Confirm `git status`, inspect the file summary without printing credential-bearing historical diffs, confirm no temporary QA artifacts remain, and ensure current history is safe to publish or explicitly report required rotation/history cleanup.
