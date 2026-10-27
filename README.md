# Codex Context-Efficiency Stack (Windows)

A practical stack for reducing wasted context, preserving Codex quota, and keeping completion verification deterministic.

> 27 October 2026 refresh: **GPT-6.1 Terra** is now an intermediate capability tier between Luna and Sol. Luna remains the default endurance worker; Sol/Astra remain the complex-work escalations.

## Recommended architecture

```text
USER REQUEST
    |
    v
PRIMARY CODEX THREAD (Luna orchestrator only)
    |
    +-- RTK / CRG / skills / bounded context
    |
    +-- luna-low       tiny mechanical work
    +-- luna-medium    normal development
    +-- luna-high      bounded cost-first reasoning
    +-- terra-medium   scoped fixes / UI / computer use
    +-- terra-high     difficult but bounded implementation/debugging
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
| bounded reasoning where Luna remains sufficient | `luna-high` |
| scoped code fix, UI, visual/computer-use work | `terra-medium` |
| difficult but bounded implementation/debugging | `terra-high` |
| complex coding, architecture, security, risky migration | `sol-high` |
| Sol High still unresolved but scope remains bounded | `sol-xhigh` |
| exceptional end-to-end difficulty | `astra-high` |
| GPT-6 Sol benchmark/fallback | `sol6-legacy-high` |

Recommended escalation:

```text
Luna Medium
 -> deterministic verification
 -> localized retry
 -> Luna High or Terra Medium (task-shaped)
 -> Terra High when still bounded
 -> GPT-6.1 Sol High
 -> verification
 -> GPT-6.1 Sol XHigh
 -> verification
 -> Astra High only when justified
```

## Documentation & curated optional tools

Start with the [documentation index](docs/README.md), including [optional integrations](docs/OPTIONAL_INTEGRATIONS.md).

- **GitHub Spec Kit**: opt-in specification -> plan -> tasks -> implementation for non-trivial feature work, integrated per project (not global).
- **Anthropic frontend-design**: included as an Apache-2.0 skill in `.agents/skills/frontend-design/`. For user-wide Codex use, explicitly run `.\scripts\install-frontend-design.ps1` once.
- **Shannon**: manual and explicitly authorized staging web/API pentesting only, never a default agent step.
- **HatchZip**: separate manual disk-space utility; archive contents are progressively removed from the source archive.

These additions do not replace RTK, Code Review Graph, or deterministic acceptance checks. The global updater does not silently install or run them.

## Automatic frontend skill routing

The Luna parent now delegates visual/UI requests (dashboards, web apps, components, styling, responsive layouts) to `ui-implementer` on **GPT-6.1 Terra Medium**. That worker loads `frontend-design` automatically when installed; no explicit `$frontend-design` mention is required.

One-time, user-wide Windows skill installation after cloning/updating this repository:

```powershell
.\scripts\install-frontend-design.ps1
```

The frontend skill needs no Node.js, Python, uv, Docker, or extra API subscription. Confirm actual use through the delegated worker's activity and result; static file checks do not prove automatic activation. [Integration policy](docs/OPTIONAL_INTEGRATIONS.md).

## Global Windows update

After `git pull`:

```powershell
cd C:\Dev\codex-context-efficiency-stack
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\update-codex-global.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-stack.ps1
```

The updater:

- creates timestamped backups under `~/.codex/backups/`;
- refreshes `~/.codex/AGENTS.md`;
- installs Luna / GPT-6.1 Terra / GPT-6.1 Sol / Astra role files;
- adds `sol-xhigh` and the legacy lane when missing;
- refreshes the opt-in `context-efficiency` profile;
- intentionally leaves project-local `.codex/config.toml` files untouched.

Restart Codex afterwards to load new roles.

## Project inheritance

Global `~/.codex/AGENTS.md` applies broadly. Repository `AGENTS.md` adds project-specific rules. A project-local `.codex/config.toml`, however, may shadow global model-routing settings.

Audit from a project directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Dev\codex-context-efficiency-stack\scripts\audit-project-inheritance.ps1
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
- **Decisions API**: promising for future bounded routing/classification, but not a core dependency because API usage is separate from the Codex subscription.
- **GPT-6.1 Sol Ultrafast**: excluded from the endurance route by default because it targets speed, not quota preservation.

See [`docs/DEVDAY_2026_UPDATE.md`](docs/DEVDAY_2026_UPDATE.md) and [`docs/MODEL_ROUTING_V4.md`](docs/MODEL_ROUTING_V4.md).

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
+ GPT-6.1 Terra Medium / High
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
