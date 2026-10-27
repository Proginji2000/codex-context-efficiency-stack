# Model Routing v4 (October 2026): Luna -> Terra -> Sol -> Astra

This routing layer optimizes for successful engineering work per unit of subscription quota while keeping deterministic verification authoritative.

## Current model roles

OpenAI's current model-selection guidance separates the family clearly:

- **GPT-6 Luna**: focused, high-volume, cost-sensitive work.
- **GPT-6.1 Terra**: scoped code fixes, visual reasoning, computer use, and everyday agentic work.
- **GPT-6.1 Sol**: complex coding and professional work where capability matters.
- **GPT-6 Astra**: the hardest ambiguous/end-to-end work.

Terra is therefore an intermediate capability tier, not a replacement for either Luna or Sol.

## Cost signals

Standard API token prices are useful as relative signals, but they are **not** a formula for Plus/Pro Work/Codex quota burn:

| Model | Input / 1M | Cached input / 1M | Output / 1M |
| --- | ---: | ---: | ---: |
| GPT-6 Luna | $0.10 | $0.01 | $0.50 |
| GPT-6.1 Terra | $1.00 | $0.05 | $5.00 |
| GPT-6.1 Sol | $2.00 | $0.10 | $10.00 |
| GPT-6 Astra | $10.00 | $1.00 | $50.00 |

OpenAI explicitly says the same Work/Codex allowance covers substantially more tasks with GPT-6.1 Terra than with GPT-6.1 Sol or GPT-6 Astra. No exact Terra-vs-Luna subscription multiplier is currently assumed by this stack.

## Lanes

| Lane | Model | Reasoning | Intended work |
| --- | --- | --- | --- |
| `luna-low` | `gpt-6-luna` | `low` | tiny mechanical work |
| `luna-medium` | `gpt-6-luna` | `medium` | routine/high-volume development, tests, exploration, localized fixes |
| `luna-high` | `gpt-6-luna` | `high` | cost-first deeper reasoning on bounded work |
| `terra-medium` | `gpt-6.1-terra` | `medium` | scoped code fixes, everyday agentic coding, visual/UI and bounded computer-use work |
| `terra-high` | `gpt-6.1-terra` | `high` | difficult but bounded implementation/debugging or computer-use work |
| `sol-high` | `gpt-6.1-sol` | `high` | complex coding, architecture, security-sensitive work, risky migrations, broad uncertainty |
| `sol-xhigh` | `gpt-6.1-sol` | `xhigh` | very hard bounded work after Sol High remains unresolved |
| `astra-high` | `gpt-6-astra` | `high` | exceptional end-to-end difficulty / unresolved Sol XHigh |
| `sol6-legacy-high` | `gpt-6-sol` | `high` | explicit regression/A-B fallback only |

## Orchestrator-only execution contract

The primary session owns routing, dependency tracking, worker assignment, coordination, evidence review, and the final user-facing summary. It must not independently perform substantive repository exploration, research, editing, tests, or review.

- One actionable engineering task: assign **one** worker.
- Several independent engineering tasks: assign separate workers up to the concurrency cap, without conflicting writes.
- Dependent tasks: delegate each phase sequentially, reusing compact handoffs and verified evidence.
- A tiny engineering edit is still delegated: the user prefers a pure orchestrator over saving the cost of a single spawn.
- Conversational responses and coordination overhead (for example, minimal read-only Git status to assign ownership) do not require delegation.
- If no subagent can be started, do not silently execute the task in the parent. Report the blocker and obtain explicit permission to switch operating mode.
- Summaries must identify **actual** worker roles and verification results. Never infer successful delegation just because roles exist in config.

**Evidence and limit:** an AGENTS.md rule is behavioral guidance, not a tool-permission interlock. Verify execution traces or the Codex agents view to confirm subagent starts and outcomes. A future hard enforcement wrapper would need to restrict the parent tool surface and audit dispatch events; that wrapper is not implemented in this repository.

### Practical acceptance tests

