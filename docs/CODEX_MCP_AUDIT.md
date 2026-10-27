# Codex MCP audit — read-only, no quota usage

## Why

A local 2026-10-27 static footprint reported `configured_mcp_server_blocks: 9`. This **does not mean** nine servers are running, nor that nine sets of tool schemas are available to every Codex agent. Dynamic tool loading and connector behavior depend on the actual Codex runtime. A separate `codex exec --json` test showed 108,273 total input tokens, including 80,384 cached; none of those tokens can be attributed to MCP from that summary alone.

## One safe command on the Windows machine

The user has Python 3.13 installed. The audit needs only the Python 3.11+ standard-library TOML parser, uses **no additional package**, never launches Codex, never initializes an MCP server and never touches existing sessions.

```powershell
cd C:\Dev\codex-context-efficiency-stack
python .\scripts\Test-CodexMcpPolicyAudit.py
python .\scripts\Get-CodexMcpPolicyAudit.py
```

To use an alternate file, pass `--config "C:\path\to\config.toml"`. The script uses `CODEX_HOME/config.toml` if defined, otherwise `~/.codex/config.toml`. Output JSON includes anonymous slots (`mcp_01`, `mcp_02`), activation flags and transport categories, counts of configured allow-/deny-list entries and overlap warnings.

**By default no MCP names, commands, args, URLs, environment variable names, API keys, environment values, headers, identifiers, file paths or config text are printed.** The file is briefly parsed in memory, not copied or uploaded. The script deliberately never reads `auth.json`, session transcripts, logs or network resources.

For local inspection **only**, append `--include-names` to show *MCP server identifiers* in the report; a name may itself be sensitive, so do not paste the resulting output publicly without review. Names are not needed for the initial aggregate audit.

## What the counters mean

- `configured_servers`: declared `[mcp_servers.<id>]` entries in this TOML file only.
- `declared_enabled_servers`: `enabled = true` or omitted, for which Codex's config defaults to enabled. This **does not confirm that the process started or the tool worked**.
- `declared_disabled_servers`: explicitly `enabled = false`.
- `transport_counts`: stdio (command), HTTP (URL), both or missing. No server launch or endpoint validation.
- `servers_with_allowlist`, `servers_with_denylist`: counts of entries with the policy key, not the actual number of model-visible tools.
- `review_flags`: `enabled_with_empty_allowlist`, `allow_deny_overlap` and `transport_needs_review` — suggestions for manual inspection, **not** instructions to mutate config.
- `plugin_mcp_policy_blocks`: configured plugin MCP policy entries; this is **not** a complete inventory of plugins/other sources.
- `runtime_mcp_tools_discovered`, `model_visible_tool_schemas` and `token_attribution`: deliberately `null`; the audit cannot measure these.

Project-local `.codex/config.toml`, managed configuration, plugin manifests, runtime authorization and server-side dynamically discovered tools may modify the effective catalog; this single-file report does not resolve overrides.

## Decision sequence after the anonymous report

1. Verify how many of the nine declared servers are enabled vs. explicitly disabled. Flag missing transport or empty allowlists.
2. Inspect the actual use case for each enabled server: critical (e.g. Context7, Playwright, CRG), occasional, redundant, or unknown. **Do not disable any without verifying why it was added.**
3. If a server has a broad tool catalog, test `enabled_tools` or `disabled_tools` only on a **separate backed-up opt-in config**, not in the working global profile. Codex documentation supports both; reports of allow-list problems on older versions require a real smoke test.
4. Before/after measurement of **actual** exposed tool schemas or token usage requires an explicitly authorized and controlled fresh runtime comparison, not a TOML inventory. Preserve deterministic acceptance and all agent permissions.

Do not assume Responses API `tool_search`/`defer_loading` applies automatically to the installed Codex CLI 0.164.0; they are separate integration surfaces.

## Official references

- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference): `mcp_servers.<id>.enabled`, `enabled_tools`, `disabled_tools`; plugin policies and project trust.
- [OpenAI API tool search](https://developers.openai.com/api/docs/guides/tools-tool-search): how deferral works in the **API/Agents API**, not a guarantee about Codex CLI.
- [MCP allowlist issue #47102](https://github.com/openai/codex/issues/47102): reported unexpected tool disappearance on prior CLI builds; check current status before any policy changes.
