---
name: feature-start
description: Use when the user wants to start and plan a new feature/phase in this repository without writing implementation code yet. This skill selects a backlog item, refines scope, inspects the codebase, creates a `codex/<slug>` branch, and writes `plans/<slug>.md`.
---

# Feature Start

Use this skill for planning only. Do not write implementation code.

## Workflow

1. Read `plans/PHASE X BACKLOG.md`.
2. Pick the feature:
   - If the user named a feature, match it against the backlog and resolve ambiguity before continuing.
   - If no feature was named, present the top 5 active backlog items as a numbered menu and ask the user to choose one.
3. Refine the scope for this increment and draft:
   - Title
   - Slug in kebab-case
   - Scope
   - Non-goals
   - Acceptance criteria
   - Risks and assumptions
4. If anything is unclear, ask one concise batched clarification question. Do not proceed until the user confirms the scope.
5. Create the branch:

```bash
git switch main
git pull --ff-only
git switch -c codex/<slug>
```

6. Inspect the relevant code, tests, templates, and configs before planning. Read files first; do not guess at interfaces.
7. If inspection changes the scope or reveals new uncertainty, ask the user before finalizing the plan.
8. Write `plans/<slug>.md` with this structure:

```markdown
# Feature: <title>

## Slug
<slug>

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
- [ ] `CHANGELOG.md` updated if the feature ships
- [ ] `plans/PHASE X BACKLOG.md` updated when the feature ships
```

9. Confirm the plan file path and stop. Tell the user to run `$feature-build` when ready.
