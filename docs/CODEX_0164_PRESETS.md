# Codex CLI 0.164.0: optional /presets workflow library

These are **templates for manual opt-in creation in the CLI TUI**. None are automatically installed and none modifies `~/.codex/config.toml`, project files or permission/model defaults.

Official release: https://github.com/openai/codex/releases/tag/rust-v0.164.0
Implementation: https://github.com/openai/codex/pull/54380 and https://github.com/openai/codex/pull/54381

## Supported surface and operation

- Codex **CLI TUI** 0.164.0 advertises ten numbered `/presets` slots (0-9); UI availability in Codex Desktop has **not** been verified.
- Open the CLI TUI with `codex`, then type `/presets`. Use the menu to create a preset from the composer text or edit a slot. The menu supports `0`-`9` for slots and `n`/`s`/`e`/`d` for new/settings/edit/delete as shown by the actual interface.
- Existing slots may contain private preferences. Inspect before replacing and do not overwrite any populated slot without explicit approval. Codex manages storage in the active user's `tui.presets`; do not copy global config from another machine.
- Presets are reusable prompts or slash commands, **not background automations**. Invoking one submits or queues an ordinary Codex input.
- `/model` and `/permissions` can accept inline parameters in 0.164.0, but these workflow templates deliberately **do not modify settings**. Permission escalation requires its ordinary approval handling. The active Codex app may use a distinct UI and permission surface.

## Suggested slots (only if free)

The following prompts assume the existing global AGENTS contract: **Luna parent orchestrates, all substantive repository work is delegated.** Copy the text of a chosen block into the CLI composer and save it through `/presets`.

### 0 — Resume safely

```text
Resume the current project. Luna remains orchestrator-only. Delegate one read-only Luna worker to reconcile live Git HEAD, branch, worktrees, uncommitted changes, existing state documents, relevant PRs and last verified tests. Preserve all unrelated changes; do not fetch, pull, reset or merge. Return a compact evidence-based checkpoint and the next concrete delegated task, with unknowns marked explicitly.
```

### 1 — PR readiness (read-only)

```text
Assess PR readiness without making changes. Luna delegates to a scoped read-only review worker: inspect the actual changed files, risks, unresolved review comments and CI results. Distinguish configured checks from executed checks; do not merge or modify branches. Return blockers, verification evidence and a concise go/no-go recommendation.
```

### 2 — Targeted verification

```text
Verify the current scoped change. Luna delegates relevant tests/build/type/lint/diff inspection to one worker, starting with targeted deterministic checks and expanding only as justified. Do not hide failures or claim unrun checks passed. Return exact commands, outcomes, regressions, and whether acceptance criteria are met.
```

### 3 — UI acceptance

```text
Luna delegates UI acceptance to ui-implementer (Terra Medium), which loads frontend-design when installed. For an authorized app, verify build and accessibility, then interaction/navigation using the tools actually available. Native IAB invisible navigation is not proof of a visible screenshot. Use a working Playwright MCP only where suitable and authorized. Report exactly what was or was not visually verified and preserve unrelated tabs/files.
```

### 4 — Project status

```text
Give a compact, evidence-based status of this project. Luna delegates one read-only worker to report current Git branch/HEAD/worktree, completed milestones, live blockers, pending PR/CI, test evidence and the next task. No unrelated searches, no mutations and no invented percentages or future work promises.
```

### 5 — Comparable A/B benchmark

```text
Prepare an A/B comparison for the same bounded task and environment. Luna delegates evidence collection to a worker. Record actual worker lanes, retries, first-pass correctness, elapsed seconds and available official usage figures. Do not estimate Codex subscription quota from API pricing, character count or guessed tokens. Do not deliberately exhaust thread slots or modify active projects.
```

Slots 6-9 are left intentionally free.

## Safe smoke test

1. Record `codex --version` and confirm CLI 0.164.0 or later with `/presets` available.
2. Save only **one** prompt to a genuinely empty slot and invoke it in a temporary clean test repo.
3. Check that Luna delegates to the expected worker and the prompt causes no unintended file or permission changes.
4. Re-open the menu and confirm the slot persists. Only after this, fill additional free slots.
5. If the menu is absent or differs in Codex Desktop, report the limitation; do not assume the CLI feature is available in Desktop.

## Privacy and measurements

Prompts contain no secrets or user-specific paths. Do not paste project logs, auth tokens, raw private code or session IDs into public templates. Record measured results using [the measurement guide](MEASUREMENT.md). The optional aggregation tool does not scrape account data or Codex conversation files.
