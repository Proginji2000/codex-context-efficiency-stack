# Opt-in Codex MCP scopes — original four servers plus optional Serena and shadcn

The 2026-10-27 local TOML audit confirmed **four configured, declared enabled stdio MCP servers**: `code-review-graph`, `context7`, `node_repl`, and `playwright`. This list is *not* a runtime tool-schema inventory. The previous nine MCP counts were nested TOML headers, since corrected.

Codex's documented `-c key=value` switch overrides settings for **one invocation** (see [CLI reference](https://learn.chatgpt.com/docs/cli/reference) and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)). `scripts/Invoke-CodexScopedMcp.ps1` provides a narrow wrapper for that feature.

## Scope selection

| Scope | Disabled only during this CLI invocation | Still configured and available |
| --- | --- | --- |
| `git` | code-review-graph, context7, node_repl, playwright | none of those four |
| `code` | node_repl, playwright | code-review-graph, context7 |
| `docs` | code-review-graph, node_repl, playwright | context7 |
| `ui` | none | all four |

**Why `node_repl` stays in UI:** some Codex Desktop/browser workflows rely on the Node REPL MCP; do not interpret `node_repl` and `playwright` as interchangeable. This wrapper targets Codex **CLI invocations only**, not preexisting Codex Desktop threads, and it does not repair Codex runtime browser-injection bugs.

**Why `code-review-graph` is not used for Git-only checks:** the scoped Git task is about current branch/status/HEAD; no dependency graph is required. The core Git executable remains available to Codex within its regular sandbox. For deep code exploration, use `code`, not `git`.

## Safe preview (zero Codex calls)

```powershell
cd C:\Dev\codex-context-efficiency-stack
.\scripts\Test-CodexScopedMcp.ps1
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope git -AsJson
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope code -AsJson
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope docs -AsJson
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope ui -AsJson
```

These invocations only print the **effective planned MCP disable list** for the chosen scope; they do not launch Codex, load MCPs, spend tokens, inspect private config values, or modify global settings.

## Optional actual CLI run

Run this **only when ready to consume Codex quota**:

```powershell
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope git `
    -ProjectDirectory "C:\Dev\codex-context-efficiency-stack" `
    -Prompt "Read-only: delegate a worker to report current Git branch and HEAD. Do not modify files." `
    -Run
```

The wrapper always passes `codex exec -C <project> --ephemeral --sandbox read-only` unless an explicitly selected alternate sandbox is provided. For `git` scope a write sandbox is rejected. The individual MCP overrides use `-c mcp_servers.<id>.enabled=false`; none is written to disk. It invokes the `codex` executable already on PATH and returns its exit status. No update or installation is performed. The underlying Codex CLI can still access its standard system tools and built-in skills, as its sandbox permits.

The optional `code` and `ui` scopes default to `read-only` as well. For a genuinely authorized code-writing task, you may explicitly select `-Sandbox workspace-write`, subject to the normal Codex approvals; this does **not** bypass sandboxing.

## Serena and shadcn (verified locally on 29 October 2026)

The operator verified `serena-agent==2.1.0` running in the Codex TUI (3 tools, LSP Python symbol lookups and project-memory persistence across **separate sessions**), and the official `shadcn@latest mcp` (7 tools; registry search and view on a disposable directory). Both MCP definitions are registered as `enabled=false` in the user's normal `config.toml`. The global configuration was backed up before each addition. These observed results do **not** mean the tools launch automatically on ordinary Codex sessions.

New opt-in flags in the existing launcher (old calls unchanged):

| Flag | Allowed scope | Effect only on selected invocation |
| --- | --- | --- |
| `-EnableSerena` | `code` or `ui` | `-c mcp_servers.serena.enabled=true` |
| `-EnableShadcn` | `ui` | `-c mcp_servers.shadcn.enabled=true` |
| `-Interactive` | Any scope | Start the interactive Codex TUI instead of noninteractive `codex exec`; `-Prompt` optional |

**Preview without starting any model or MCP** (run from this repository):

```powershell
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope code -EnableSerena -AsJson
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope ui -EnableShadcn -Interactive -AsJson
.\scripts\Test-CodexScopedMcp.ps1
```

**A real UI project when explicitly selected**:

```powershell
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope ui -EnableShadcn -Interactive -Run -ProjectDirectory 'C:\Dev\some-ui-project'
```

For deeper code navigation, choose `-Scope code -EnableSerena -Interactive -Run`; optional flags may be combined under `-Scope ui`. Actual `-Run` launches Codex and can consume quota, start MCPs and download any missing dependencies. Scope options apply **at launch time**, not automatically based on the semantics of a prompt in an already-running Codex session. Runtime subagent access still needs observation on a legitimate work item.

The launcher does **not** install, enable globally, disable other managed bridges such as `codex_apps`, or modify `AGENTS.md`. Serena maintains project-local Markdown memories at `.serena/memories/`; global or cloud auto-capture is not part of this integration. Keep project memory writes scoped to approved repositories and review new metadata before committing. Do not run synthetic dashboard or memory projects to justify extra tools.

## Measurements and limitations

This makes a narrower MCP configuration available per new CLI execution, **not a proven optimization**. The first unfiltered Git test reported 108,273 cumulative input tokens including 80,384 cached and 259 output. It did not prove a successful worker Git check, and cannot be directly compared against different tasks or versions.

Before claiming savings, compare two identical, successful runs with and without MCP overrides using the same CLI version, repository snapshot, AGENTS file, model/effort, prompt, permissions and workers. Cache reuse and model/tool events can make one-off figures noisy. Use the existing `Convert-CodexExecUsage.ps1` for aggregated usage when appropriate. A normal live Codex execution consumes quota; the preview and synthetic tests do not.

No user config writes; no MCP starts in preview; no collection of session history; **no automatic changes to the user's default tooling or PR #14**.

Note: a CLI-scoped MCP override is not guaranteed to apply to external plugins or other managed runtime tools. It only changes the named `mcp_servers` keys for that new invocation. If a required UI/browser tool is absent, use the full `ui` scope and verify actual tool exposure.
