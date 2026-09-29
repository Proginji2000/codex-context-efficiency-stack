# Codex Context-Efficiency Stack (Windows)

A practical stack for reducing wasted context, preserving Codex quota, and keeping completion verification deterministic.

> DevDay refresh — 29 September 2026: the normal strong-model path now uses **GPT-6.1 Sol**, with **Sol High -> Sol XHigh -> Astra High**. GPT-6 Sol is retained only as a legacy benchmark/fallback lane.

## Recommended architecture

```text
USER REQUEST
    |
    v
PRIMARY CODEX THREAD
    |
    +-- RTK / CRG / skills / bounded context
    |
    +-- luna-low       tiny mechanical work
    +-- luna-medium    normal development
    +-- luna-high      complex but bounded debugging/refactors
    +-- sol-high       GPT-6.1 Sol / high
    +-- sol-xhigh      GPT-6.1 Sol / xhigh
    `-- astra-high     final escalation
            |
            v
 DETERMINISTIC VERIFICATION
 tests / build / lint / typecheck / diff
```

Central rule:

> **If software can prove it, run the software. Use model judgment only for what remains uncertain.**

## Why GPT-6.1 Sol

OpenAI positions GPT-6.1 Sol as a major upgrade over GPT-6 Sol for agentic coding. Standard API pricing remains **$2/M input and $10/M output**, while cached input falls from **$0.20/M to $0.10/M**. OpenAI also reports a 6.4-point DeepSWE v1.1 improvement over GPT-6 Sol's best score at lower reasoning effort and cost.

API pricing is not a direct measurement of Plus/Pro subscription quota. Therefore `sol6-legacy-high` is retained for controlled A/B measurements of actual quota burn, latency, retries and success rate.

## Routing

| Work | Lane |
| --- | --- |
| docs, typo, obvious rename, simple config | `luna-low` |
| normal feature, tests, localized bug, ordinary SQL | `luna-medium` |
| complex bounded debugging, subtle state, non-trivial refactor | `luna-high` |
| architecture, security, risky migration, repeated Luna failure | `sol-high` |
| Sol High still unresolved but scope remains bounded | `sol-xhigh` |
| exceptional end-to-end difficulty | `astra-high` |
| GPT-6 Sol benchmark/fallback | `sol6-legacy-high` |

Recommended escalation:

```text
Luna Medium
 -> deterministic verification
 -> localized retry
 -> Luna High
 -> verification
 -> GPT-6.1 Sol High
 -> verification
 -> GPT-6.1 Sol XHigh
 -> verification
 -> Astra High only when justified
```

## Global Windows update

After `git pull`:

```powershell
cd C:\Dev\codex-context-efficiency-stack
pwsh -ExecutionPolicy Bypass -File .\scripts\update-codex-global-devday-2026.ps1
pwsh -ExecutionPolicy Bypass -File .\scripts\verify-stack.ps1
```

The updater:

- creates timestamped backups under `~/.codex/backups/`;
- refreshes `~/.codex/AGENTS.md`;
- installs Luna / GPT-6.1 Sol / Astra role files;
- adds `sol-xhigh` and the legacy lane when missing;
- refreshes the opt-in `context-efficiency` profile;
- intentionally leaves project-local `.codex/config.toml` files untouched.

Restart Codex afterwards to load new roles.

## Project inheritance

Global `~/.codex/AGENTS.md` applies broadly. Repository `AGENTS.md` adds project-specific rules. A project-local `.codex/config.toml`, however, may shadow global model-routing settings.

Audit from a project directory:

```powershell
pwsh -ExecutionPolicy Bypass -File C:\Dev\codex-context-efficiency-stack\scripts\audit-project-inheritance.ps1
```

Use this before migrating a project with custom routing.

## RTK and Code Review Graph

RTK reduces terminal-output context:

```powershell
rtk init -g --codex
rtk gain
```

CRG narrows code scope before broad source reads:

```powershell
python.exe -m pip install -U "code-review-graph[communities,enrichment]"
code-review-graph install --platform codex
code-review-graph build
```

Source and tests remain authoritative if the graph is incomplete or stale.

## DevDay features tracked by the stack

- **GPT-6.1 Sol**: adopted now in the normal routing path.
- **`/agents`**: useful for tracking delegated work; no special stack config required.
- **Reusable cloud environments**: complementary to this local Windows stack.
- **Code Review / Security Cloud**: complementary surfaces; do not duplicate every local verification pass.
- **Decisions API**: promising for future bounded routing/classification, but not a core dependency while it remains preview/newly released.
- **GPT-6.1 Sol Ultrafast**: excluded from the endurance route by default because it targets speed, not quota preservation.

See [`docs/DEVDAY_2026_UPDATE.md`](docs/DEVDAY_2026_UPDATE.md) and [`docs/MODEL_ROUTING_V2.md`](docs/MODEL_ROUTING_V2.md).

## Verification and measurement

```powershell
.\scripts\verify-stack.ps1
rtk gain
code-review-graph status
```

Track tasks per lane, successful completion, retries, escalations, failed checks, wall-clock latency and visible quota use. The useful metric is **successful engineering work per unit of quota/cost**.

## Recommended stack

```text
Codex primary
+ Luna Low / Medium / High
+ GPT-6.1 Sol High / XHigh
+ Astra High only as final escalation
+ GPT-6 Sol legacy only for A/B
+ RTK
+ concise AGENTS.md
+ skills / progressive disclosure
+ tool_output_token_limit = 4000
+ Code Review Graph where useful
+ deterministic tests/build/lint/typecheck/diff
```

A separate Claude Pro layer is documented in [`CLAUDE_PRO.md`](CLAUDE_PRO.md). The future dual-provider scheduler should remain a separate layer rather than complicating the core Codex stack.
