# ForgeGuard

> **Codex writes the code. ForgeGuard proves it is safe to ship.**

AI coding agents can produce convincing patches and passing tests while still weakening authorization, changing public contracts, or modifying unrelated files. ForgeGuard is the verification, supervision, and recovery layer around autonomous engineering: it combines independent AI reviewers with deterministic evidence, blocks unsafe changes, repairs specific findings, and returns an auditable proof package.

## The loop

```text
Repository + Task
       │
       ▼
Engineer Agent ──► isolated git worktree ──► real staged diff
       │
       ├─────────────┬───────────────┐
       ▼             ▼               ▼
   Security        Scope        Adversarial
       └─────────────┴───────────────┘
                     │
        deterministic tests/build
                     │
                     ▼
                 Risk Engine
               ┌─────┴─────┐
               ▼           ▼
            BLOCKED     VERIFIED
               │           │
          scoped repair     └──► proof package + flight recorder
               └───────────────► re-verify (maximum 2 cycles)
```

The MVP intentionally uses three independent reviewers—Security, Scope, and Adversarial—and the exact weighted risk formula from the product brief. A critical finding always blocks. Tests count only when at least one test ran and all tests passed.

## What is implemented

- FastAPI task API with async SQLite persistence and terminal failure guarantees.
- Isolated local/GitHub repository worktrees with path traversal and `.git` write protection.
- OpenAI Engineer, Adversarial, and Repair adapters; Groq Security and Scope adapters.
- Strict JSON contracts, 30/60-second deadlines, and one retry for malformed or timed-out model output.
- Parallel independent reviews with results recorded as they complete.
- Deterministic pytest/npm detection and captured logs.
- Automatic BLOCKED → repair → re-review loop.
- Proof-carrying Markdown output and timestamped flight recorder.
- Deterministic demo mode that reproduces the hackathon “tests pass but security fails” story without API keys.
- Next.js dashboard with live polling, React Flow evidence graph, Monaco diff, reviewer evidence, risk panel, responsive states, and copyable proof.
- Render backend manifest, Vercel-ready frontend, non-root Docker image, and GitHub Actions CI.

## Local setup

Requirements: Python 3.11+, Node.js 20+, npm, Git, and optionally Docker.

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env  # Windows; use `cp` on macOS/Linux
python -m uvicorn app.main:app --reload --port 8000
```

`DEMO_MODE=true` works without AI keys. For real repositories set `DEMO_MODE=false`, then provide `OPENAI_API_KEY` and `GROQ_API_KEY` in `backend/.env`. Never put either key in a `NEXT_PUBLIC_` variable.

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local  # Windows; use `cp` on macOS/Linux
npm run dev
```

Open `http://localhost:3000`.

## Exact live demo

Use repository `demo`, branch `main`, and this exact task:

> **Add retry handling with exponential backoff to checkout. Do not change the public API.**

The first deterministic Engineer pass adds valid retry handling but also weakens `auth.py`. Checkout tests pass. Security and Scope independently reject the unrelated authorization change, the Risk Engine blocks it, Repair restores the role check, and the whole patch is verified again. The deterministic path exists solely to make the hackathon demonstration reliable; provider-backed execution never injects it.

## Verification commands

```bash
cd backend
python -m pytest
ruff check app tests

cd ../frontend
npm test
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e

cd ..
docker build -f backend/Dockerfile -t forgeguard-api .
git grep -nEi '(sk-[A-Za-z0-9_-]{16,}|gsk_[A-Za-z0-9_-]{16,})' -- ':!README.md'
```

## Deployment

### Render backend

Create a Render Blueprint from this repository; `render.yaml` builds `backend/Dockerfile`, mounts a 1 GB SQLite disk, and exposes `/api/health`. Set `ALLOWED_ORIGINS` to the Vercel origin. Set provider and GitHub secrets manually in Render—each is marked `sync: false` and is never committed.

### Vercel frontend

Import the repository, set the Root Directory to `frontend`, and set `NEXT_PUBLIC_API_URL` to the Render service URL (for example `https://forgeguard-api.onrender.com`). The standard Next.js build command is sufficient.

## Security notes

ForgeGuard never sends provider credentials to the browser. It rejects credential-bearing repository URLs and unsafe branch names, never executes model-supplied shell commands, restricts writes to resolved worktree paths, refuses `.git` and symlink targets, and truncates stored provider/command output. This MVP deliberately has no user authentication, so deploy it as a controlled hackathon service rather than a public multi-tenant SaaS.

Dependency audit note (2026-08-15): the product brief pins Next.js 14, whose final 14.x release is still reported by npm for a high-severity advisory that is resolved only by a major upgrade. ForgeGuard does not use the implicated middleware, rewrites, Server Actions, `next/image`, custom servers, or CSP nonce flows. Keep the dashboard behind the intended controlled hackathon deployment and move to the current Next.js major before a public production launch if the brief permits it.

## Three-minute pitch

1. Show the task and explain that passing tests do not prove an AI patch is safe.
2. Start autonomous engineering and watch the Engineer create a patch in an isolated worktree.
3. Point out that deterministic checkout tests pass.
4. Let Security and Scope expose the authorization regression and show the BLOCKED verdict.
5. Watch scoped repair restore authorization, rerun all evidence, and reach VERIFIED.
6. Copy the proof package and close on accountability, not agent count.

Codex can write the code. ForgeGuard makes autonomous coding accountable.
