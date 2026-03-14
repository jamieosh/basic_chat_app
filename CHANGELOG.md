# Changelog

## 2026-03-14

### Finish Portability And Configuration Baseline

- Added a central runtime settings layer for OpenAI and CORS configuration.
- Made `.env` loading explicitly project-root-based so startup does not depend on the current working directory.
- Switched CORS behavior to environment-driven defaults aligned with the current no-auth baseline.
- Allowed model name, prompt name, timeout, and temperature to be configured without code changes.
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
- Fixed the default OpenAI request temperature at `0.0` and documented Phase 1 baseline guarantees in the README.
- Added regression tests that lock the default prompt payload to raw user input unless context is explicitly configured.
