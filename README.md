# Codex Context-Efficiency Stack (Windows)

A quality-preserving setup for reducing unnecessary context and tool-output tokens in OpenAI Codex **without lowering the model or reasoning level**.

> Tested on native Windows in September 2026. Some third-party integrations, especially Windows hooks, can change over time. Re-check upstream release notes before blindly copying a workaround.

## Goals

This stack is designed to reduce waste around a strong reasoning model, not to make the model "think less".

It targets four different sources of context bloat:

1. **Shell output** → RTK (Rust Token Killer)
2. **Agent behavior** → concise global `AGENTS.md`
3. **Tool/function output retained by Codex** → `tool_output_token_limit`
4. **Large-codebase exploration** → Code Review Graph (CRG) via MCP

The result is a layered setup:

```text
Preferred Codex model + preferred reasoning effort
                    │
        ┌───────────┼───────────┐
        │           │           │
      AGENTS       RTK         CRG
        │           │           │
 behavior rules  shell output  structural code map
        │           │           │
        └───────────┼───────────┘
                    │
        tool_output_token_limit
                    │
                    ▼
            cleaner model context
```

## What this does *not* do

- It does **not** switch you to a cheaper/smaller model.
- It does **not** reduce reasoning effort.
- It does **not** promise a fixed percentage reduction in total Codex quota usage.
- It does **not** replace tests, source verification, or proper code review.

RTK savings apply to the shell output it filters. CRG savings apply to codebase exploration/review context. The total effect depends on workload.

---

# 1. Back up Codex configuration

On Windows, the default Codex home is:

```text
%USERPROFILE%\.codex
```

Back up the important files before changing integrations:

```powershell
$CodexHome = Join-Path $env:USERPROFILE '.codex'

Copy-Item "$CodexHome\config.toml" "$CodexHome\config.toml.backup" -ErrorAction SilentlyContinue
Copy-Item "$CodexHome\AGENTS.md" "$CodexHome\AGENTS.md.backup" -ErrorAction SilentlyContinue
Copy-Item "$CodexHome\hooks.json" "$CodexHome\hooks.json.backup" -ErrorAction SilentlyContinue
```

If `CODEX_HOME` is set, use that path instead.

---

# 2. Add a native Codex tool-output budget

Add this near the top of `~/.codex/config.toml`:

```toml
tool_output_token_limit = 4000
```

Codex defines this as the token budget applied when storing tool/function outputs in its context manager.

`4000` is a conservative starting point: small enough to prevent giant outputs from dominating context, but large enough to preserve useful diagnostics. If more data is needed, inspect another targeted range instead of dumping everything at once.

This is intentionally different from a behavioral **byte** limit in `AGENTS.md`.

- `AGENTS.md`: roughly 4 KB initial output for unknown/unoptimized commands.
- `tool_output_token_limit`: 4,000 **tokens** retained per tool output.

See [`templates/config.snippet.toml`](templates/config.snippet.toml).

---

# 3. Install RTK for Codex

RTK is a CLI proxy that compresses common shell-command output before it enters the model context.

Upstream: <https://github.com/rtk-ai/rtk>

After installing the RTK binary, initialize its Codex integration:

```powershell
rtk init -g --codex
```

For Codex, RTK uses prompt-level guidance rather than a transparent native-Windows shell rewrite. It installs/uses:

```text
~/.codex/RTK.md
~/.codex/AGENTS.md  -> @RTK.md
```

Verify:

```powershell
rtk --version
rtk gain
```

`rtk gain` is useful after real development sessions to see how many shell-output tokens RTK actually removed.

### Native Windows caveat

Do not assume every shell command is transparently rewritten on native Windows. The Codex integration is instruction-based, so the agent should explicitly prefer commands such as:

```text
rtk git status
rtk git diff
rtk pytest -q
rtk rg ...
```

The global `AGENTS.md` template in this repository reinforces that behavior.

---

# 4. Use a concise global AGENTS.md

Codex reads global instructions from `~/.codex/AGENTS.md` (unless a global `AGENTS.override.md` exists), then layers project instructions on top.

The goal is to encode reusable context discipline once instead of repeating it in every prompt.

Copy or adapt:

- [`templates/AGENTS.md`](templates/AGENTS.md)

The template covers:

- RTK-first terminal usage
- quiet/concise output
- search before reading
- bounded source reads
- targeted tests during iteration
- broader validation only at meaningful checkpoints
- targeted diffs
- avoiding repeated unchanged reads/output
- context compaction discipline
- hard limits for unknown output
- CRG-first code navigation when an index exists

