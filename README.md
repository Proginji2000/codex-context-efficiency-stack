# Codex Context-Efficiency Stack (Windows)

A practical Codex setup for reducing wasted context, avoiding unnecessary model escalation, and keeping verification deterministic.

This repository now has two complementary layers:

1. **Context efficiency** — RTK, concise `AGENTS.md`, `tool_output_token_limit`, Code Review Graph (CRG), targeted reads and bounded tool output.
2. **Model routing v2** — GPT-6 Luna workers by default, explicit Luna Low/Medium/High roles, and GPT-6 Sol High only for work that actually warrants escalation.

> Tested and refreshed for native Windows in September 2026. Codex configuration and third-party integrations can change; verify current upstream behavior before blindly copying old workarounds.

## Architecture

```text
USER REQUEST
    |
    v
PRIMARY CODEX THREAD
    |
    +-- bounded context / RTK / CRG / skills
    |
    +-- luna-low      tiny mechanical changes
    +-- luna-medium   normal development work
    +-- luna-high     complex but bounded reasoning
    `-- sol-high      architecture / security / migration / repeated failure
            |
            v
     IMPLEMENTATION
            |
            v
 DETERMINISTIC VERIFICATION
 tests / build / lint / typecheck / diff
            |
      +-----+-----+
      |           |
     PASS        FAIL
      |           |
  COMPLETE    retry / escalate
```

The central rule is:

> **If software can prove it, run the software. Use model judgment only for what remains uncertain.**

A compiler decides whether code compiles. The test runner decides whether tests pass. `git diff` decides what changed. Models interpret evidence, choose implementations and handle ambiguity.

---

# Quick start

## 1. Back up Codex configuration

Default Codex home on Windows:

```text
%USERPROFILE%\.codex
```

Before changing anything:

```powershell
$CodexHome = Join-Path $env:USERPROFILE '.codex'
Copy-Item "$CodexHome\config.toml" "$CodexHome\config.toml.backup" -ErrorAction SilentlyContinue
Copy-Item "$CodexHome\AGENTS.md" "$CodexHome\AGENTS.md.backup" -ErrorAction SilentlyContinue
Copy-Item "$CodexHome\hooks.json" "$CodexHome\hooks.json.backup" -ErrorAction SilentlyContinue
```

If `CODEX_HOME` is set, use that path instead.

## 2. Limit retained tool output

Add to `~/.codex/config.toml`:

```toml
tool_output_token_limit = 4000
```

This limits tool/function output retained in Codex context. It does not replace selective reading: when more detail is required, inspect a targeted range rather than dumping everything.

See [`templates/config.snippet.toml`](templates/config.snippet.toml).

## 3. Use the global AGENTS template

Use [`templates/AGENTS.md`](templates/AGENTS.md) as the basis for `~/.codex/AGENTS.md`.

It enforces:

- search before broad reads
- concise terminal output
- targeted tests during iteration
- deterministic completion checks
- targeted diffs
- no repeated unchanged reads
- bounded subagent context
- evidence-based Luna -> Sol escalation
- CRG-first navigation when a useful graph exists

Keep project-specific conventions in repository-level `AGENTS.md` files or skills rather than growing the global file indefinitely.

## 4. Install the optional Luna/Sol routing layer

Codex supports multi-agent role declarations and role-specific config layers. This repository provides:

```text
templates/agents/luna-low.toml
templates/agents/luna-medium.toml
templates/agents/luna-high.toml
templates/agents/sol-high.toml
```

Copy them to:

```text
~/.codex/agents/
```

Then merge:

```text
templates/config.routing.snippet.toml
```

into:

```text
~/.codex/config.toml
```

The recommended defaults are:

```text
spawned worker default -> GPT-6 Luna / medium
small work             -> Luna / low
hard bounded work      -> Luna / high
architecture/security/
migration/repeated fail -> Sol / high
```

Restart Codex after editing configuration.

Full routing policy: [`docs/MODEL_ROUTING_V2.md`](docs/MODEL_ROUTING_V2.md).

### Important limitation

`AGENTS.md` can tell Codex *when* a lane should be used, but it does not magically mutate the model of an already-running primary turn.

The provided custom roles make spawned-agent model selection explicit. If the current runtime does not have those roles loaded, the agent should continue with the active model rather than pretending a switch occurred.

A fully external router that changes the primary session model dynamically is a separate orchestration layer, for example via the Agents API.

---

# Context layer

## RTK

RTK compresses common shell-command output before it reaches model context.

Upstream: <https://github.com/rtk-ai/rtk>

After installing the binary:

```powershell
rtk init -g --codex
rtk --version
rtk gain
```

On native Windows, do not assume every command is transparently rewritten. The Codex integration is instruction-driven, so the agent should explicitly prefer RTK-supported commands where they preserve required evidence.

## Code Review Graph

CRG builds a local structural graph of the repository and exposes code relationships through MCP.

Upstream: <https://github.com/tirth8205/code-review-graph>

Install:

```powershell
python.exe -m pip install -U "code-review-graph[communities,enrichment]"
code-review-graph install --platform codex
```

For each repository:

```powershell
cd C:\path\to\repo
code-review-graph build
code-review-graph status
code-review-graph register C:\path\to\repo --alias repo-name
```

After the first full build, prefer:

```powershell
code-review-graph update
```

Use CRG to narrow the search, then verify important conclusions in real source and tests. Source remains authoritative if the graph is stale or incomplete.

### Windows PATH caveat

If `code-review-graph` is installed but not found:

```powershell
$Scripts = python.exe -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))"
Get-ChildItem "$Scripts" -Filter "code-review-graph*"
& "$Scripts\code-review-graph.exe" --help
```

If necessary, point the MCP configuration directly to the absolute executable path.

See [`docs/WINDOWS_TROUBLESHOOTING.md`](docs/WINDOWS_TROUBLESHOOTING.md).

### Windows hooks caveat

Some CRG versions have generated Unix-style hook commands on Windows. Inspect `~/.codex/hooks.json` before trusting generated hooks. A sanitized Windows example is available at [`templates/hooks.windows.json`](templates/hooks.windows.json).

---

# Progressive disclosure instead of giant prompts

Do not turn `AGENTS.md` into a project encyclopedia.

Prefer:

```text
AGENTS.md
  -> short global/repository rules
  -> conditional pointers

