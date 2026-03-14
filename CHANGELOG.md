# Changelog

## 2026-03-14

### Stabilize The Single-Chat Request/Response Path

- Hardened OpenAI response handling for missing, blank, and malformed model content.
- Refactored chat response formatting to safely render mixed plain text and fenced code blocks.
- Standardized HTMX bot/error message HTML for the single-chat request/response path.
- Returned deterministic 400 responses for missing or blank user messages.
- Stopped exposing raw unexpected exception text in user-facing error messages.
- Added regression tests for route errors, formatter edge cases, and model-response fallback paths.
