---
name: feature-ship
description: Use when the user wants to finish a completed `codex/<slug>` feature branch by updating project docs and backlog records, running full verification, merging to `main`, pushing, and cleaning up the branch safely.
---

# Feature Ship

Ship a completed feature branch by merging it into `main` and cleaning up afterward.

## Workflow

1. Establish context:

```bash
git branch --show-current
git status --short
```

2. Require the current branch to be `codex/<slug>`. If it is `main` or does not start with `codex/`, stop and report that the feature branch is required.
3. Read `AGENTS.md` and `plans/<slug>.md` and verify:
   - All implementation steps are checked off
   - All acceptance criteria are checked off
   - The feature is actually complete
   If any of these fail, stop.
4. Determine the documentation targets before editing:
   - `CHANGELOG.md`
   - the matching active backlog file such as `plans/PHASE 3 BACKLOG.md`
   - the matching shipped-items file such as `plans/done/PHASE 3 DONE.md`
   - `README.md` and `AGENTS.md` when contributor-facing behavior or architecture changed
5. If any of those target files already contain unrelated user edits, stop rather than risking a bad merge of planning or changelog content.
6. Update `CHANGELOG.md` in the repository's existing format:
   - Reuse the current top-level `## YYYY-MM-DD` heading if it already matches today's date.
   - Otherwise add a new top-level date heading at the top.
   - Add a `### <Feature title>` subsection summarizing the shipped behavior in human-readable terms.
   - Mention the most significant files or commands changed.
   - Include test results if they are available from the verification run.
7. Move the shipped item from the active phase backlog into the matching `plans/done/` file.
   - Preserve the existing backlog and done-file style.
   - Do not delete or rewrite unrelated backlog items.
8. Update `README.md` if the feature changes user-visible behavior, setup, configuration, or extension guidance.
9. Update `AGENTS.md` if the feature changes architecture notes, current capability claims, or contributor guidance.
10. Delete `plans/<slug>.md` only after the shipped state is reflected in changelog and planning docs.
11. Run the final gates:

```bash
uv run ruff check .
uv run mypy .
uv run python -m pytest
```

12. If the shipped change materially affects the browser UI, also run the relevant Playwright smoke or visual checks before merging.
13. If there are uncommitted changes, stage specific files only and create a final conventional commit:

```bash
git add <specific files>
git commit -m "feat(<slug>): finalize feature ship"
```

14. Determine the integration remote:
   - If a `fork` remote exists, push there.
   - Otherwise use `origin` and explicitly note that no dedicated fork remote exists.
15. Push the feature branch before merging so the remote has the final branch state:

```bash
git push -u <remote> codex/<slug>
```

16. Merge the feature into `main` locally:

```bash
git switch main
git pull --ff-only <remote> main
git merge --no-ff codex/<slug> -m "merge: codex/<slug>"
git push <remote> main
```

If the merge or push fails, stop and report the failure. Do not force anything.

17. Clean up the feature branch after `main` is pushed successfully:

```bash
git branch -d codex/<slug>
git push <remote> --delete codex/<slug>
```

18. Print:

```bash
git status --short --branch
git log --oneline -5
```

19. Report success, the remote used, verification performed, and that the feature was merged to `main` and cleaned up.
