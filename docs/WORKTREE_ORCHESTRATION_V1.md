# Worktree delegation V1 — optional Luna workflow

This is a **staged, opt-in** workflow for the existing orchestrator-only Luna setup. It does **not** change `~/.codex/AGENTS.md`, installed roles, MCP settings, Codex runtime permissions or the experimental global-instruction PR #14.

The local cycle has already been validated on Windows: `audit-1` was created and then removed from the repository using `scripts/Manage-CodexWorktrees.py`; `main` remained, and the `codex/audit-1` branch was preserved. That proves single-worktree provisioning/retirement, **not** end-to-end multi-agent dispatch.

## Why a separate planner?

The existing manager controls one worktree at a time. A two-writer wave additionally needs to reject overlapping file ownership before either workspace is created. `scripts/Plan-CodexWorktreeWave.py` enforces that up front.

The manifest is a local JSON file supplied explicitly by the operator or a trusted provisioning worker. Example (`wave.json` in a safe local path):

```json
{
  "version": 1,
  "workers": [
    {
      "name": "api-task",
      "lane": "luna-medium",
      "goal": "Implement an isolated backend change",
      "write_scopes": ["src/backend"]
    },
    {
      "name": "ui-task",
      "lane": "ui-implementer",
      "goal": "Implement the independent UI",
      "write_scopes": ["src/frontend"]
    }
  ]
}
```

`write_scopes` are exclusive **relative repository paths**. Exact, parent/child and case-insensitive overlaps are rejected. Absolute paths, drive paths, `..`, and `.git`/`.codex` scopes are refused. The manifest is **a planning record, not a technical filesystem sandbox**; workers must honor ownership. Do not put secrets, customer data or confidential code in `goal`, and do not commit live task manifests inadvertently.

The currently configured two-thread conservative cap means at most two writers per wave. For read-only reviewers, a shared checkout is usually sufficient; worktrees are for independent concurrent **writers**.

## Simulate before provisioning

```powershell
cd C:\Dev\codex-context-efficiency-stack
python .\scripts\Test-CodexWorktreeWave.py
python .\scripts\Plan-CodexWorktreeWave.py --repo C:\Dev\codex-context-efficiency-stack --manifest C:\Temp\wave.json
```

This validates all writers, previews the creation of **every** worktree through the existing guarded manager and prints only names, lane and owned path counts. It does not start Codex, create branches, launch MCP servers or consume model quota.

Only after validating the planned ownership and Git preflight, explicitly request:

```powershell
python .\scripts\Plan-CodexWorktreeWave.py --repo C:\Dev\codex-context-efficiency-stack --manifest C:\Temp\wave.json --apply
```

This creates Git worktrees and branches through `Manage-CodexWorktrees.py`, without `--force`, reset, branch reuse, fetching or other Git/network changes. An error after a partial creation **preserves** successful worktrees; inspect with `Manage-CodexWorktrees.py inventory` and recover intentionally. No automatic rollback or deletion.

## Luna delegation protocol

Luna must act **only as orchestrator**. At a meaningful task boundary:

1. Delegate repository reconnaissance to a read-only worker. Determine whether workstreams are genuinely independent and identify exact write scopes and verification requirements.
2. If parallel writers are useful, delegate worktree wave planning/provisioning to one suitable worker. The parent must not implement or run tests itself. Require a preview report, then approve `--apply` only for that wave.
3. Confirm from Git that the worktrees and isolated branches exist before assigning bounded worker tasks; include the worktree directory, goal, allowed paths, acceptance tests and explicit no-overlap rule in each assignment.
4. Collect worker terminal evidence (changed files, tests, commit/head, failures). Do not claim that a worktree was created or an agent launched without observed evidence. Avoid starting a third writer when the concurrency cap is saturated.
5. Independently verify integration/review via delegated tests. Preserve every worktree until the relevant work is actually integrated and no active worker owns it.
6. **Cleanup is a separate operator-approved action**, using the existing manager's clean/ignored/locked/ancestry gates, `remove --apply --confirm-name`. No automatic worktree deletion, branch deletion, `--force`, Git reset or PR merge.

The script never spawns agents. Codex must expose delegation tools in the active session for the worker phase. The planner cannot itself prove effective sandbox boundaries, agent thread-slot release or runtime tool availability.

### Optional handoff prompt for a fresh Codex session

> You are Luna Medium, exclusively orchestrator. Delegate one read-only worker to inventory the current Git state and determine whether two genuinely independent writer tasks need separate worktrees. Use `docs/WORKTREE_ORCHESTRATION_V1.md` and the repository's `Plan-CodexWorktreeWave.py` as the bounded provisioning procedure. Do not change global Codex config, do not create worktrees before a safe preview, and never delete them without separate explicit authorization. Assign each writer a nonoverlapping directory scope, collect test evidence, and report actual worker identities and results.

For real work use a *specific* engineering task, not an empty wave. Do not burn Codex quota on a purposeless demonstration when quota is low.

## Acceptance and limits

GitHub Windows CI tests the planner with **temporary local repositories**: simulated dry-run, two separate worktrees, exact/nested/case-insensitive collisions, traversal rejection, no branch reuse and preservation of created branches. No Codex model calls are made.

A real two-worker Codex trial, a branch integration test and runtime agent orchestration have **not** been completed. Keep this experimental workflow separate from the installed global contract and PR #14 until an appropriate low-risk trial confirms the interaction. The established single-worktree manager is described in [CODEX_WORKTREES.md](CODEX_WORKTREES.md).
