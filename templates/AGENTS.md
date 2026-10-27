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


### Orchestrator-only contract

- **The parent is a dispatcher and integrator, not an execution worker.** For every actionable engineering task requiring repository exploration, research, implementation, tests, debugging, review, or documentation changes, delegate the substantive work to at least one appropriately scoped subagent. This applies even if the request contains only one non-trivial task.
- **Before doing task work**, identify requested outcomes, dependencies, write ownership, acceptance checks, and suitable specialist lanes. Keep the task graph proportional to the request; do not split dependent micro-steps into unnecessary agents.
- For multiple independent non-trivial workstreams, delegate them concurrently up to the configured cap. For dependent workstreams, delegate sequentially, passing concise verified outputs and acceptance criteria to the next worker.
- The parent may perform only orchestration overhead: classify and route tasks, spawn/message/wait for agents, establish non-mutating repository/worktree status if needed for ownership, compare returned evidence, request corrections, decide acceptance, and report the result. **Do not have the parent perform substantive source analysis, edit source/docs/config, execute tests/builds, or run reviews as a substitute for a worker.**
- Assign narrow work to the lowest sufficient worker model. Match specialized roles to code, tests, docs, risk, security, and other requested activities. Delegating does not mean escalating model strength.
- Every subagent assignment must include outcome, constraints, permitted files/scope, known context, verification criteria, and the required concise report. Do not delegate a raw full conversation when a bounded brief suffices.
- Keep one writer per mutable scope. Parallel read-only work is preferred; use separate worktrees for genuinely independent concurrent writers. A reviewer should not self-approve its own critical implementation.
- Collect concrete worker evidence (files changed, tests run and outcomes, blockers). If evidence is missing or conflicting, ask a worker to investigate or rerun checks. The parent synthesizes and verifies *the evidence chain*, not by redoing the work itself.
- Report the worker role(s) used and the returned verification result. Do not claim delegation occurred unless a subagent was actually started and returned evidence.
- **No silent parent takeover:** if subagent tools are missing, disabled, blocked, or quota-exhausted, state that execution is blocked and request an explicit change of mode. Do not silently work around the missing delegation by doing the implementation in the parent.
- Only pure conversation, a simple clarification/approval, and task-routing/administrative operations require no worker. For any actionable file/code/research task, delegate even when spawning one worker adds overhead. The user's preference is orchestrator-only rather than mandatory minimum-token fan-out.
- These are instruction-level rules, not a technical access-control boundary. Real enforcement requires a dispatch wrapper/harness or tool permissions; validate observed behavior through subagent activity, not by checking AGENTS.md alone.

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
