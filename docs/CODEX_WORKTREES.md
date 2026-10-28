# Git worktrees for parallel Codex workers — guarded local lifecycle

A Git worktree creates a separate working directory associated with the same repository, with its own checked-out branch and working tree. The parent Codex **Luna orchestrator remains non-writing**: assign different files/branches to different workers and preserve one writer per scope. Worktree isolation is not a mechanism to increase Codex concurrency limits or reclaim agent thread slots.

The optional `scripts/Manage-CodexWorktrees.py` uses Python 3.11+ and local Git. It never starts Codex, calls a model, fetches/pulls from a remote, changes global Codex config, edits the main worktree or installs dependencies.

## Preview first

From a repository (example):

```powershell
cd C:\Dev\codex-context-efficiency-stack
python .\scripts\Test-CodexWorktrees.py
python .\scripts\Manage-CodexWorktrees.py inventory
python .\scripts\Manage-CodexWorktrees.py create --name test-isolation
```

The `create` command above is **only a preview**. No branch or worktree is created.

Only an explicit `--apply` creates a new isolated branch named `codex/test-isolation` at the *primary worktree's current HEAD*, with a checkout stored in a dedicated sibling directory called `<primary-repo>-codex-worktrees/test-isolation`. This is not a fresh `git clone`; source code is shared through Git objects but the working copy is separate:

```powershell
python .\scripts\Manage-CodexWorktrees.py create --name test-isolation --apply
```

The tool refuses to reuse an existing branch or target path and never invokes `git worktree add --force` or `git branch -B`. If a repository is at a different commit than expected, review its HEAD before invoking `--apply`. The tool will not silently stash, commit, reset or migrate changes already in the main worktree. Ignore files and user modifications there remain untouched.

A worktree is a **filesystem location**; it does not run a worker. Start a distinct approved Codex CLI/Desktop session for each real task with the desired project directory, and ensure workers have **non-overlapping writer ownership**. Neither the script nor Git can prevent two agents from changing the same logical files across branches.

## Inventory

```powershell
python .\scripts\Manage-CodexWorktrees.py inventory
```

The default report omits full filesystem paths. Use `--include-paths` locally if needed, and review them before sharing. An inventory labels linked worktrees, locks, prunable/missing checkouts, dirty states (including ignored files), and whether conservative removal criteria currently pass. A reported eligible state is only a **snapshot**.

## Safe retirement — never automatic or forced

Once a dedicated worktree is no longer being used and its work has been **integrated via an actual Git branch ancestry relationship** to `refs/heads/main`, inspect:

```powershell
python .\scripts\Manage-CodexWorktrees.py remove --name test-isolation
```

This too is preview-only. To actually remove the linked checkout, the operator must type both flags:

```powershell
python .\scripts\Manage-CodexWorktrees.py remove --name test-isolation --apply --confirm-name test-isolation
```

The script refuses removal if **any** of these apply:

- The name/path was not created under the dedicated managed namespace, or the checked-out branch is not precisely `codex/<name>`.
- The target is the primary worktree, missing/prunable, symlinked, or locked.
- There are staged/unstaged changes, untracked files, **or even ignored files** (such as .env, caches, build artifacts, evidence).
- The dedicated branch is not an ancestor of the selected local base branch (default `refs/heads/main`), or that base branch is absent. A squash-merged or cherry-picked PR may fail this conservative ancestry test; handle that state manually after independently confirming retention of its commits.
- The command lacks `--apply` and the exact `--confirm-name` value.

Even when allowed, the tool calls only ordinary **non-forced** `git worktree remove`, and **retains the branch**. It never runs `git clean`, `git reset`, `git branch -D`, `git worktree prune`, or recursively deletes the checkout itself. Git's own safety checks remain authoritative. No unattended cleanup or automatic idle-worktree deletion is enabled.

The tool cannot reliably detect an agent still running or a process holding the checkout open. **Stop the worker and review the branch and files yourself before explicitly removing its workspace**. If a worktree is intentionally locked or represents an unmerged PR, retain it. Avoid trying `--force` manually unless you independently accept the risks.

For a repository whose protected integration branch is not `main`, set `--merged-into refs/heads/<branch>` to a verified local branch name. This checks only local ancestry; it never contacts GitHub to confirm a PR was merged.

## Verification without quota

```powershell
python .\scripts\Test-CodexWorktrees.py
```

The synthetic test creates temporary local Git repositories, exercises preview, explicit creation, dirty/untracked/ignored files, locks, unmerged commits, successful integrated cleanup, retained branches, unmanaged/detached worktrees, and then removes its **own temporary test directory**. It does not inspect existing real worktrees, run Codex or make network requests.

## Design boundaries

Worktree management is intentionally separate from Codex agent lifecycle and MCP profiles. The target directory is derived from the **primary** Git worktree and is never an arbitrary user-supplied deletion destination. This avoids mistakes with real worktrees from Polymarket or other projects. Initial rollout is opt-in; do not auto-create a worktree on every prompt or embed silent cleanup into global `AGENTS.md` until real-world behavior is validated.

Reference: [official Git worktree documentation](https://git-scm.com/docs/git-worktree) — particularly `--porcelain -z`, worktree locks, and non-forced removal.
