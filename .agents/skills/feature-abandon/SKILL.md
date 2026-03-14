---
name: feature-abandon
description: Use when the user wants to safely abandon a `codex/<slug>` feature branch in this repository, after reviewing unmerged commits, uncommitted changes, the optional remote branch, and the optional plan file.
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
3. Show the user:
   - The branch name
   - The unmerged commits
   - Any uncommitted changes
4. Ask for explicit confirmation with a clear warning that local unmerged work and uncommitted changes can be lost. Do not proceed unless the user clearly confirms.
5. Delete the local branch:

```bash
git switch main
git pull --ff-only
git branch -D codex/<slug>
```

6. Ask whether to delete the remote branch too:
   - Prefer `fork` if that remote exists
   - Otherwise offer `origin`
7. If the user agrees, delete the remote branch:

```bash
git push <remote> --delete codex/<slug>
```

8. If `plans/<slug>.md` exists, ask whether to delete it.
9. Report final status:

```bash
git status --short --branch
```