Keep global instructions concise. Put project-specific commands and conventions in repository-level `AGENTS.md` files instead.

---

# 5. Install Code Review Graph (CRG)

CRG builds a local structural knowledge graph of a repository with Tree-sitter, stores it locally in SQLite, and exposes graph queries through MCP.

Upstream: <https://github.com/tirth8205/code-review-graph>

Install the core package plus the two optional groups used in this stack:

```powershell
python.exe -m pip install -U "code-review-graph[communities,enrichment]"
```

This adds:

- `igraph` → Leiden community detection
- `Jedi` → additional Python call-resolution enrichment

Then install the Codex integration:

```powershell
code-review-graph install --platform codex
```

CRG may add:

- an MCP entry to `~/.codex/config.toml`
- Codex hooks
- CRG guidance/instructions

**Always inspect the resulting files after installation** so the installer does not leave redundant or misplaced instructions.

---

# 6. Windows: Python Store / PATH issue

A common Windows symptom is:

```text
code-review-graph : The term 'code-review-graph' is not recognized...
```

while this works:

```powershell
python.exe -m pip show code-review-graph
```

For a Microsoft Store Python install, find the user Scripts directory with:

```powershell
$Scripts = python.exe -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))"
$Scripts
Get-ChildItem "$Scripts" -Filter "code-review-graph*"
```

Test the executable directly:

```powershell
& "$Scripts\code-review-graph.exe" --help
```

Add that Scripts directory to the user PATH:

```powershell
$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')

if (($UserPath -split ';') -notcontains $Scripts) {
    [Environment]::SetEnvironmentVariable(
        'Path',
        "$UserPath;$Scripts",
        'User'
    )
}

$env:Path = "$Scripts;$env:Path"
```

Verify:

```powershell
Get-Command code-review-graph
code-review-graph --help
```

---

# 7. Configure CRG MCP deterministically on Windows

If Codex does not inherit the updated user PATH reliably, point the MCP server at the absolute CRG executable.

Find it:

```powershell
(Get-Command code-review-graph).Source
```

Then adapt this block in `~/.codex/config.toml`:

```toml
[mcp_servers.code-review-graph]
command = 'C:\absolute\path\to\code-review-graph.exe'
args = ["serve"]
type = "stdio"
startup_timeout_sec = 30

[mcp_servers.code-review-graph.env]
PYTHONUTF8 = "1"
```

A generic PATH-based alternative is included in [`templates/config.snippet.toml`](templates/config.snippet.toml).

After changing MCP configuration, restart Codex.

Verify from Codex with:

```text
/mcp
```

You should see `code-review-graph` among active servers.

---

# 8. Windows CRG hooks: inspect before trusting

CRG has historically generated Unix-style hook commands on Windows in some versions, e.g. commands containing:

```text
cat >/dev/null
>/dev/null 2>&1
|| true
```

Those are not native PowerShell syntax.

If your generated `~/.codex/hooks.json` still looks like that, use a Windows-specific command variant. A sanitized example matching the setup tested for this guide is provided here:

- [`templates/hooks.windows.json`](templates/hooks.windows.json)

Important properties of the workaround:

- drain hook stdin first
- fail open
- only update CRG inside a Git repository
- keep update output out of model context

Because this is a third-party integration detail, check the current CRG release first: a newer version may have fixed the generator.

---

# 9. Build one graph per repository

Run a full build once per repository:

```powershell
cd C:\path\to\repo
code-review-graph build
code-review-graph status
```

A healthy status should contain non-zero nodes/edges and a real `Last updated` timestamp.

Register repositories if you want multi-repo MCP queries:

```powershell
code-review-graph register C:\path\to\repo --alias repo-a
code-review-graph repos
```

After the initial build, prefer incremental updates:

```powershell
code-review-graph update
```

Do **not** repeatedly run full builds unless necessary.

---

# 10. Git hygiene matters a lot for CRG

In Git repositories, CRG indexes tracked files. This makes `.gitignore` one of the most effective ways to keep the graph focused.

Before the first commit, exclude runtime/vendor/generated content such as:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
node_modules/

.code-review-graph/

data/
logs/
*.log

build/
dist/
coverage/
.cache/

*.db-journal
*.db-wal
*.sqlite-journal

