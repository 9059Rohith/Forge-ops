# ForgeGuard Product Design

## Product boundary

ForgeGuard is a deployable verification and governance layer for autonomous coding agents. A user submits a Git repository, branch, and engineering task. ForgeGuard creates an isolated worktree, asks an Engineer Agent for file replacements, computes the real git diff, runs deterministic checks, sends the patch to Security, Scope, and Adversarial reviewers concurrently, calculates risk, repairs blocked work up to two times, and emits a proof package plus a complete flight log.

The complete build prompt is authoritative where the two supplied documents differ. Authentication, billing, teams, MCP, screenshots, human approval gates, vector search, extra reviewer agents, and real pull-request creation are outside this MVP.

## Architecture

The Next.js 14 App Router frontend is a thin, typed client. It submits tasks and polls the FastAPI API every 1.5 seconds while tasks are active. FastAPI owns secrets, persistence, orchestration, repository access, model calls, validation, timeouts, and error handling. SQLite with async SQLAlchemy persists projects, tasks, agent runs, evaluations, flight logs, and generated artifacts needed to recover state after requests finish.

Agent providers are small adapters with strict JSON parsing, timeouts, and a single retry. The demo mode is deterministic and requires no provider keys: its first pass intentionally introduces an unrelated authorization regression, review blocks it, repair restores authorization and adds retry handling, and verification then succeeds. Non-demo mode uses OpenAI for Engineer, Adversarial, and Repair and Groq for Security and Scope.

Repository mutations are restricted to a resolved worktree root. Model-returned paths must be relative, remain inside that root after resolution, avoid symlinks, and cannot target `.git`. Commands use argument arrays, never a shell. Repository URLs accept local paths or HTTPS GitHub URLs; credentials never enter frontend state.

## API and lifecycle

`POST /api/tasks` validates repository, branch, and description, creates rows, and schedules `run_task()` without blocking. Task status moves through `queued`, `planning`, `engineering`, `reviewing`, `blocked`, `repairing`, and a terminal `verified` or `failed`. Every transition emits a timestamped flight record. Read endpoints return task state, flight log, diff, and proof. A manual repair endpoint is idempotent and only accepts blocked tasks below the configured repair limit.

Unhandled failures always persist a terminal status and a safe public error. Provider errors and command output are truncated and scrubbed before storage. Worktrees are preserved on exhausted repair for inspection and removed only when setup itself fails before useful artifacts exist.

## Risk and proof

Risk uses the supplied exact weights: Security 30%, Scope 20%, Adversarial 30%, and deterministic tests 20%. Tests contribute 100 only when at least one test ran and all passed. Any critical reviewer finding blocks regardless of total. Scores below 75 block; below 60 or critical is HIGH, otherwise blocked is MEDIUM; verified is LOW.

The proof package reports task, files changed, tests, all reviewer scores, confidence, risk, repair count, and evidence channels. It is generated for both verified and exhausted/failed review outcomes so judges can inspect why ForgeGuard decided.

## Visual system

Accepted references:

- `docs/design/forgeguard-entry-concept.png` at 1584×1024
- `docs/design/forgeguard-task-concept.png` at 1516×1045

The UI uses a near-black graphite background (`#060b10`), cool slate bands (`#0b141c`, `#101b24`), hairline borders (`#263844`), off-white primary text (`#f4f7f6`), muted slate text (`#94a3ad`), electric mint (`#64e6bd`) for primary/verified, amber (`#f4b74a`) for repair, and red (`#ff6b70`) for blocked/critical. Sans display typography carries headings; a monospaced face carries labels, inputs, timestamps, scores, and code.

The entry page is an asymmetric two-column first viewport with one task form frame, followed by a single workflow rail and the supplied accountability line. The task page uses a quiet top bar, one horizontal summary band, the agent graph, three expandable reviewer rows, a diff/proof work area, a right evidence rail with flight recorder, and a bottom proof summary. Container geometry stays square at 8–10px radii with minimal shadow and no glass, glow, decorative gradients, fake metrics, or card-grid filler.

Above-the-fold entry copy is locked to: `ForgeGuard`, `Autonomous engineering, with proof.`, the supplied support sentence, `Repository`, `Branch`, `Engineering task`, `Start autonomous engineering`, and the five workflow labels. Task detail copy is driven by API state plus required action labels `Run another task`, `View diff`, and `Copy proof`.

## Responsive and accessibility behavior

At tablet widths the task summary wraps into a grid, evidence rail moves below the main work area, and the React Flow canvas remains horizontally usable. On mobile, entry content becomes one column; task summary becomes stacked; reviewer metadata wraps; Monaco uses a fixed accessible height; and no primary content overflows. All controls have visible keyboard focus, labels remain programmatically associated, semantic status text accompanies color, expandable content uses native disclosure semantics, motion honors reduced-motion preferences, and contrast targets WCAG AA.

## Testing and acceptance

Backend unit tests cover risk boundaries, proof rendering, safe path handling, provider JSON parsing, command detection, and model serialization. API tests cover validation, task creation, reads, missing resources, and repair guards. An integration test runs the deterministic demo loop from task creation through BLOCKED, repair, and VERIFIED without external APIs.

Frontend tests cover task-form validation/submission, API error handling, status rendering, reviewer expansion, and polling termination. Playwright verifies the entry-to-task workflow using a real local backend, desktop and mobile layout, keyboard focus, and copy/proof actions. Release gates are backend tests, frontend tests, lint, typecheck, production build, demo-repo tests, secret scan, dependency audit where tooling is available, Docker build where Docker is available, and browser screenshot comparison against both accepted concepts.

