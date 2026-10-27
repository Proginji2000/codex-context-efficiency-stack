@RTK.md

## Global context and token efficiency

Preserve correctness while minimizing unnecessary context, tool-output tokens, repeated work, and unnecessary model escalation.

### Model routing and delegation

- Use the lowest sufficient lane at meaningful task boundaries.
- `luna-low`: tiny mechanical low-risk work.
- `luna-medium`: default routine/high-volume development, tests, exploration, triage, and localized fixes.
- `luna-high`: cost-first deeper reasoning on bounded work when Luna remains sufficient.
- `terra-medium`: scoped code fixes, everyday agentic coding, visual/UI work, and bounded computer-use tasks with clear acceptance criteria.
- `terra-high`: difficult but still bounded implementation/debugging, visual reasoning, or computer-use work before Sol escalation.
- `sol-high`: complex coding, architecture, security-sensitive changes, risky migrations, broad cross-module uncertainty, or repeated Luna/Terra failure.
- `sol-xhigh`: a deeper GPT-6.1 Sol pass when Sol High remains unresolved.
- `astra-high`: final escalation for exceptional end-to-end difficulty.
- Prefer `luna-medium` as the default spawned worker. Terra is an intermediate capability tier, not a new default.
- GPT-6 Sol is legacy in this stack. Use `sol6-legacy-high` only for explicit A/B quota/performance measurement, regression investigation, or temporary compatibility fallback.
- Route by task shape, not by a rigid ladder. A scoped code/UI/computer-use task may go directly from Luna to Terra; architecture/security/high-risk work may go directly to Sol.
- Do not spawn or switch lanes after every read, command, edit, or test. Route at task boundaries, after a materially different phase begins, or when verification evidence justifies escalation.
- Never use another model to answer a fact that deterministic tooling can establish. Run the compiler, tests, type checker, linter, formatter/checker, `git diff`, or other authoritative tool instead.
- A localized failure does not automatically require escalation. Retry the same cheap lane once when the corrective path is clear. Prefer Terra for a scoped task that needs stronger agentic/tool/visual capability; prefer Sol when the uncertainty becomes complex, broad, architectural, security-sensitive, or high-risk.
- Give subagents bounded context: goal, constraints, relevant files/symbols, known evidence, and acceptance criteria. Do not copy the entire parent conversation unless it is genuinely required.
- Avoid parallel agents that perform substantially overlapping exploration. Parallelism is useful only when branches of work are independent.
- Keep the default concurrency conservative for subscription endurance. Use the `/agents` view when available to monitor delegated work rather than spawning redundant workers.


### Orchestration first

- On a multi-part prompt or a broad task, first identify independent workstreams before doing deep implementation/reasoning in the parent thread.
- If two or more meaningful workstreams are independent enough to run without conflicting writes, delegate them. Typical candidates are repository exploration, documentation research, test/diagnostic work, independent review, and separate implementation scopes.
- The parent thread is primarily the orchestrator for delegated work: define scopes, choose lanes, preserve dependencies, wait for results, synthesize evidence, and own final acceptance. Do not duplicate a delegated investigation unless its evidence is insufficient.
- Keep short, tightly dependent sequential steps in the parent when delegation would add more handoff cost than value.
- Prefer read-only parallelism. For writes, assign one writer per file/scope or use isolated worktrees; never allow competing agents to edit the same mutable scope concurrently.
- For prompts containing several distinct requested tasks, delegate each independent non-trivial task up to the concurrency cap instead of solving the whole prompt serially in the parent.
- Delegation is not optional merely because the parent model can reason through the task. If decomposition materially improves context isolation, specialization, validation, or wall-clock time, use subagents.
- Avoid quota-amplifying fan-out: do not spawn agents for trivial subtasks, overlapping exploration, or dependent micro-steps.

### Quota discipline

- Optimize for successful engineering work per unit of quota, not maximum model strength per task.
- Keep routine/high-volume work on Luna.
- Use Terra when its extra capability is likely to avoid retries while the task remains scoped; do not promote routine Luna work to Terra merely because Terra is available.
- Use Sol/Astra only when task complexity or evidence justifies them.
- OpenAI states that GPT-6.1 Terra allows substantially more Work/Codex tasks per allowance than GPT-6.1 Sol or GPT-6 Astra, but no exact Terra-vs-Luna subscription multiplier is assumed here.
- API price is not subscription quota accounting. Terra is $1/$5 per million standard API input/output tokens, versus Luna $0.10/$0.50 and Sol $2/$10; use these only as relative cost signals, not as quota formulas.
- When quota information is visible, treat it as a routing signal, not as proof that a stronger model is required.
- Do not burn quota on duplicate reviews when deterministic verification already establishes correctness.
- When comparing model lanes, keep scope/context/effort comparable and record quota/latency/retry evidence.

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

### Durable task state

- For long-running, multi-milestone, interruption-prone, or multi-agent work, maintain one concise durable task-state file so a fresh session can resume without replaying the full conversation.
- Do not create or maintain task-state files for trivial edits or short self-contained tasks.
- Update durable state only at meaningful milestones, decisions, failures, handoffs, and verification checkpoints; never after every command.
- Keep only the current goal, definition of done, constraints, key decisions, relevant files/symbols, verification evidence, unresolved issues, and next action.
- Source code, tests, build output, and Git remain authoritative. The state file is a compact resume index, not a replacement for deterministic evidence.

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
