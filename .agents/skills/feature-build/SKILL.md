---
name: feature-build
description: Use when the user wants to implement a planned feature in this repository from `plans/<slug>.md`, step by step, with targeted verification and incremental commits on a `codex/<slug>` branch.
---

# Feature Build

Implement an existing feature plan incrementally.

## Workflow

1. Establish context:

```bash
git branch --show-current
```

2. Require the current branch to be `codex/<slug>`. If it is `main` or does not start with `codex/`, stop and tell the user to switch branches or run `$feature-start`.
3. Derive `<slug>` from the branch name and read `plans/<slug>.md` in full before making changes.
4. Resume from the first unchecked implementation step. Do not redo completed steps.
5. For each remaining implementation step:
   - Implement the step.
   - Run targeted checks for the affected area. Prefer the smallest useful command, for example:

```bash
uv run python -m pytest tests/test_main_routes.py -q
uv run python -m pytest tests/test_openai_agent.py -q
uv run python -m pytest tests/test_html_formatter.py -q
uv run ruff check <touched paths>
```

   - Fix failures before moving on.
   - Mark the completed implementation step in `plans/<slug>.md`.
   - Check off any acceptance criteria that are now fully satisfied.
   - Commit with specific file staging only. Never use `git add -A`.

```bash
git add <specific files>
git commit -m "feat(<slug>): <what this step does>"
```

6. After all implementation steps are complete, run the full test suite:

```bash
uv run python -m pytest
```

7. Confirm whether any acceptance criteria remain unchecked. If all planned work is complete, tell the user to run `$feature-ship`.
