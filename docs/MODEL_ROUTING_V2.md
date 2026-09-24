# Model Routing v2: Luna-first, evidence-based escalation

This optional v2 layer sits on top of the original context-efficiency stack.

The core idea is simple:

1. Use deterministic software for facts.
2. Use the cheapest sufficient coding lane for generation.
3. Escalate only when evidence justifies it.
4. Keep context bounded with targeted reads, concise tool output, skills and subagents.

## Important implementation detail

`AGENTS.md` can express routing policy, but it does not magically change the model of the already-running primary Codex turn.

For deterministic model selection, use Codex multi-agent roles backed by separate TOML config layers. Codex supports:

- `agents.default_subagent_model`
- `agents.default_subagent_reasoning_effort`
- custom roles via `agents.<name>.config_file`

The role config can set its own `model` and `model_reasoning_effort`.

This repository provides four lanes:

| Lane | Model | Reasoning | Intended work |
| --- | --- | --- | --- |
| `luna-low` | `gpt-6-luna` | `low` | tiny edits, renames, docs, simple config |
| `luna-medium` | `gpt-6-luna` | `medium` | normal feature work, localized debugging, tests |
| `luna-high` | `gpt-6-luna` | `high` | complex debugging, multi-file logic, non-trivial refactors |
| `sol-high` | `gpt-6-sol` | `high` | architecture, security-sensitive changes, migrations, repeated failure |

Luna supports `none`, `low`, `medium`, `high`, `xhigh` and `max`; `medium` is its default. The lane names above are policy choices, not model limitations.

## Recommended architecture

```text
USER REQUEST
    |
    v
PRIMARY CODEX ORCHESTRATOR
    |
    +-- deterministic classification when obvious
    |
    +-- luna-low
    +-- luna-medium
    +-- luna-high
    `-- sol-high
            |
            v
     IMPLEMENTATION PASS
            |
            v
   DETERMINISTIC VERIFICATION
   tests / build / lint / typecheck / diff
            |
      +-----+-----+
      |           |
     PASS        FAIL
      |           |
 scope check   retry budget
      |           |
  COMPLETE     Luna higher lane
                  |
              repeated failure /
              high-risk uncertainty
                  |
               Sol High
```

## Routing policy

Use the lowest lane that is clearly sufficient.

### `luna-low`

Prefer for:

- spelling or documentation edits
- renames with obvious scope
- small configuration changes
- one-file mechanical edits
- adding a straightforward field or assertion

Do not use it when the task requires architectural inference, security review, risky migration logic or broad debugging.

### `luna-medium`

Default worker lane for most development tasks:

- small and medium features
- well-scoped endpoints
- tests
- ordinary SQL changes
- validation logic
- localized bugs
- multi-file changes with clear boundaries

### `luna-high`

Use when the task has significant reasoning load but remains well bounded:

- complex debugging
- unfamiliar multi-file control flow
- subtle state transitions
- large refactors with known acceptance criteria
- concurrency logic that is not security critical

### `sol-high`

Escalate directly or after failed Luna attempts for:

- architecture decisions with multiple plausible designs
- authentication, authorization, crypto or other security-sensitive code
- destructive or difficult-to-reverse migrations
- repeated failed implementation attempts
- broad uncertainty about invariants or blast radius
- tasks where the acceptance criteria cannot be established confidently from the current evidence

## Deterministic verification first

Never spend model judgment on facts software can establish.

Use the repository's actual toolchain:

```text
Compilation  -> compiler/build command
Tests        -> test runner
Types        -> type checker
Formatting   -> formatter/check mode
Lint         -> linter
Changed code -> git diff / git status
```

A model may interpret failures, but it should not replace the command that proves whether the check passed.

## Retry and escalation budget

A practical default:

```text
Luna Medium attempt 1
  -> deterministic checks
  -> if fixable/localized: Luna Medium attempt 2
  -> deterministic checks
  -> if still failing or blast radius expanded: Luna High
  -> deterministic checks
  -> if unresolved/high-risk: Sol High
```

Do not escalate merely because a stronger model exists.

Do not keep retrying the same lane indefinitely either.

## Completion gate

Report completion only when all applicable items are true:

- requested behavior is implemented
- relevant tests pass
- build/type/lint checks pass where applicable
- final diff matches requested scope
- no known failure is hidden or ignored
- risky assumptions are either verified or explicitly reported

For tiny changes, do not invent heavyweight validation that the repository does not normally require.

## Context efficiency rules

Routing saves model capacity, but context discipline usually saves more.

Keep these rules from the original stack:

- search before broad reads
- bound file reads to relevant ranges
- use CRG when it narrows the search materially
- keep tool output concise
- inspect targeted diffs during iteration
- avoid rereading unchanged material
- compact completed investigation phases
- use subagents with narrow tasks instead of copying the whole parent history

For repository-specific workflows, prefer skills under `.agents/skills/` with concise `name` and `description` metadata. Load their full instructions only when the task triggers them.

## Jev or another external decision model

Optional only.

Do not make an external decision model a mandatory hop for every task. Most routing decisions can be made from deterministic rules, and most completion facts come from the toolchain.

A bounded decision model can still help at genuinely ambiguous boundaries, for example:

- continue vs escalate after conflicting evidence
- whether the blast radius has materially increased
- whether verification coverage is sufficient when no deterministic single answer exists

A typed response or confidence score is not proof of correctness. Tests, build output and source evidence remain authoritative.

## Install the lane configs

Copy the role files from:

```text
templates/agents/
```

to a stable location under your Codex home, for example:

```text
~/.codex/agents/
```

Then merge the contents of:

```text
templates/config.routing.snippet.toml
```

into:

```text
~/.codex/config.toml
```

Restart Codex after editing the configuration.

## Suggested first deployment

Start conservatively:

```text
primary thread: your current preferred model
spawned workers: Luna Medium by default
small obvious work: Luna Low
hard bounded work: Luna High
Sol High: architecture / security / migration / repeated failure
```

Measure real tasks before making the router more aggressive.

Track at least:

- tasks per lane
- successful completion by lane
- retries
- escalations
- failed verification passes
- context/token usage where visible
- wall-clock latency

The useful metric is successful work per unit of quota/cost, not raw token count alone.
