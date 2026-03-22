---
name: feature-abandon
description: Use when the user wants to safely abandon a `codex/<slug>` branch in this repository after reviewing unmerged commits, uncommitted changes, any matching remote branch, and the optional `plans/<slug>.md` file.
---

# Feature Abandon

Safely abandon an in-progress feature branch only after explicit confirmation.

## Workflow

1. Establish context:

```bash
git branch --show-current
git log main..HEAD --oneline
git status --short
```

2. Require the current branch to be `codex/<slug>`. If it is `main` or does not start with `codex/`, stop and report that there is no active feature branch to abandon.
3. Check whether `plans/<slug>.md` exists and whether a same-name remote branch exists on `fork` or `origin`.
4. Show the user:
   - The branch name
   - The unmerged commits
   - Any uncommitted changes
   - Whether `plans/<slug>.md` exists
   - Whether a remote branch exists
5. Ask for explicit confirmation with a clear warning that local unmerged work and uncommitted changes can be lost. Do not proceed unless the user clearly confirms.
6. If uncommitted changes are present, warn that `git switch main` may fail and do not auto-stash, reset, or discard anything.
7. Delete the local branch only after switching away cleanly:

```bash
git switch main
git pull --ff-only
git branch -D codex/<slug>
```

8. Ask whether to delete the remote branch too:
   - Prefer `fork` if that remote exists
   - Otherwise offer `origin`
9. If the user agrees, delete the remote branch:

```bash
git push <remote> --delete codex/<slug>
```

10. If `plans/<slug>.md` exists, ask whether to delete it. Do not modify backlog or done files unless the user explicitly asks.
11. Report final status:

```bash
git status --short --branch
```
