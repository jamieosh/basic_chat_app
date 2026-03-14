# Changelog

## 2026-03-14

### Reduce External Runtime Fragility

- Kept CDN-hosted HTMX and Tailwind as the intentional Phase 1 default instead of introducing a frontend build step.
- Added explicit template comments that identify the external browser assets and document the HTMX pin plus the reviewed Tailwind CDN exception.
- Documented the default external frontend runtime assumptions, tradeoffs, and fork guidance in the README.
- Added regression coverage that locks the home page to the reviewed HTMX and Tailwind asset references.

### Strengthen Baseline Request And Failure UX

- Prevented duplicate chat submissions while an HTMX request is already in flight.
- Simplified the normal loading state to the existing typing dots while keeping footer status messaging for validation and failure conditions.
- Made unavailable-agent and startup-incomplete chat requests render consistent inline HTML error states instead of falling back to raw framework errors.
- Added focused route and Playwright coverage for duplicate-submit prevention, server-side failure rendering, degraded home-page state, and transport-error fallback behavior.

### Expand Regression Coverage For Baseline Reliability

- Added focused regression tests for route helper behavior, partial readiness states, and remaining OpenAI error branches.
- Added settings and diagnostics coverage for invalid values, fallback defaults, failure summaries, and prompt-specific startup paths.
- Added agent-level regression tests for context-prefix behavior, prompt lookup failures, and GPT-5 temperature-parameter compatibility.
- Added formatter edge-case coverage for empty input, empty fenced blocks, adjacent code fences, and invalid input types.

### Finish Portability And Configuration Baseline

- Added a central runtime settings layer for OpenAI and CORS configuration.
- Made `.env` loading explicitly project-root-based so startup does not depend on the current working directory.
- Switched CORS behavior to environment-driven defaults aligned with the current no-auth baseline.
- Allowed model name, prompt name, timeout, and temperature to be configured without code changes.
- Adjusted GPT-5 request construction to omit unsupported `temperature` parameters while preserving custom temperature support for older model families.
- Updated setup documentation and example environment configuration to match the supported runtime surface.
- Added regression coverage for settings parsing, CORS wiring, configured prompt lookup, and env-driven agent startup.

### Improve Startup And Runtime Diagnostics

- Added explicit startup diagnostics for required configuration and app asset checks.
- Split liveness and readiness behavior with a dedicated readiness endpoint that reports failed checks.
- Refined startup, request, and OpenAI-path logging to be more actionable and lower-noise for local debugging.
- Added deterministic regression tests for startup failures, readiness states, and logging config parsing.

### Stabilize The Single-Chat Request/Response Path

- Hardened OpenAI response handling for missing, blank, and malformed model content.
- Refactored chat response formatting to safely render mixed plain text and fenced code blocks.
- Standardized HTMX bot/error message HTML for the single-chat request/response path.
- Returned deterministic 400 responses for missing or blank user messages.
- Stopped exposing raw unexpected exception text in user-facing error messages.
- Added regression tests for route errors, formatter edge cases, and model-response fallback paths.

### Keep Default Behavior Deterministic And Neutral

- Removed hardcoded domain-specific default context from the baseline OpenAI request path.
- Renamed the default assistant identity to the neutral, repo-branded `AI Chat`.
- Kept the user-context prompt seam in place while making it empty by default.
- Updated the default OpenAI temperature baseline to align with the current GPT-5 default-model behavior.
- Added regression tests that lock the default prompt payload to raw user input unless context is explicitly configured.

### Polish Baseline Chat Input Layout

- Synced the `Send` button height with the textarea's rendered single-line height so the chat composer stays visually aligned before the input expands.
