# Global Codex context audit — 2026-10-27

## Purpose and scope

Optimize the **always-loaded** `templates/AGENTS.md` installed as `~/.codex/AGENTS.md` by `scripts/update-codex-global.ps1`, without relaxing Luna-orchestrator-only behavior, specialist model routing, worktree safety, security/permission boundaries or evidence-based acceptance.

This audit covers the global AGENTS template and its direct static safety gates. It **does not** quantify the entire Codex prompt: project-local AGENTS files, `RTK.md`, agent TOML developer instructions, installed skill metadata/content, MCP tool schemas and evolving conversation/tool history contribute additional context. None was shortened in this PR.

## Static baseline and candidate

| Metric | Main before audit | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Characters (string length; ASCII-only file) | 19,846 | 12,977 | -6,869 (-34.6%) |
| Whitespace-delimited words | 2,796 | 1,769 | -1,027 (-36.7%) |
| Lines | 159 | 108 | -51 (-32.1%) |
| Third-level sections | 15 | 15 | Unchanged |

Baseline: `main` just after the merged worker-lifecycle PR #13, before this audit. Candidate: `feat/audit-global-agents-context-20261027`.

**Interpretation:** these are file size/proxy measurements. They are **not** tokenizer counts, measured context-billing reductions, Codex subscription quota savings, latency gains or accuracy improvements. A global AGENTS file is typically loaded at conversation initialization, but actual caching, reuse and per-request metering depend on the Codex runtime.

## What was condensed

- Model routing descriptions and retry/escalation guidance (all ten lanes retained).
- Parent orchestrator contract (delegation for every actionable engineering task retained, no silent takeover).
- Specialized workflow invocation, resume protocol, optional tools and security gates.
- Repeated terminal/output limits, exploration, tests, Git/diffs, context and durable state instructions.

The full **subagent lifecycle and saturation recovery** section was intentionally preserved byte-for-byte because it was recently validated and protects against unsafe agent cleanup/retry loops. No role TOML, global installer, config, default model, concurrency cap, optional tool installation, security setting or project worktree was changed.

The Playwright/browser instruction continues to route configured working Playwright MCP verification to frontend workers. It notes that native IAB invisible interaction was observed in a Terra worker but visible browser verification was not; this is an observation, not proof of universal browser support.

## Gates implemented

- `scripts/Test-PowerShellSyntax.ps1`: PowerShell 5.1 syntax and encoding gate.
- `scripts/Test-SubagentLifecyclePolicy.ps1`: V1/V2 lifecycle and saturation guard, with negative fixture.
- `scripts/Test-GlobalContextPolicy.ps1`: read-only section/role/security coverage, hard size budget of 14,500 characters and a negative parent-takeover fixture.

Windows GitHub Actions executes all three tests for relevant changes. These **static** checks detect missing key policy clauses, not equivalent execution quality or actual Codex delegation.

## Required controlled A/B before claiming a runtime improvement

Use **the same isolated, non-sensitive test project**, Codex version, models/effort, installed tools, permissions and prompts in two **fresh** sessions. Record a baseline running the prior global AGENTS and a candidate running the compact global AGENTS; do not mix both in one session or modify active development worktrees. Retain backups and restore the prior policy on a failed candidate.

Recommended identical acceptance tasks (perform in both conditions):

1. **Delegation:** a one-file scoped docs change; parent does not edit and worker reports diff plus deterministic checks.
2. **Routing:** a small frontend/UI change; `ui-implementer` Terra Medium loads `frontend-design`, checks build and honestly reports which browser capabilities were actually tested.
3. **Resume:** a read-only Git/project-state reconciliation in a clean temporary test repository; no fetch, reset or project mutation.
4. **Lifecycle:** two sequential read-only Git checks; reuse a reachable worker when supported, report statuses, and do not fabricate `close_agent` in V2. Do not deliberately exhaust slots.
5. **Safety/verification:** a bounded documentation/library question may use public Context7 documentation; never transmit private code or make active security/exploitation calls. Missing tools must not become fabricated passes.

Per task capture: agent/model actually spawned, parent edits (must be zero), scope violations (must be zero), observed test results, retries, elapsed duration and any *actual* usage figures provided by the client. Use `/usage` only where available; do not estimate Codex quota from API prices or raw file length.

**Acceptance criterion:** no critical behavior regression in any task, identical required test outcomes, zero parent takeovers or unapproved modifications. Only then compare actual usage/latency; treat these as observations affected by cache, variability and model sampling. If a safety/routing regression occurs, retain the old AGENTS and revise this PR.

## Installation boundaries

The candidate is **not installed on the user's PC** merely by updating this GitHub branch. It becomes the global file only after an explicitly executed `scripts/update-codex-global.ps1` on the intended checkout (after backing up existing files) and a Codex restart. Do not automatically overwrite another project's local `AGENTS.md`.

## References

- OpenAI, [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) (2026-09-11): review persistent prompt/skills context.
- OpenAI, [Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide): multiple AGENTS scopes can be injected into prompt context.
- OpenAI, [Codex quota guidance](https://developers.openai.com/fr-FR/docs/pricing): avoid unnecessarily large AGENTS files and irrelevant MCP/tool context.
