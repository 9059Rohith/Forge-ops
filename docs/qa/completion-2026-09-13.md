# Application completion — September 13, 2026

The previously uncommitted application work is integrated and verified: same-origin API transport, explicit live/demo selection, read-only audits, monorepo test discovery, truthful failed/no-test decisions, immutable GitHub identity migration, billing boundaries, responsive graph, and task lookup.

Additional issues were found and fixed during completion:

- Authorization cards now select the most severe finding, then the lowest confidence score, rather than selecting the safest review.
- Repeated submissions tolerate duplicate project rows created by concurrent requests, rather than returning an internal server error.
- The configured Groq reviewer model was unavailable to the account. The default and example now use `openai/gpt-oss-120b`, verified against the account's models endpoint and [Groq's model documentation](https://console.groq.com/docs/model/openai/gpt-oss-120b).
- Nonzero test-process exit codes now block verification even when reported pass/total counts match; regression cases cover errors and timeouts.
- Explicit read-only security requests with negated change wording stay in the audit workflow.
- Audit context and finding validation reject symlink targets outside the repository.

## Verification

| Check | Result |
|---|---|
| Backend pytest | 111 passing |
| Backend Ruff | Passing |
| Frontend Vitest | 26 passing |
| Frontend ESLint / TypeScript | Passing |
| Next.js production build | Passing |
| Application Playwright journeys | 4 passing: desktop/mobile proof flow and keyboard/layout checks |
| Separate demo capture | Passing; no browser page errors |
| Downloaded demo receipt SHA-256 | Independently recomputed and matched |
| Remotion ESLint / TypeScript | Passing |
| Demo repository pytest | 3 passing |
| Backend and frontend Docker images | Both built successfully |
| Final MP4 | Full decode passed; 1920×1080, 24 fps, 115.67 seconds, H.264/AAC |
| Audio | Mean -20.9 dB, peak -1.5 dB; audible and unclipped |

Browser tests run with one worker to avoid cold-build resource contention. The temporary capture test was removed after producing the video assets.

## Actual provider-backed run

A disposable local Git repository contained a deliberately incorrect `calculator.add` and a test. A real OpenAI engineer changed only `calculator.py`; Groq security/scope reviewers and the OpenAI adversarial reviewer completed successfully. The result was `verified`, 1/1 tests passed, 94.0% confidence, no repair cycles, and the original source repository remained clean. The raw local run evidence is retained in the ignored `.forgeguard-work/live-smoke-result.json`.

This validates one small live task, not every possible repository, language, provider outage, or risk policy.

## Demo artifact

The narrated 1080p recording is linked from the root README and stored at `docs/demo/forgeguard-demo.mp4`. Its reproducible source, real application captures, narration, and original ambient audio live in `demo-video/`. The showcase receipt is `fg_f3e9f8e042a3f1ea`. A copy and subtitle file were saved to the user's Downloads folder as `ForgeGuard-Demo.mp4` and `ForgeGuard-Demo.srt`; SHA-256 checks confirmed identical video copies. Machine-readable media checks are in [media-verification.json](../demo/media-verification.json).

## External integration limits

GitHub App installation credentials and Dodo payment credentials are not configured locally. Their unit/API contracts pass, but live signed-webhook delivery, real checkout, and automated pull-request creation were not exercised. Deployment credentials and service settings remain operator-managed. Roadmap items such as KMS signing, remote sandboxes, and team accounts remain future features, not claims of this release.