1. Ask the primary Luna thread for a one-file README edit: expect at least one delegated worker, not a direct parent edit.
2. Ask for unrelated docs and tests: expect two scoped workers (parallel if safe), with outputs collected by the parent.
3. Ask for implementation then tests dependent on it: expect two **sequentially** delegated phases, never two simultaneous writers.
4. Make agent creation unavailable: expect a truthful blocked status, not parent execution.
5. Inspect the agents view/event trace and final worker summary. Passing static policy checks alone does not establish runtime compliance.

## Frontend design worker — automatic skill selection

A visual/UI frontend request is delegated by Luna to `ui-implementer` (GPT-6.1 Terra Medium) even when the user does not name a skill. The worker loads `$frontend-design` from its available user/project skills at the beginning of the visual work. Examples: responsive websites, dashboard layouts, app UI, styling or visual polish.

If the skill is not installed, the worker reports its absence rather than falsely claiming to have used it. Setup is a one-time explicit local step using `scripts/install-frontend-design.ps1`; the global stack updater registers the role but does not install unrelated programs.

This is a behavioral instruction; verify the subagent's actual skill load and build/accessibility checks on representative work.

## Routing is not a single rigid ladder

Use task shape first.

### Routine/high-volume

```text
Luna Low / Medium
  -> deterministic checks
  -> retry once if corrective path is obvious
```

### Scoped code fix / UI / computer-use

```text
Luna Medium (when cheap attempt is sensible)
  -> Terra Medium
  -> Terra High if still bounded and genuinely difficult
  -> Sol High if complexity broadens or remains unresolved
```

A well-scoped task can route directly to Terra Medium when visual reasoning, computer use, or stronger everyday agentic coding is likely to save retries.

### Complex/high-risk

```text
Sol High
  -> deterministic checks
  -> Sol XHigh
  -> Astra High only for exceptional unresolved work
```

Architecture, security-sensitive changes, risky migrations, broad cross-module invariants, and unfamiliar hard problems should not be forced through Terra merely to save quota.

## Why keep Luna High?

Terra costs roughly 10x Luna per standard API input/output token. Luna High can still be the correct endurance choice for a bounded text/code reasoning problem where the stronger Terra tool/vision profile is not needed. Measurement should decide whether a given workload benefits more from Luna High or Terra Medium.

## Why no Terra XHigh/Max default lane?

GPT-6.1 Terra supports reasoning through `max`, but OpenAI still recommends GPT-6.1 Sol or Astra for the most complex coding tasks. The stack therefore stops at Terra High by default to avoid spending heavy reasoning on the wrong model family. Explicit manual use remains possible for benchmarking or a proven workload.

## Terra evaluation notes

OpenAI reports:

- GPT-6.1 Terra standard API prices are 50% below GPT-6.1 Sol.
- Terra completes the highlighted computer-use tasks more than 3x faster than Sol/Astra on average.
- Terminal-Bench 4.0 reaches 50.3% at max effort, more than double GPT-5.6 Terra's published score.
- For the most complex coding tasks, Sol and Astra remain the recommended choices.

These are useful priors, not substitutes for our own task-level measurements.

## Decisions API

As of 22 October 2026, the Decisions API is generally available with GPT-6 Luna and supports up to 400 questions per request. It is relevant to future bounded routing/classification, including the Jev-like role discussed for the dual-provider stack.

It is **not** a dependency of this subscription-focused stack because API usage is billed separately. The normal router should remain deterministic unless measurement shows a paid decision call improves total economics.

## Completion gate

A task is complete only when requested behavior is implemented, relevant deterministic checks pass, the final diff matches scope, and no known failure is hidden.

## Model benchmarking

When comparing lanes, keep repository, scope, context size, reasoning effort, acceptance checks and task type as comparable as possible. Record:

- first-pass success
- retries/escalations
- elapsed time
- visible quota before/after when available
- deterministic verification outcome

Do not infer Work/Codex subscription consumption directly from API token prices.
