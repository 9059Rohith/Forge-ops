# ForgeGuard Hackathon Upgrade Design

## Objective

Turn the existing, working ForgeGuard MVP into a memorable Codex Community Hackathon submission without destabilizing its strongest asset: a deterministic live demonstration in which tests pass, independent reviewers catch an authorization regression, scoped repair removes it, and the patch is verified again.

The upgrade optimizes for the published judging signals: what was built, meaningful Codex use, and clarity of the final demonstration.

## Considered approaches

### 1. Presentation-only polish

Rewrite the README, add a poster, and leave the product untouched. This is the fastest route and carries almost no engineering risk, but gives judges no new product capability to discover during the demo.

### 2. Proof-first product upgrade — selected

Keep the existing agent workflow and visual system, add a tamper-evident verification receipt that can be downloaded from the final proof surface, and make the README tell the complete unsafe-patch-to-proof story. This creates a concrete artifact judges can inspect while remaining small enough to test thoroughly before the event.

### 3. Broad platform expansion

Add more agents, pull-request creation, multimodal review, or team workflows. This could increase breadth, but it would dilute the core story, require new credentials and failure modes, and weaken demo reliability within the available time.

## Product story

The winning narrative is not “many agents write code.” It is “autonomous code earns trust through independent evidence.” ForgeGuard demonstrates the gap between a passing test suite and a safe change, then closes that gap with isolation, adversarial review, bounded repair, deterministic re-verification, and a portable receipt.

The three-minute demo remains the primary experience:

1. Submit the bundled checkout task.
2. Watch the Engineer create a real diff in an isolated worktree.
3. Show the deterministic tests passing while Security and Scope reject an unrelated authorization change.
4. Watch the Risk Engine block the patch and Repair remove only the unsafe change.
5. Reach `VERIFIED`, then download the evidence receipt and show its stable ForgeGuard ID.

Provider-backed execution remains available for real repositories. The deterministic mode remains the default stage path because it is reproducible, requires no network, and demonstrates every important state.

## Verification receipt

The backend will derive a machine-readable receipt from persisted task evidence. The receipt will include:

- schema version and ForgeGuard receipt ID;
- terminal decision, task identity, repository, branch, and changed files;
- deterministic test totals, reviewer scores and severities, confidence, risk, and repair cycles;
- completed agent-run metadata and flight-recorder events;
- SHA-256 digests of the captured diff and Markdown proof;
- an integrity block containing the canonical payload digest.

The receipt ID will be the `fg_` prefix plus the first 16 hexadecimal characters of the canonical SHA-256 digest. Canonical JSON uses sorted keys and compact separators. The digest covers the evidence payload before the derived `receipt_id` and `integrity` fields are attached, avoiding a self-referential hash while keeping rebuilding deterministic.

`GET /api/tasks/{task_id}/proof` will preserve the existing `markdown` field and add a nullable `receipt` field. Before proof exists, `receipt` is `null`; terminal proof responses include the complete receipt. This keeps the polling API backwards-compatible and avoids adding another request to every refresh cycle.

## Frontend experience

The accepted graphite, slate, and electric-mint dashboard remains unchanged except for the proof-package header and receipt strip. When a receipt exists, the surface will show:

- a short `Evidence sealed · fg_…` identity;
- `Copy proof`, preserving current behavior;
- `Download receipt`, producing a local JSON file from the real API payload.

Controls remain keyboard accessible, use the existing Lucide outline language, and collapse cleanly on mobile. No fake metrics, decorative dashboard cards, or new navigation will be added.

## README and poster

The README will open with a custom wide cinematic poster saved inside the repository. The poster will use ForgeGuard’s graphite/mint visual language and depict an unsafe red code stream entering a guarded evidence pipeline and leaving as a sealed green patch. It will contain only the exact product name and concise tagline so it remains legible on GitHub.

The rewritten README will include:

- a one-sentence value proposition and concise badges;
- the 60-second problem/solution story;
- a judge-oriented “why this matters” section;
- a product screenshot and exact three-minute demo script;
- Mermaid system architecture, verification loop, and sequence diagrams;
- the weighted risk equation and critical-finding rule;
- the verification receipt contract and trust boundaries;
- local setup for deterministic and provider-backed modes;
- API surface, repository map, testing matrix, deployment, security, and roadmap;
- a clear explanation of how Codex was used to build and validate the project.

The README will avoid unsupported adoption claims, fabricated metrics, and vague “AI-powered” language.

## Secret handling

Real credentials must live only in ignored `backend/.env`. The tracked `backend/.env.example` must contain empty placeholders. Automated verification will scan tracked content and Git diffs for provider-key patterns. Because credentials were present in the existing local commit before this upgrade, the handoff will require rotating those credentials before publishing and, if preserving the current repository history, removing the original secret-bearing commit from the public branch.

## Error handling

Receipt generation will be total for any persisted task: missing proof produces `receipt: null`; missing optional evidence becomes an empty list or neutral value; canonical serialization uses JSON-compatible primitives only. Download controls will be disabled until a receipt exists and will revoke generated object URLs immediately after use.

Provider connectivity checks will report only provider name, success/failure, HTTP status where applicable, and model response validity. Credentials and response bodies will never be printed.

## Testing and acceptance

Backend tests will first fail for the missing deterministic receipt builder and extended proof response, then pass after implementation. Frontend tests will first fail for the missing receipt identity/download behavior, then pass after implementation.

Release gates are:

- backend pytest and Ruff;
- frontend Vitest, type-check, lint, and production build;
- desktop and mobile Playwright flows through the complete deterministic repair cycle;
- demo repository pytest;
- OpenAI, Groq, and GitHub credential connectivity checks with secret-safe output;
- tracked-file and pending-diff secret scans;
- Docker build when Docker is available;
- visual comparison of the accepted dashboard concepts and fresh desktop/mobile renders.

The upgrade is accepted when the deterministic demo reaches `VERIFIED`, the UI downloads a JSON receipt whose ID matches its SHA-256 digest, the README renders with valid Mermaid diagrams and local images, no current tracked file contains a live credential, and every available release gate passes.
