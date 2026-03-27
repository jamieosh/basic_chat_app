---
name: feature-start
description: Plan one feature increment without implementation. Use when the user asks to choose/scope the next backlog item, create `plans/slug.md`, and create or reuse `codex/slug`; not for coding or shipping.
---

# Feature Start

Plan only. Do not write implementation code.

## Workflow

1. Establish context first:

```bash
git branch --show-current
git status --short
ls plans
```

2. Read `AGENTS.md`, `plans/PHASES.md`, and the active phase backlog before proposing scope.
   - Detect the active phase from the `(In Progress)` marker in `plans/PHASES.md`.
   - If no phase is explicitly marked in progress, use the highest-numbered `plans/PHASE * BACKLOG.md` that still has unshipped items.
   - Note the matching shipped-items file under `plans/done/`.

3. Pick the feature:
   - If the user named a feature, map it to a backlog item and resolve ambiguity before continuing.
   - If no feature was named, present the top 5 backlog candidates as a numbered menu and ask the user to choose one.

4. Refine the increment and draft:
   - title
   - slug (kebab-case)
   - source backlog item
   - scope
   - non-goals
   - acceptance criteria
   - risks/assumptions

5. If scope is ambiguous, ask one concise batched clarification question and wait for confirmation.

6. Before branch work, inspect the worktree:

```bash
git status --short
```

   - Respect unrelated edits.
   - If planning changes would conflict with existing edits in `plans/` or docs, stop and ask the user.

7. Create or reuse the feature branch:
   - If `codex/<slug>` already exists, switch to it.
   - Otherwise:

```bash
git switch main
git pull --ff-only
git switch -c codex/<slug>
```

8. Inspect relevant code/tests/docs before finalizing the plan. Read files first; do not assume interfaces.

9. If inspection changes scope materially, ask the user before writing the plan.

10. Write `plans/<slug>.md` using this structure:

```markdown
# Feature: <title>

## Slug
<slug>

## Source
<phase/backlog item>

## Scope
<scope>

## Non-goals
<non-goals>

## Acceptance Criteria
- [ ] <criterion 1>
- [ ] <criterion 2>

## Risks / Assumptions
<risks>

## Implementation Steps
- [ ] Step 1: <description> — files: <file list>
- [ ] Step 2: <description> — files: <file list>

## Tests to Add
- [ ] <test case> -> covers AC: <criterion>

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
```

11. Confirm the branch and plan path, then stop.
   - Do not edit backlog, done, changelog, or implementation files in this skill.
   - Tell the user to run `$feature-build` when ready.
