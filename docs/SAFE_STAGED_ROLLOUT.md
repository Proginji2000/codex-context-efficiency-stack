# Safe staged rollout

Use this mode when you have a sensitive or unfinished project whose current Codex behavior must not change yet.

## Why

Codex configuration is layered. A selected user profile can override the normal user config, while trusted-project `.codex/config.toml` files can override profile and user settings. Global `~/.codex/AGENTS.md` is still injected into every project, with repository-local AGENTS instructions layered after it.

Therefore, the safest migration path is to prepare the new stack without changing global instructions, default config, global hooks or existing role files.

## Stage 1 — prepare only

From this repository on Windows PowerShell:

```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$ProfileRoot = Join-Path $CodexHome 'profiles\context-efficiency'
$ProfileAgents = Join-Path $ProfileRoot 'agents'

New-Item -ItemType Directory -Force $ProfileAgents | Out-Null

Copy-Item '.\templates\agents\luna-low.toml'    (Join-Path $ProfileAgents 'luna-low.toml') -Force
Copy-Item '.\templates\agents\luna-medium.toml' (Join-Path $ProfileAgents 'luna-medium.toml') -Force
Copy-Item '.\templates\agents\luna-high.toml'   (Join-Path $ProfileAgents 'luna-high.toml') -Force
Copy-Item '.\templates\agents\sol-high.toml'    (Join-Path $ProfileAgents 'sol-high.toml') -Force
Copy-Item '.\templates\agents\astra-high.toml'  (Join-Path $ProfileAgents 'astra-high.toml') -Force

Copy-Item '.\templates\context-efficiency.config.toml' (Join-Path $CodexHome 'context-efficiency.config.toml') -Force
```

This deliberately does not write to `~/.codex/agents`, so existing project-specific or user-level role files cannot be overwritten by the staged setup.

At this stage, do **not** replace or merge into:

```text
~/.codex/config.toml
~/.codex/AGENTS.md
~/.codex/hooks.json
~/.codex/agents/*
```

Do not run RTK global initialization or change project-local `.codex/` files in the protected project yet.

The isolated role files are inert unless the profile is explicitly selected. The profile is opt-in and is used only when Codex is launched with:

```powershell
codex --profile context-efficiency
```

## Stage 2 — test away from the protected project

When quota/availability allows, test the profile in a disposable or low-risk repository first:

```powershell
cd C:\path\to\safe-test-repo
codex --profile context-efficiency
```

Check routing, tool-output behavior and verification before widening adoption.

## Stage 3 — protected project stays unchanged

Until its current milestone is completed, launch the protected project normally, without the profile:

```powershell
cd C:\path\to\protected-project
codex
```

Do not alter its existing `AGENTS.md`, `.codex/config.toml`, hooks, role configuration, branch/worktree strategy or task state as part of the general-stack migration.

Also avoid upgrading the Codex CLI solely for this migration while a sensitive milestone is unfinished. Record the current version first; upgrade after the milestone unless a separate bug/security reason requires it.

## Stage 4 — migrate after the milestone

Once the protected milestone is accepted, committed and pushed:

1. capture the accepted baseline commit;
2. record current project-specific Codex config and instructions;
3. create a dedicated migration branch/worktree;
4. decide which global/profile rules are still useful;
5. add project-level overrides where the project needs different concurrency, routing or model policy;
6. validate with representative tasks before making the new stack the normal path.

## Configuration precedence to remember

Highest to lowest, relevant local layers are:

```text
CLI flags / --config overrides
project .codex/config.toml
selected --profile
user ~/.codex/config.toml
managed/system defaults
```

AGENTS instructions are separate: global instructions are loaded first, then repository and deeper-directory instructions. This is why avoiding a global AGENTS replacement is important during a protected milestone.
