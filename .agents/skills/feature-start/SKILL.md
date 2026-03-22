---
name: feature-start
description: Use when the user wants to plan a new feature in this repository without implementing it yet. This skill identifies the active backlog item, refines scope, inspects the relevant code and docs, creates a `codex/<slug>` branch, and writes `plans/<slug>.md`.
---

# Feature Start

Use this skill for planning only. Do not write implementation code.

## Workflow

1. Read `AGENTS.md`, `plans/PHASES.md`, and the active phase backlog before proposing scope.
   - Prefer the highest-numbered backlog file that still has active items, which is currently `plans/PHASE 3 BACKLOG.md`.
   - Also note the matching shipped-items file under `plans/done/` so the plan uses the repo's real phase names and paths.
2. Pick the feature:
   - If the user named a feature, match it against the backlog and resolve ambiguity before continuing.
   - If no feature was named, present the top 5 active backlog items as a numbered menu and ask the user to choose one.
3. Refine the scope for this increment and draft:
   - Title
   - Slug in kebab-case
   - Source backlog item or phase slice
   - Scope
   - Non-goals
   - Acceptance criteria
   - Risks and assumptions
4. If anything is unclear, ask one concise batched clarification question. Do not proceed until the user confirms the scope.
5. Inspect `git status --short` before creating a branch.
   - If the worktree is dirty in a way that could conflict with planning work, stop and ask the user how to proceed.
   - Do not overwrite existing planning-doc changes that you did not make.
6. Create the branch from `main`:

```bash
git switch main
git pull --ff-only
git switch -c codex/<slug>
```

7. Inspect the relevant code, tests, templates, configs, and contributor docs before finalizing the plan. Read files first; do not guess at interfaces.
8. If inspection changes the scope or reveals new uncertainty, ask the user before finalizing the plan.
9. Write `plans/<slug>.md` with this structure:

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

10. Confirm the branch name and plan file path, then stop. Do not edit backlog, done, changelog, or implementation files in this skill. Tell the user to run `$feature-build` when ready.
