---
name: phase-start
description: Use when the user wants to start planning the next delivery phase in this repository. This skill verifies there is no active phase already underway, inspects the next phase in `plans/PHASES.md`, produces a grounded phase briefing from the repo's current state, and creates `plans/PHASE X DESIGN.md` plus `plans/PHASE X BACKLOG.md`.
---

# Phase Start

Use this skill to open the next delivery phase. Do not implement backlog items in this skill.

## Workflow

1. Read `AGENTS.md`, `plans/PHASES.md`, `plans/VISION.md`, and `plans/PARKING LOT.md` before drafting anything.
2. Establish the current planning state:
   - Inspect `plans/` for active `PHASE * BACKLOG.md` and `PHASE * DESIGN.md` files outside `plans/done/`.
   - Read `plans/PHASES.md` and identify any phase heading marked `(In Progress)`.
   - If an active phase already exists, stop, report which phase is still underway, and do not create new phase files.
3. Identify the next phase from `plans/PHASES.md`:
   - Use the lowest-numbered phase that is not marked `(Completed)` and is not already underway.
   - Reuse the repository's existing phase naming exactly.
   - Derive the target file paths as `plans/PHASE X DESIGN.md` and `plans/PHASE X BACKLOG.md`.
4. Check whether either target file already exists.
   - If it does, stop and report the existing path instead of overwriting it.
5. Inspect the current repo reality before drafting the new phase:
   - Read the latest active or most recently completed phase docs, including the prior phase design/backlog and the matching `plans/done/PHASE X DONE.md` file when present.
   - Read the current top-level product and contributor docs that define the shipped state, especially `README.md` and `AGENTS.md`.
   - Read the code and tests that best represent the app's current architecture and product surface. Prefer the main route layer, persistence/service seams, harness/runtime code, and the highest-signal test files.
6. Produce a structured phase-start briefing in your working notes before writing files. The briefing should cover:
   - Current shipped product shape
   - Architecture and workflow seams already in place
   - Important gaps and unresolved constraints
   - What should remain stable in the next phase
   - Candidate delivery slices in likely execution order
   - Key risks, dependencies, and things the user should decide early
7. Write `plans/PHASE X DESIGN.md`.
   - The design doc should describe the common concerns across the whole phase rather than item-by-item implementation tasks.
   - Keep it grounded in what already exists today.
   - Include links to the matching backlog file and `plans/PARKING LOT.md`.
   - Recommended section shape:

```markdown
# Phase X Design

Short summary paragraph.

See [`plans/PHASE X BACKLOG.md`](...) for the proposed delivery slices.

See [`plans/PARKING LOT.md`](...) for known ideas that are intentionally deferred.

## Goal

## What This Phase Means For Users

## What This Phase Means For Developers And Forks

## Design Principles

## Current State And Gaps

## Scope Decisions

## Expected Architecture / Product Shape

## Delivery Guardrails

## Out Of Scope

## Open Questions To Keep Visible
```

8. Write `plans/PHASE X BACKLOG.md`.
   - The backlog should be a sequential list of independently deliverable slices.
   - Each item should be scoped so it can be planned and shipped through the existing feature workflow.
   - Keep completed prior-phase work out of the new backlog unless explicitly carried over as unfinished dependency work.
   - Recommended structure:

```markdown
# Phase X Backlog

Short summary paragraph.

Completed items should move to `plans/done/PHASE X DONE.md` once shipped.

## Proposed Items

- `PX-01 <title>`: outcome-focused description
- `PX-02 <title>`: outcome-focused description

## Sequencing Notes

- Why the order matters
- Known dependencies or late-phase proof items
```

9. Keep the docs realistic:
   - Do not invent capabilities that the repo does not have.
   - Call out carried-forward constraints when they materially shape the phase.
   - Favor product and architecture intent over implementation detail, but make the backlog concrete enough to drive `feature-start`.
10. Report the target phase, the new file paths, and the main briefing conclusions. Then stop.
