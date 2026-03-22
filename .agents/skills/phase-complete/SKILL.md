---
name: phase-complete
description: Use when the user wants to close out an active delivery phase in this repository. This skill verifies the active phase backlog has no remaining items, moves the phase design doc into `plans/done/`, deletes the active phase backlog file, and updates `plans/PHASES.md` to mark that phase completed.
---

# Phase Complete

Use this skill when a delivery phase is ending. Do not continue if the active phase still has unfinished backlog work.

## Workflow

1. Read `AGENTS.md`, `plans/PHASES.md`, and inspect `plans/` for active phase planning files.
2. Identify the current active phase:
   - Prefer the phase marked `(In Progress)` in `plans/PHASES.md`.
   - Confirm the matching active files exist at `plans/PHASE X DESIGN.md` and `plans/PHASE X BACKLOG.md`.
   - If no phase is clearly active, stop and report that there is no in-progress phase to complete.
3. Validate that the phase backlog is actually empty before making any edits.
   - Read `plans/PHASE X BACKLOG.md`.
   - Treat any remaining proposed backlog item as blocking completion.
   - If backlog items remain, stop, report that the phase cannot be completed yet, and point the user at the active backlog file.
4. Check the destination paths under `plans/done/`.
   - Move `plans/PHASE X DESIGN.md` to `plans/done/PHASE X DESIGN.md`.
   - Do not overwrite an existing done-path file; if the destination already exists, stop and report it.
5. Delete `plans/PHASE X BACKLOG.md` only after the empty-backlog check passes.
6. Update `plans/PHASES.md`:
   - Change the active phase heading from `(In Progress)` to `(Completed)`.
   - Keep the existing prose intact unless a small wording change is necessary to keep the status text coherent.
   - Do not change later phase descriptions while closing the current one.
7. Preserve user work:
   - If the relevant planning files already contain unrelated edits that conflict with the completion update, stop instead of guessing.
   - Do not rewrite unrelated docs in `plans/` or `plans/done/`.
8. Report what changed:
   - completed phase number and title
   - moved design-doc path
   - deleted backlog path
   - `plans/PHASES.md` status update

## Completion Rule

This skill is intentionally strict. If the active backlog still lists even one deliverable item, do not complete the phase.
