# Feature: Session Metadata And Inspectability Surface

## Slug
p4-02-session-metadata-and-inspectability-surface

## Source
plans/PHASE 4 BACKLOG.md - P4-02 Session Metadata And Inspectability Surface

## Scope
Expose a read-only session inspectability surface in the active chat header so users can see stable session and runtime identity details (session identity, runtime binding, and latest run metadata) without changing existing send/navigation behavior.

## Non-goals
Lineage actions (fork/duplicate/replay/resume), profile/policy editing workflows, arbitrary in-place runtime switching, and any broader control-plane behavior.

## Acceptance Criteria
- [x] Active chat view shows an inspectability section with stable session identity details (at minimum session ID and lifecycle timestamps) for the currently selected session.
- [x] Active chat view shows bound runtime/agent identity details derived from the selected session binding (harness key/version plus provider/model presentation), not only app-default banner metadata.
- [x] Active chat view shows latest run metadata for that session (run ID, kind, status) when a run exists, and degrades cleanly when no run record exists yet.
- [x] Metadata is consistent across full page load and HTMX partial updates (`/chats/{chat_id}/transcript`, `/chat-start/transcript`, send-response OOB header updates).
- [x] Start and not-found shells remain unchanged in behavior and accessibility semantics.

## Risks / Assumptions
The current schema does not yet include editable profile fields (scope/notes/guidance), so this increment assumes inspectability is sourced from existing persisted session/run/binding data only. Added header density can regress small-screen readability, and per-render metadata lookups may add query overhead if not kept to bounded, indexed reads.

## Implementation Steps
- [x] Step 1: Add repository-level read support for session inspectability metadata (including latest run record lookup for a selected session) and expose typed return shapes needed by routes. - files: `persistence/repository.py`, `persistence/__init__.py`
- [x] Step 2: Build route context helpers for session inspectability so active-chat rendering can resolve selected-session runtime binding and pass normalized metadata into templates for both full-page and OOB/partial paths. - files: `main.py`
- [x] Step 3: Extend active chat header template to render a compact, readable metadata surface (session, runtime binding, latest run) with graceful empty-state handling and responsive layout treatment. - files: `templates/components/chat_view_header.html`, `static/css/chat.css`
- [x] Step 4: Add route/service regression coverage for metadata rendering, HTMX update consistency, and no-regression start/not-found states. - files: `tests/test_main_routes.py`
- [x] Step 5: Add persistence coverage for new inspectability read helpers and run-lookup behavior. - files: `tests/test_chat_repository.py`
- [x] Step 6: Update visual smoke assertions/snapshots only where header output intentionally changes. - files: `tests/e2e/test_chat_smoke.py`, `tests/e2e/snapshots/*`

## Tests to Add
- [x] `test_main_routes.py`: active chat page/header includes session/runtime metadata fields for a bound chat session -> covers AC: 1, 2
- [x] `test_main_routes.py`: header includes latest run metadata after a send and degrades cleanly when no run exists -> covers AC: 3
- [x] `test_main_routes.py`: HTMX transcript/header swaps keep metadata aligned when switching chats and when returning to `/chat-start` -> covers AC: 4, 5
- [x] `test_chat_repository.py`: latest-run lookup returns most recent run for a chat and handles no-run sessions deterministically -> covers AC: 3
- [x] `test_chat_smoke.py`: visual/assertion coverage for active header metadata on desktop/mobile shells -> covers AC: 1, 2, 4

## Definition of Done
- [ ] All acceptance criteria checked off
- [ ] All new or updated tests pass
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy .` passes
- [ ] `uv run python -m pytest` passes
- [ ] `README.md` updated if user-visible behavior changed
- [ ] E2E or visual checks run when UI behavior changes materially
- [ ] `CHANGELOG.md` updated when the feature ships
- [ ] Matching phase backlog and `plans/done/PHASE X DONE.md` updated when the feature ships
- [ ] `AGENTS.md` updated if architecture or contributor guidance changes
