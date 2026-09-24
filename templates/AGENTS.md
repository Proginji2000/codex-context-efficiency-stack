@RTK.md

## Global context and token efficiency

Preserve correctness while minimizing unnecessary context, tool-output tokens, repeated work, and unnecessary model escalation.

### Model routing and delegation

- If the configured custom Codex roles are available, use the lowest sufficient lane at meaningful task boundaries: `luna-low` for tiny mechanical low-risk work, `luna-medium` for normal development, `luna-high` for complex but bounded reasoning, and `sol-high` for architecture, security-sensitive work, risky migrations, broad invariant uncertainty, or repeated Luna failure.
- Prefer `luna-medium` as the default spawned worker unless the task is obviously smaller or harder.
- Do not spawn or switch lanes after every read, command, edit, or test. Route at task boundaries, after a materially different phase begins, or when verification evidence justifies escalation.
- Never use another model to answer a fact that deterministic tooling can establish. Run the compiler, tests, type checker, linter, formatter/checker, `git diff`, or other authoritative tool instead.
- A failed attempt does not automatically require Sol. Retry the same Luna lane once when the failure is localized and the corrective path is clear; otherwise move to `luna-high`. Escalate to `sol-high` when repeated attempts fail, the blast radius expands materially, or high-risk uncertainty remains.
- If custom roles are unavailable in the current runtime, continue with the active model and follow the same verification discipline. Never claim a model switch or delegation occurred when it did not.
- Give subagents bounded context: goal, constraints, relevant files/symbols, known evidence, and acceptance criteria. Do not copy the entire parent conversation unless it is genuinely required.
- Avoid parallel agents that perform substantially overlapping exploration. Parallelism is useful only when branches of work are independent.

### Terminal output

- Use RTK for supported commands whenever it preserves the information required for the task.
- Prefer concise or quiet command output.
- Never print large command outputs into the conversation when only a summary, error, or relevant subset is needed.
- Redirect large raw outputs to files and inspect only the relevant sections.
- Preserve full error messages, warnings, stack traces, failing assertions, and other diagnostic evidence when needed.

### Code exploration

- Search before reading.
- Prefer targeted symbol searches, `rg`, and bounded file ranges over opening entire large files.
- Do not reread unchanged files unless necessary.
- Do not recursively enumerate large directory trees unless required.
- Read the minimum amount of code necessary to establish dependencies and behavior, then expand only when needed.

### Tests and deterministic verification

- During implementation, run the smallest relevant targeted test set first.
- Do not rerun the complete test suite after every minor change.
- Run broader or complete validation at meaningful checkpoints and before declaring the task complete.
- Prefer quiet test output and expand details only for failures.
- Do not reduce required validation quality merely to save tokens.
- Before reporting completion, verify the requested behavior, inspect the relevant final diff, and ensure applicable build/test/type/lint checks pass.
- Never hide or silently ignore failed verification.

### Git and diffs

- Prefer targeted diffs while iterating.
- Avoid repeatedly dumping an unchanged full repository diff.
- Inspect the complete relevant diff before final validation when necessary.
- Do not repeat `git status`, `git diff`, or equivalent commands when their previous result is still valid.

### Context management

- Avoid repeating information already established in the current context.
- Avoid restating long plans, logs, code excerpts, or diagnostics unless they have materially changed.
- Compact or summarize completed investigation phases before moving to a substantially different phase when appropriate.
- Preserve decisions, constraints, unresolved issues, file names, symbols, and validation evidence when compacting.
- Never trade correctness, completeness, or necessary reasoning depth for token savings.
- Prefer repository skills for detailed recurring workflows so their full instructions are loaded only when relevant.

### Hard output limits

- For commands not optimized by RTK and whose output size is unknown, never return unbounded output to the context.
- Limit unknown command output to approximately 4000 bytes initially.
- If additional output is required, inspect another targeted range rather than dumping the complete output.
- For large logs or diagnostics, write the complete output to disk and inspect targeted excerpts.
- These limits must never truncate diagnostic information required to understand a failure; expand selectively when necessary.

### Code Review Graph

- When the current repository has a Code Review Graph index, use CRG to narrow code scope before broad file searches or large reads.
- Always pass the current Git repository root explicitly as `repo_root` to CRG tools; never rely on the MCP server working directory.
- Prefer graph queries for symbol discovery, callers/callees, dependencies, impact analysis, architecture, and review context.
- After narrowing scope with CRG, verify relevant behavior in the actual source and tests before making non-trivial changes.
- Source code is authoritative if the graph is stale, incomplete, or disagrees with the repository.
- If no CRG graph exists for the current repository, fall back normally to targeted search and bounded source reads.
