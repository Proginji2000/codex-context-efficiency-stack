# Claude Pro context-efficiency stack

This is the Claude Code counterpart of the repository's Codex context-efficiency stack. It targets subscription efficiency first: Sonnet does normal work, Haiku absorbs cheap exploration, and Opus is an evidence-based escalation lane. Fable is deliberately not part of automatic routing.

The configuration was written against Claude Code documentation current on 29 September 2026. It uses model-family aliases so later supported Sonnet, Opus, and Haiku releases can be adopted without rewriting every agent definition.

## Architecture

```text
REQUEST
  |
  v
MAIN CLAUDE CODE SESSION
Sonnet / normal daily work
  |
  +-- Explore / Haiku       repository discovery, read-focused search
  +-- haiku-low             tiny mechanical low-risk work
  +-- sonnet-medium         normal implementation
  +-- sonnet-high           complex bounded debugging/refactor
  +-- opus-high             architecture/security/migration/escalation
  `-- opus-xhigh            final subscription-safe escalation
          |
          v
DETERMINISTIC VERIFICATION
build / tests / types / lint / formatter / git diff
```

Central rule: if software can prove the result, run that software. Do not spend another model call on facts a compiler, test runner, type checker, linter, or Git can establish.

## Why these defaults

`claude/settings.json` starts sessions on `sonnet`, keeps Ultracode off, caps Agent-tool concurrency at two, and sets subagent spawn depth to one. Spawn depth one means top-level subagents cannot create another layer. This is intentionally conservative for Claude Pro quota.

Claude Code's built-in Explore agent normally inherits the main session model in current releases. The supplied user agent named `Explore` overrides it and pins exploration to Haiku, while denying write/edit and further Agent spawning.

Haiku does not currently expose the same configurable effort ladder as current Sonnet/Opus models, so the Haiku agents intentionally omit `effort`. Sonnet and Opus workers use explicit `medium`, `high`, or `xhigh` effort.

Fable is not technically blocked: the user can still choose it manually. The global instruction only prevents the stack from selecting `fable` or `best` autonomously, because Fable can draw on usage credits depending on plan/account state.

## Windows install

From the repository root:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\install-claude-pro-stack.ps1
pwsh -ExecutionPolicy Bypass -File .\scripts\verify-claude-pro-stack.ps1
```

The installer:

1. creates timestamped backups below `~/.claude/backups/`;
2. initializes RTK when it is already installed;
3. preserves the existing global `CLAUDE.md` and adds one import line instead of replacing it;
4. merges the quota-safe keys into the existing `settings.json` instead of replacing unrelated settings;
5. installs the six user-level agents under `~/.claude/agents/`.

If the agents directory did not exist when Claude Code was launched, restart Claude Code after installation so it discovers the new directory.

### Install missing dependencies too

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\install-claude-pro-stack.ps1 -InstallDependencies
```

The script uses `winget` for RTK when available. It does not install Code Review Graph globally unless `-ConfigureCurrentRepository` is also supplied because CRG configuration is repository-specific.

### Configure CRG for the current repository

Run the installer while your shell is located in the target code repository:

```powershell
pwsh C:\path\to\codex-context-efficiency-stack\scripts\install-claude-pro-stack.ps1 -InstallDependencies -ConfigureCurrentRepository
```

Equivalent manual CRG setup:

```powershell
python -m pip install -U "code-review-graph[communities,enrichment]"
code-review-graph install --platform claude-code
code-review-graph build
code-review-graph status
```

CRG narrows the code scope; it does not replace source inspection. When graph and source disagree, source wins.

## RTK

RTK has a native Claude Code integration. When installed, the stack runs:

```powershell
rtk init -g --auto-patch
```

RTK registers its Claude hook and keeps its own compact `RTK.md` instructions. Check it with:

```powershell
rtk --version
rtk gain
```

If hook prerequisites are missing on Windows, RTK should fail visibly or remain inactive; do not assume command rewriting is occurring merely because the binary exists.

## Routing policy

| Work | Lane |
| --- | --- |
| Repository lookup, symbol discovery, read-only exploration | Explore / Haiku |
| Docs, obvious rename, tiny config or mechanical change | haiku-low |
| Normal feature, tests, localized bug, ordinary SQL, clear multi-file change | sonnet-medium |
| Complex bounded debugging, subtle state logic, non-trivial refactor | sonnet-high |
| Architecture, security, risky migration, broad invariants, repeated Sonnet failure | opus-high |
| Exceptional unresolved end-to-end problem | opus-xhigh |

Do not spawn a subagent for simple sequential work. The context isolation is valuable when exploration is verbose or a workstream is independent; otherwise the main session is cheaper and faster.

Suggested escalation:

```text
Sonnet main / sonnet-medium
 -> deterministic verification
 -> localized failure: retry once
 -> sonnet-high
 -> deterministic verification
 -> unresolved high-risk uncertainty: opus-high
 -> final exceptional case: opus-xhigh
```

## Files installed

```text
~/.claude/
├── CLAUDE.md                         existing file preserved + one import
├── CLAUDE_CONTEXT_EFFICIENCY.md      stack rules
├── settings.json                     merged, not wholesale replaced
└── agents/
    ├── Explore.md
    ├── haiku-low.md
    ├── sonnet-medium.md
    ├── sonnet-high.md
    ├── opus-high.md
    └── opus-xhigh.md
```

## Verification

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\verify-claude-pro-stack.ps1
```

Then inside Claude Code check:

```text
/status
/context
/tasks
```

For recent Claude Code versions, `/doctor prompt-audit` can audit instruction files and agent configuration for stale or conflicting guidance.

## Reverting

The installer prints a backup directory such as:

```text
~/.claude/backups/context-efficiency-20260929-153000/
```

Restore `settings.json`, `CLAUDE.md`, or individual agent files from that directory. Files that did not exist before the installation have no backup copy and can simply be removed.

RTK and CRG have their own installation state; restoring the Claude files does not uninstall those tools.

## Measurements that matter

Track completed software work per unit of subscription quota, not raw token counts alone. Useful signals are tasks by lane, retries, escalations, verification failures, RTK savings, subagent count, context compactions, elapsed latency, and how often Opus was actually needed.

Do not add more orchestration layers until those measurements show a real bottleneck.
