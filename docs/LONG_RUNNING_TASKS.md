# Long-running Codex tasks

For long, interruption-prone, multi-milestone, or multi-agent work, keep the task's essential state outside the conversation so context compaction or a fresh session does not require replaying the full chat.

OpenAI's long-horizon Codex guidance emphasizes durable project memory: specs, plans, constraints, status, repository state, worktrees, and verification outputs give the agent externalized state it can revisit.

## When to use durable task state

Use it when one or more are true:

- the task spans several milestones
- the task may continue in another Codex session
- context compaction is likely
- several agents or worktrees are involved
- important architectural or behavioral decisions must survive a handoff
- verification requires multiple independent checkpoints

Do not create it for typo fixes, tiny refactors, or short self-contained changes.

## Recommended file

Start from:

```text
templates/TASK_STATE.md
```

For private/local state, a project-local path such as `.codex/TASK_STATE.md` is convenient. If the status is useful to collaborators and intentionally versioned, use a repository document such as `docs/CODEX_STATUS.md` instead.

Do not put secrets, tokens, credentials, private environment values, or large raw logs in the state file.

## Update policy

Update state only when information materially changes:

- a milestone completes
- a significant decision is made
- a new failure changes the plan
- work moves to another agent/session/worktree
- verification establishes a new fact

Do not rewrite it after every shell command. The file should remain a small resume index, not a transcript.

## What to preserve

Preserve:

- goal and definition of done
- hard constraints and explicit out-of-scope items
- current milestone
- important decisions and why they were made
- relevant files and symbols
- latest deterministic verification evidence
- unresolved issues and risks
- the next concrete action

Do not preserve long prose, repeated diagnostics, complete diffs, or raw logs when Git and files already contain the authoritative evidence.

## Worktrees

Use separate Git worktrees when independent Codex runs need to modify the same repository concurrently. This isolates working trees, keeps diffs reviewable, and reduces cross-task thrash.

Avoid parallel agents modifying the same files unless there is an explicit coordination plan. Short dependent steps are usually better kept in the primary thread.

## Resume pattern

A fresh Codex session should be able to start from a compact request such as:

```text
Resume this task from .codex/TASK_STATE.md.
Verify the recorded state against Git and the relevant source/tests before changing code.
Continue from Next action until the definition of done is satisfied.
```

The state file is a navigation aid. Source code, tests, build output, and Git are still authoritative.

## Measure whether it helps

For long tasks, track whether a fresh session can resume correctly from the state file without reloading the old conversation. Useful signals include:

- resume succeeds without re-exploration
- number of files re-read after resume
- repeated decisions avoided
- verification evidence preserved correctly
- no stale state causing incorrect work

If maintaining the state file costs more than it saves for a class of tasks, narrow the trigger conditions instead of making it mandatory everywhere.
