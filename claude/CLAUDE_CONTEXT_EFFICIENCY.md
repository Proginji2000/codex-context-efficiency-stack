# Claude Code context and quota efficiency

Preserve correctness while minimizing unnecessary context, repeated work, tool-output tokens, and model escalation.

## Routing and delegation

- Keep the main session on Sonnet for normal engineering work unless the user explicitly selects another model.
- Use `Explore` or `haiku-low` for cheap repository exploration and tiny mechanical work.
- Use `sonnet-medium` for normal self-contained feature work, tests, ordinary debugging, SQL changes, and clear multi-file edits.
- Use `sonnet-high` for complex but bounded debugging, subtle state logic, or non-trivial refactors.
- Use `opus-high` for architecture, security-sensitive changes, risky migrations, broad invariant uncertainty, or repeated Sonnet failure.
- Use `opus-xhigh` only as a final escalation for genuinely difficult unresolved work.
- Never select `fable` or `best` automatically. Fable can consume usage credits depending on the plan. Use it only after the user explicitly chooses it.
- Route at meaningful task boundaries, not after every read, command, edit, or test.
- Retry the same lane once when a failure is localized and the corrective path is clear before escalating.
- Do not delegate simple sequential work merely to use a subagent. Use a subagent when isolated context, verbose exploration, or an independent workstream is materially useful.
- Give subagents bounded context: goal, constraints, relevant files/symbols, known evidence, and acceptance criteria.
- Never claim a model switch or delegation happened when it did not.

## Deterministic verification

- If software can prove a result, run that software instead of asking another model to judge it.
- Use the smallest relevant tests during iteration; broaden validation at meaningful checkpoints.
- Before declaring completion, verify requested behavior, inspect the relevant final diff, and run applicable build, test, type, lint, or formatter checks.
- Never hide or silently ignore a failed check.

## Terminal output

- Use RTK for supported commands when it preserves the diagnostic information required by the task.
- Prefer quiet or concise command modes.
- Do not dump large logs or command outputs into context. Save full output to disk and inspect targeted ranges.
- For unknown unoptimized output, inspect roughly the first 4000 bytes or a targeted range, then expand only as needed.
- Preserve full error messages, failing assertions, warnings, and stack traces when they are necessary for diagnosis.

## Code exploration

- Search before reading large files.
- Prefer symbol search, `rg`, LSP, bounded ranges, and targeted diffs over whole-file or whole-tree reads.
- When a Code Review Graph index is available, use it to narrow symbols, callers, dependencies, impact, and likely tests before broad exploration.
- Source code and tests remain authoritative if a graph is stale or disagrees with the repository.
- Do not reread unchanged files without a reason.

## Context management

- Do not restate information already established in the current context.
- Summarize completed investigation phases before moving to a materially different phase when that reduces context pressure.
- Preserve decisions, constraints, unresolved issues, file names, symbols, and verification evidence when compacting.
- Keep global instructions concise. Put project-specific conventions in the repository and detailed recurring procedures in skills or path-scoped rules.
- For long, interruption-prone work, maintain one concise durable task-state file. Do not create one for trivial tasks.

## Parallelism

- Maximum configured concurrent subagents: 2.
- Nested subagent spawning is disabled by configuration.
- Parallelize only independent workstreams; avoid overlapping agents exploring the same code.

## Completion gate

A task is complete when the requested behavior is implemented, relevant deterministic checks pass, the final diff is within scope, and no known failure is being concealed.
