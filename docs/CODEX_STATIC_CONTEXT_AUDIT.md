# Static Codex context footprint audit — October 27, 2026

## Why this audit exists

The user's first successful **real Codex CLI** JSONL measurement from an explicitly launched read-only Git task (Codex CLI 0.164.0) reported:

| Field | Observed |
| --- | ---: |
| `complete_turns` | 1 |
| `input_tokens` | 108,273 |
| `cached_input_tokens` | 80,384 (74.2% of total input) |
| Input tokens excluding cached | 27,889 |
| `output_tokens` | 259 |
| `processed_events` | 7 |
| JSON stream processing duration | 15.05 s |

The usage event **does not** show the individual underlying prompts or how much was attributable to global rules, project rules, each tool schema, or each worker. `complete_turns: 1` does not prove successful subagent execution or one model invocation. The pipeline duration is **not** a complete task wall-clock benchmark. Cached tokens are already included within `input_tokens`; do not add them again. These counters are **not** Plus/Pro subscription quota accounting.

## What we know from the repository

Current `main` global template `templates/AGENTS.md` is 19,846 ASCII characters. The proposed, **unmerged** PR #14 candidate is 12,977 characters: **6,869 characters less (-34.6%)**. Do not convert this into an asserted token saving, billing reduction, or proportion of the 108,273 input tokens. Source: [PR #14](https://github.com/Proginji2000/codex-context-efficiency-stack/pull/14).

Codex automatically looks for applicable `AGENTS.md` instructions globally and from repository root towards the working directory. It may also incorporate other runtime prompts, tool definitions, and subsequent tool results. The installed global routing config lists ten specialist agent roles. The global `@RTK.md` reference is present but **this audit does not assume it is expanded as an automatically loaded separate file**.

OpenAI explicitly recommends shorter, task-appropriate `AGENTS.md` instructions and fewer unrelated MCP server tools, rather than claiming that a smaller text file guarantees better model performance.

### Attribution: known vs. unknown

| Component | Static measurement possible? | Actual contribution to measured tokens? |
| --- | --- | --- |
| Global AGENTS | Yes: bytes/characters | Unknown |
| Repository/inherited AGENTS | Yes: count/size | Unknown |
| Global RTK.md | Yes: file size only | Unknown whether expanded |
| Installed agent TOML files | Yes: number/total bytes | Unknown when instantiated |
| MCP server configuration | Yes: configured block count | Unknown loaded tool schemas |
| Runtime system/developer instructions | No | Unknown |
| Tool definitions and responses | No | Unknown |
| Parent vs. worker accounting | Not with current sanitized summary | Unknown |
| Cached input prefix and quota billing | Cached count is observed | Actual allowance conversion unknown |

Avoid explaining the 108k figure as a verified bloated `AGENTS.md`, a stuck Git command, or a particular MCP; none is established by these data.

## Local read-only audit (uses zero Codex model tokens)

From the verified repository checkout:

```powershell
cd C:\Dev\codex-context-efficiency-stack
.\scripts\Test-CodexContextFootprint.ps1
.\scripts\Get-CodexContextFootprint.ps1 -ProjectDirectory "C:\Dev\codex-context-efficiency-stack" -AsJson
```

The script only inventories global and applicable repository instruction files, sizes a referenced RTK file separately, counts installed TOML roles, and counts top-level `[mcp_servers.*]` and `[agents.*]` configuration tables. It **does not execute git**, contact Codex/GitHub/OpenAI, access sessions/credentials, store the configuration, print config values, print server names, output file contents or automatically modify anything. It uses the nearest `.git` marker to limit the scan and treats `AGENTS.override.md` as preferred when present. Other runtime override mechanisms or a custom `CODEX_HOME` may affect the true loaded context; this inventory is **not** a definitive prompt trace.

The `candidate_comparison` is available only when explicitly passing a readable local candidate path, for example:

```powershell
.\scripts\Get-CodexContextFootprint.ps1 -CandidatePath "C:\Temp\candidate-AGENTS.md" -AsJson
```

Never download an unverified candidate or overwrite the live `~/.codex/AGENTS.md` solely for an audit.

## Decision on PR #14 and further measurements

- **Done:** old vs. proposed global AGENTS static comparison (19,846 vs. 12,977 chars); synthetic PowerShell regression checks and CI.
- **Done:** first CLI token-counter capture using a new noninteractive Codex task (108,273/80,384/259).
- **Next no-quota step:** inventory the *actual* PC's global/project instruction sizes and configured MCP/agent blocks with this script. Report the counters only.
- **Deferred while user quota is low:** a controlled A/B of the **same** task, same CLI build, same repository snapshot, same permissions, same attached MCPs and models, using separate fresh sessions and safely staged global policy. Measure real success, worker evidence, elapsed time and tokens for each; avoid saturation tests.
- **Acceptance:** no parent execution takeover, missing worker, lost safety or tool-check regressions; only then consider merging PR #14. If behavior is equivalent but token totals differ, report observed variance, not assumed savings.

## Sources

- [OpenAI Codex prompting guide — AGENTS instructions](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
- [OpenAI: Rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
- [OpenAI Codex quota guidance](https://developers.openai.com/fr-FR/docs/pricing)
- [OpenAI Agents API observability (usage categories, not a Codex-specific billing source)](https://developers.openai.com/api/docs/guides/agents-api/observability)

## Correction: 9 MCP headings versus 4 servers

The first local `Get-CodexContextFootprint.ps1` report found `configured_mcp_server_blocks: 9`, but the later Python `tomllib` audit found **4 actual `mcp_servers` entries**, all declared enabled and using stdio. The initial PowerShell regex counted nested TOML headings (such as `[mcp_servers.example.env]`) as distinct servers. The corrected PowerShell script reports both a **distinct-server header count** and a separate number of MCP-related headings including subtables.

The Python TOML parser remains authoritative when the two counts disagree. Neither audit establishes which MCP tools actually load into model context, nor their share of the measured token usage. Do not disable any MCP based on the former nine-server count.
