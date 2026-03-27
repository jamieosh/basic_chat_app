---
name: phase-start
description: Plan the next delivery phase (not a single feature). Use when the user asks to start the next phase by creating `plans/PHASE X DESIGN.md` and `plans/PHASE X BACKLOG.md` from `plans/PHASES.md`.
---

# Phase Start

Open the next delivery phase. Do not implement backlog items in this skill.

## Workflow

1. Read `AGENTS.md`, `plans/PHASES.md`, `plans/VISION.md`, and `plans/PARKING LOT.md`.
2. Establish planning state from `plans/`:
   - Find active `PHASE * BACKLOG.md` / `PHASE * DESIGN.md` files outside `plans/done/`.
   - Find any phase in `plans/PHASES.md` marked `(In Progress)`.
   - If an active phase already exists, stop and report it. Do not create new phase files.
3. Identify the next phase from `plans/PHASES.md`:
   - Use the lowest-numbered phase not marked `(Completed)` and not currently in progress.
   - Reuse the phase title exactly as written.
   - Derive target files: `plans/PHASE X DESIGN.md` and `plans/PHASE X BACKLOG.md`.
4. If either target file already exists, stop and report the path instead of overwriting it.
5. Ground the phase on current repo reality:
   - Read prior phase docs (`plans/PHASE * ...` and `plans/done/PHASE * DONE.md` as applicable).
   - Read `README.md` and `AGENTS.md`.
   - Read high-signal architecture and test files (routes, service/persistence seams, harness layers, core tests).
6. Build a short internal briefing before writing files:
   - current shipped shape
   - current architecture seams and constraints
   - major gaps that phase should address
   - delivery slices and rough dependency order
   - key risks and early user decisions needed
7. Write `plans/PHASE X DESIGN.md` as phase-level guidance (not item-by-item implementation).
   - Keep it grounded in current reality.
   - Link the new backlog file and `plans/PARKING LOT.md`.
   - Include: goal, user impact, developer/fork impact, principles, current gaps, scope decisions, expected shape, guardrails, out-of-scope, open questions.
8. Write `plans/PHASE X BACKLOG.md` as an ordered list of independent delivery items.
   - Pull phase number/title/goal from `plans/PHASES.md`.
   - Keep each item shippable through the existing workflow (`codex/<slug>` + `plans/<slug>.md` + `$feature-start`).
   - For each item include: ID (`P<N>-NN`), title, size, dependencies, 2-3 sentence description, and `What the user will see`.
   - End with a `Deferred` section and move true non-phase ideas into `plans/PARKING LOT.md`.
9. Keep documentation realistic:
   - Do not invent capabilities.
   - Preserve active constraints when they shape phase design.
   - Keep detail high enough that the next item can be selected and planned immediately.
10. Report target phase, new file paths, and key briefing conclusions, then stop.