.env
.env.*
!.env.example
*.secret
*.pem
```

Do **not** blindly ignore a `data/` directory if it contains source-controlled fixtures/configuration. Adapt to the repository.

See [`templates/gitignore.example`](templates/gitignore.example).

### Anonymized real-world result

In one large local workspace, CRG initially parsed roughly:

```text
2,057 files
~73,800 graph nodes
~596,000 graph edges
```

After initializing Git and excluding runtime environments, caches, backups, offline dependencies and generated state, the relevant graph dropped to roughly:

```text
86 files
~3,500 graph nodes
~40,000 graph edges
```

That is about **95.8% fewer files in the graph**, without changing the model or reasoning effort.

The exact token savings are workload-dependent; the important point is that structural noise was removed before the model had to explore it.

---

# 11. Keep CRG instructions compact

Do not blindly paste a long CRG instruction block globally.

A concise version is enough:

```text
- If the current repo has a CRG index, use CRG first to narrow code scope.
- Pass the Git repository root explicitly as repo_root.
- Prefer graph queries for symbols, callers/callees, dependencies, impact, architecture and review context.
- Verify non-trivial conclusions in source and tests.
- Source code wins if the graph is stale/incomplete.
```

The provided [`templates/AGENTS.md`](templates/AGENTS.md) includes a slightly fuller version.

---

# 12. Existing Codex sessions

New Codex sessions should load the current global instructions and MCP configuration after restart.

For a session that was already running before the global instructions changed, send this once:

```text
Re-read the global Codex instructions in ~/.codex/AGENTS.md and the RTK.md file they reference. Apply their current version to this session and all following steps.
```

Do **not** repeat it on every prompt.

For CRG, check:

```text
/mcp
```

If `code-review-graph` is not listed, re-reading `AGENTS.md` cannot create a tool that the runtime never loaded. Restart Codex or start a fresh thread/runtime.

More detail: [`docs/EXISTING_SESSIONS.md`](docs/EXISTING_SESSIONS.md).

---

# 13. Measure before adding more layers

After real development sessions, measure rather than assuming.

RTK:

```powershell
rtk gain
```

CRG:

```powershell
code-review-graph status
code-review-graph detect-changes --brief
```

Also watch behavior:

- Does the agent use graph queries before broad source reads?
- Are test runs targeted during iteration?
- Are full validations reserved for meaningful checkpoints?
- Are huge logs/diffs written to disk and sampled instead of dumped?
- Are unchanged files repeatedly reopened?

See [`docs/MEASUREMENT.md`](docs/MEASUREMENT.md).

---

# 14. Optional / experimental items

This stack intentionally stops before adding every possible optimizer.

Potential experiments **after measuring the core stack**:

- disabling `include_apps_instructions` in a code-only profile
- A/B testing response-shaping plugins such as Ponytail
- adding a separate large-log/context proxy only if large non-shell blobs remain a proven bottleneck

Avoid stacking overlapping MCPs just because they all advertise token savings. Every MCP also adds tool schemas/instructions and can increase decision overhead.

See [`docs/OPTIONAL_EXPERIMENTS.md`](docs/OPTIONAL_EXPERIMENTS.md).

---

# 15. Privacy and publication hygiene

Before publishing your setup, remove or replace:

- usernames
- local project names
- absolute personal paths
- private repository names
- branch names that reveal internal work
- API keys/tokens
- MCP Bearer tokens
- environment secrets
- browser profile paths
- database paths
- machine-specific runtime IDs

Do not publish raw CRG graph exports without inspection. They can contain absolute paths and structural metadata about source code.

See [`SECURITY.md`](SECURITY.md).

---

# Quick verification

This repository includes a read-only PowerShell checker:

```powershell
.\scripts\verify-stack.ps1
```

It checks for:

- Codex home/config
- global AGENTS
- RTK
- `tool_output_token_limit`
- Code Review Graph executable
- CRG MCP config
- Windows hooks file
- registered CRG repositories

It does not modify Codex or any repository.

---

# Recommended core stack

```text
High-quality Codex model / high reasoning effort
        +
RTK
        +
concise global AGENTS.md
        +
tool_output_token_limit = 4000
        +
Code Review Graph
        +
igraph (Leiden)
        +
Jedi enrichment for Python-heavy repositories
        +
clean Git tracking / .gitignore
```

Then **stop and measure**.

---

# Sources

Primary upstream references are collected in [`SOURCES.md`](SOURCES.md).
