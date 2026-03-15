# Phase 1 Done

This record reconstructs the completed Phase 1 work from the deleted `PHASE 1 BACKLOG.md` history plus the shipped changelog entries.

Phase 1 was the "Reliable Single-Chat Baseline" phase.

## Completed Items

### Stabilize The Single-Chat Request/Response Path

Delivered:

- hardened model-response handling for missing, blank, and malformed assistant content
- refactored chat output formatting so mixed plain text and fenced code blocks render safely
- standardized inline bot and error message HTML for the single-chat request/response flow
- returned deterministic validation errors for missing or blank user messages
- stopped surfacing raw unexpected exception text to end users

What the user sees:
The default single-chat loop behaves more predictably, especially when model output is malformed or a request fails.

### Improve Startup And Runtime Diagnostics

Delivered:

- added explicit startup diagnostics for required configuration and asset checks
- split liveness and readiness behavior with a readiness endpoint that reports failed checks
- refined startup, request, and OpenAI-path logging so local debugging is more actionable and less noisy
- added deterministic coverage for startup failures, readiness states, and logging configuration parsing

What the user sees:
No major UI change, but local setup and troubleshooting are much clearer when startup or dependency problems occur.

### Keep Default Behavior Deterministic And Neutral

Delivered:

- removed hardcoded domain-specific default context from the baseline OpenAI path
- renamed the default assistant identity to the neutral, repo-branded `AI Chat`
- kept the user-context prompt seam in place while making it empty by default
- aligned the default GPT-5 request behavior with current model expectations
- added regression tests that lock the default prompt payload to explicit user input unless extra context is configured

What the user sees:
The out-of-box assistant behaves more neutrally and predictably, which makes forks and experiments easier to compare.

### Finish Portability And Configuration Baseline

Delivered:

- added a central runtime settings layer for OpenAI and CORS configuration
- made `.env` loading explicitly project-root-based so startup no longer depends on the current working directory
- switched CORS behavior to environment-driven defaults aligned with the current no-auth baseline
- allowed model name, prompt name, timeout, and compatible temperature settings to be changed without code edits
- updated setup documentation and the example environment configuration to match the supported runtime surface

What the user sees:
The project is easier to run consistently across environments, and core runtime choices can be changed without editing application code.

### Strengthen Baseline Request And Failure UX

Delivered:

- prevented duplicate submissions while a request is already in flight
- simplified the normal loading state to the existing typing dots while preserving footer status messaging for validation and failure cases
- made unavailable-agent and startup-incomplete requests render consistent inline HTML error states
- added focused route and Playwright coverage for duplicate-submit prevention, degraded home-page state, and transport-error fallback behavior

What the user sees:
The single-chat UI feels steadier under normal use and degrades more cleanly when the backend is unavailable.

### Reduce External Runtime Fragility

Delivered:

- kept CDN-hosted HTMX and Tailwind as the intentional no-build-step default instead of an accidental dependency
- added explicit template comments that identify the external browser assets and the reviewed HTMX/Tailwind choices
- documented the external frontend runtime assumptions, tradeoffs, and fork guidance in the README
- added regression coverage that locks the home page to the reviewed HTMX and Tailwind asset references

What the user sees:
No direct feature change, but contributors and fork maintainers now have a clearer record of the default frontend runtime assumptions.

### Expand Regression Coverage For Baseline Reliability

Delivered:

- added focused regression tests for route helpers, partial readiness states, and remaining OpenAI error branches
- added settings and diagnostics coverage for invalid values, fallback defaults, failure summaries, and prompt-specific startup paths
- added agent-level regression tests for context-prefix behavior, prompt lookup failures, and GPT-5 compatibility details
- added formatter edge-case coverage for empty input, empty fenced blocks, adjacent code fences, and invalid input types

What the user sees:
No visible UI change, but the baseline is much safer to refactor because the main failure paths are now covered.

### Complete Phase 1 Documentation Alignment

Delivered:

- added a clear `Phase 1 Complete Means` definition to the README
- documented the default security posture and the main safe customization points for prompts, runtime wiring, and chat UI behavior
- updated `plans/PHASES.md` to mark Phase 1 complete and describe the shipped baseline accurately
- tightened planning language so authentication, streaming, persisted multi-chat continuity, generalized runtime abstraction, and deployment hardening remained clearly deferred beyond Phase 1
- reduced the old Phase 1 backlog to an explicit no-remaining-items marker before it was later removed during Phase 2 planning cleanup

What the user sees:
No product change, but the project’s shipped baseline and deferred work became much clearer for contributors and forks.

## Phase Result

Phase 1 completed the reliable single-chat baseline:

- the app could be cloned, configured with `OPENAI_API_KEY`, started, and used without changing code
- the default UX was a single-turn request/response flow with deterministic validation and inline failure handling
- runtime configuration and startup behavior were portable and environment-driven
- the default UI worked without a frontend build step
- extension seams for prompts, provider wiring, and chat UI behavior were explicit enough for later phases to build on
