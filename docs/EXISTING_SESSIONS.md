# Existing Codex sessions

Codex builds its instruction chain at session/runtime startup. After changing global `AGENTS.md`, RTK guidance or MCP configuration, treat **new sessions** and **already-running sessions** differently.

## New sessions

Restart Codex after configuration changes. A fresh session should load:

- current `~/.codex/AGENTS.md`
- referenced RTK guidance
- current `~/.codex/config.toml`
- configured MCP servers

Verify MCP with:

```text
/mcp
```

## Existing sessions

If the session predates the new global instructions, send this **once**:

```text
Re-read the global Codex instructions in ~/.codex/AGENTS.md and the RTK.md file they reference. Apply their current version to this session and all following steps.
```

If CRG is already visible in `/mcp`, add the current repository root explicitly when needed:

```text
Use Code Review Graph with the current Git repository root as repo_root. Use the graph to narrow scope before broad source reads, then verify important conclusions in source and tests.
```

Do not repeat this preamble on every prompt.

## Important MCP limitation

Re-reading an instruction file cannot create a tool that the runtime never loaded.

If a newly installed MCP server does not appear in `/mcp`:

1. close/restart Codex, or
2. start a fresh thread/runtime.
