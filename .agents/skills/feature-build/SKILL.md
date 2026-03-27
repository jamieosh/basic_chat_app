---
name: feature-build
description: Implement a planned feature from `plans/slug.md` on `codex/slug`. Use when the user asks to execute plan steps, add/update tests, run targeted checks, and make incremental commits; not for final merge/ship.
---

# Feature Build

Implement an existing feature plan incrementally.

## Workflow

1. Establish context:

```bash
git branch --show-current
git status --short
```

2. Require the current branch to be `codex/<slug>`. If it is `main` or does not start with `codex/`, stop and tell the user to switch branches or run `$feature-start`.
3. Derive `<slug>` from the branch name and read `AGENTS.md` plus `plans/<slug>.md` in full before making changes.
4. Respect unrelated dirty worktree files. Never revert user changes. If the requested implementation conflicts with unrelated edits in the same files, stop and ask the user how to proceed.
5. Resume from the first unchecked implementation step in `plans/<slug>.md`. Do not redo completed steps.
6. For each remaining step:
   - Implement the step.
   - Update or add tests for the behavior changed by that step.
   - Run targeted checks for the affected area. Prefer the smallest useful command, for example:

```bash
uv run python -m pytest tests/test_main_routes.py -q
uv run python -m pytest tests/test_openai_agent.py -q
uv run python -m pytest tests/test_html_formatter.py -q
uv run ruff check <touched paths>
```

   - Fix failures before moving on.
   - Mark the completed implementation step in `plans/<slug>.md` immediately after it is done.
   - Check off any acceptance criteria that are now fully satisfied.
   - Check off any completed test items or definition-of-done items that are now true.
   - Keep the plan honest; do not pre-check future work.
   - Commit with specific file staging only. Never use `git add -A`.

```bash
git add <specific files>
git commit -m "feat(<slug>): <what this step does>"
```

7. After all implementation steps are complete, run the repo's final verification gates:

```bash
uv run ruff check .
uv run mypy .
uv run python -m pytest
```

8. If the change materially affects the browser UI, also run the relevant Playwright smoke or visual checks.
9. Confirm whether any acceptance criteria, test items, or definition-of-done items remain unchecked. If all planned work is complete, tell the user to run `$feature-ship`.
