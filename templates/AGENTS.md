@RTK.md

## Global context and token efficiency

Preserve model quality and reasoning depth while minimizing unnecessary context and token usage.

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

### Tests

- During implementation, run the smallest relevant targeted test set first.
- Do not rerun the complete test suite after every minor change.
- Run broader or complete validation at meaningful checkpoints and before declaring the task complete.
- Prefer quiet test output and expand details only for failures.
- Do not reduce required validation quality merely to save tokens.

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
