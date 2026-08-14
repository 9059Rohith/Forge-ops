# ForgeGuard Visual Fidelity Ledger

QA date: 2026-08-15

## Evidence

- Accepted entry concept: `docs/design/forgeguard-entry-concept.png` (1584×1024)
- Entry render: `docs/qa/forgeguard-entry-render.png` (1584×1024 viewport)
- Accepted task concept: `docs/design/forgeguard-task-concept.png` (1516×1045)
- Verified task render: `docs/qa/forgeguard-task-render.png` (1516×1045 viewport)
- Capture method: Playwright Chromium full-page screenshots after real API interaction.

## Comparison points

| Area | Concept evidence | Initial render evidence | Resolution |
|---|---|---|---|
| Entry hierarchy | Two-line editorial headline aligned with the task form | Headline wrapped to three lines and made the left side feel heavier | Reduced desktop display scale, widened its text measure, and preserved the exact two-line composition |
| Entry layout | Form begins near the center line and is 647px wide | Form sat roughly 50px too far right | Left-aligned the fixed-width form within the second grid column |
| Workflow rail | One open horizontal rail with four stages, larger outline icons, and generous height | Rail was too wide and visually light | Constrained it to 1372px, increased vertical rhythm, and enlarged icon containers and labels |
| Dashboard density | Graph, three reviewer rows, diff, evidence rail, and proof fit a small-laptop command-center viewport | First implementation produced a page almost twice the concept height | Compressed graph coordinates, reviewer padding, Monaco height, and proof preview while keeping every region usable |
| Agent graph | Clear Engineer → three parallel reviewers → Risk Engine → verdict anatomy | Early fit-to-view scaling made nodes too small | Repositioned reviewer nodes into the actual 190px canvas to restore legible node scale and clean connectors |
| Evidence rail | Fixed-height evidence summary and scrolling flight log | Flight log expanded with the complete trace and stretched the page | Fixed the recorder at 480px and retained the full trace in an accessible scroll region |
| Proof package | Compact proof rail at the bottom | Full Markdown body dominated the page | Kept rendered GFM Markdown and copy action, but placed the body in a compact scroll region |
| Palette and geometry | Graphite canvas, cool slate bands, mint verification, amber repair, hairline borders, 8–10px radii | Implementation matched closely | Locked shared Tailwind tokens and removed decorative containers or gradients beyond the concept’s faint background treatment |
| Typography | Sans display hierarchy with monospaced fields, scores, timestamps, and code | Initial form and workflow labels were undersized | Increased control text, input text, workflow labels, and entry brand scale; no browser-default control typography remains |
| Responsive behavior | Desktop density with a credible mobile continuation | Potential horizontal pressure from summary and graph | Verified Pixel 7 with no page overflow; summary stacks, detail rail moves below, and graph remains internally navigable |

## Above-the-fold copy diff

The visible entry copy matches the locked list: `ForgeGuard`, `Autonomous engineering, with proof.`, the supplied support sentence, `Repository`, `Branch`, `Engineering task`, `Start autonomous engineering`, and the workflow labels. No hero eyebrow, badge, fake metric, marketing navigation, or extra claim was added.

One intentional data deviation remains: the repository field defaults to `demo` rather than the concept’s illustrative `forgeguard-labs/demo-checkout`. `demo` is the executable backend locator that makes the end-to-end hackathon path work without a network clone. Task-screen scores, timestamps, repository label, tests, and findings are likewise real API output rather than frozen concept values.

## Sign-off

The final implementation preserves the accepted information hierarchy, container model, palette, typography roles, interaction model, responsive behavior, and required copy. No material visual mismatch remains that would block agency sign-off; the recorded deviations are functional data substitutions, not design reinterpretations.
