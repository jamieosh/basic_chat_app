---
name: feature-ship
description: Use when the user wants to finish a completed feature branch in this repository by updating docs, changelog, backlog status, running full verification, merging the feature into `main`, pushing the result, and cleaning up the feature branch locally and remotely.
---

# Feature Ship

Ship a completed feature branch by merging it into `main` and cleaning up afterward.

## Workflow

1. Establish context:

```bash
git branch --show-current
```

2. Require the current branch to be `codex/<slug>`. If it is `main` or does not start with `codex/`, stop and report that the feature branch is required.
3. Read `plans/<slug>.md` and verify:
   - All implementation steps are checked off
   - All acceptance criteria are checked off
   - The feature is actually complete
   If any of these fail, stop.
4. Inspect `git status --short`.
5. Update `CHANGELOG.md` in the repository's existing format:
   - Reuse the current top-level `## YYYY-MM-DD` heading if it already matches today's date.
   - Otherwise add a new top-level date heading at the top.
   - Add a `### <Feature title>` subsection summarizing the shipped behavior in human-readable terms.
   - Mention the most significant files or commands changed.
   - Include test results if they are available from the verification run.
6. Update `plans/PHASE 1 BACKLOG.md` to reflect that the item shipped:
   - Prefer moving the completed item into a `## Completed` section at the bottom.
   - If creating that section would be too disruptive, clearly mark the backlog item as completed with today's date.
7. Update `README.md` if the feature changes user-visible behavior, setup, configuration, or contributor workflow.
8. Delete `plans/<slug>.md` once the feature plan is fully complete so the merge removes the finished plan file from the repository.
9. Run the final gates:

```bash
uv run ruff check .
uv run mypy .
uv run python -m pytest
```

10. If there are uncommitted changes, stage specific files only and create a final conventional commit:

```bash
git add <specific files>
git commit -m "feat(<slug>): finalize feature ship"
```

11. Determine the integration remote:
   - If a `fork` remote exists, push there.
   - Otherwise use `origin` and explicitly note that no dedicated fork remote exists.
12. Push the feature branch before merging so the remote has the final branch state:

```bash
git push -u <remote> codex/<slug>
```

13. Merge the feature into `main` locally:

```bash
git switch main
git pull --ff-only <remote> main
git merge --no-ff codex/<slug> -m "merge: codex/<slug>"
git push <remote> main
```

If the merge or push fails, stop and report the failure. Do not force anything.

14. Clean up the feature branch after `main` is pushed successfully:

```bash
git branch -d codex/<slug>
git push <remote> --delete codex/<slug>
```

15. Print:

```bash
git status --short --branch
git log --oneline -5
```

16. Report success, the remote used, and that the feature was merged to `main` and cleaned up.