.agents/skills/
  -> detailed reusable workflows
  -> scripts
  -> references
```

A good repository instruction says *when* to load documentation rather than forcing every task to read everything.

Example:

```text
Use architecture.md for service-boundary changes.
Use database.md for schema or migration changes.
Use deployment.md only when preparing a deployment.
```

This keeps typo fixes and small code changes from paying the context cost of unrelated architecture, database and deployment documentation.

---

# Routing policy

Use the lowest sufficient lane.

| Work | Preferred lane |
| --- | --- |
| docs, typo, obvious rename, simple config | Luna Low |
| normal feature, tests, localized bug, ordinary SQL | Luna Medium |
| complex bounded debugging, subtle state logic, non-trivial refactor | Luna High |
| architecture, auth/security, risky migration, repeated Luna failure | Sol High |

Do not call an AI judge after every tiny action. Route at meaningful boundaries only.

A practical escalation sequence is:

```text
Luna Medium
 -> verify
 -> localized failure: retry once
 -> verify
 -> still difficult: Luna High
 -> verify
 -> unresolved/high-risk: Sol High
```

Jev or another external decision model is **optional**, not part of the required stack. Typed output and confidence scores are useful control signals, but they are not proof of correctness.

---

# Completion gate

Before declaring a task complete, apply the checks that are relevant to the repository:

```text
requested behavior implemented
+ relevant tests pass
+ build/type/lint checks pass where applicable
+ final diff matches requested scope
+ no unresolved failure is hidden
= completion
```

Do not invent a heavyweight full-suite requirement for a trivial change if the repository does not normally require it. Conversely, do not skip required validation merely to save quota.

---

# Git hygiene

CRG and agents become noisier when repositories track generated/runtime content.

Typical exclusions include:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
node_modules/
.code-review-graph/
logs/
*.log
build/
dist/
coverage/
.cache/
.env
.env.*
!.env.example
*.secret
*.pem
```

Adapt this to the repository. Do not ignore source-controlled fixtures merely because they live in a directory named `data/`.

See [`templates/gitignore.example`](templates/gitignore.example).

---

# Existing sessions

After changing global instructions, an already-running session can be told once to re-read them:

```text
Re-read the global Codex instructions in ~/.codex/AGENTS.md and the RTK.md file they reference. Apply their current version to this session and all following steps.
```

Configuration-level features such as newly added MCP servers or custom agent roles may still require a Codex restart/new runtime.

See [`docs/EXISTING_SESSIONS.md`](docs/EXISTING_SESSIONS.md).

---

# Measure instead of assuming

Track actual behavior:

```powershell
rtk gain
code-review-graph status
code-review-graph detect-changes --brief
```

For routing, track:

- tasks per lane
- successful completions per lane
- retries
- escalations
- failed verification passes
- context/quota usage where visible
- wall-clock latency

The useful metric is **successful engineering work per unit of quota/cost**, not raw token volume alone.

See [`docs/MEASUREMENT.md`](docs/MEASUREMENT.md).

---

# Quick verification

The repository includes a read-only PowerShell checker:

```powershell
.\scripts\verify-stack.ps1
```

It checks the original context-efficiency layer: Codex home/config, global AGENTS, RTK, `tool_output_token_limit`, CRG executable/MCP configuration, hooks and registered repositories.

The v2 role configs are intentionally simple enough to inspect directly.

---

# Recommended stack

```text
Codex primary thread
        +
GPT-6 Luna spawned workers by default
        +
Luna Low / Medium / High explicit roles
        +
Sol High only on real escalation conditions
        +
RTK
        +
concise AGENTS.md
        +
repository skills / progressive disclosure
        +
tool_output_token_limit = 4000
        +
Code Review Graph where useful
        +
clean Git tracking
        +
deterministic tests/build/lint/typecheck/diff
```

Then stop adding layers until measurement shows a real bottleneck.

---

# Sources and security

Primary references are collected in [`SOURCES.md`](SOURCES.md).

Before publishing local configuration, remove usernames, absolute personal paths, private repository names, secrets, tokens, browser-profile paths, database paths and raw CRG exports containing private structural metadata.

See [`SECURITY.md`](SECURITY.md).
