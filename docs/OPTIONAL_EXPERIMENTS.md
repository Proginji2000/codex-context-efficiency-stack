# Optional experiments after the core stack

The core recommendation is intentionally conservative. Add more layers only after observing a remaining bottleneck.

## External bounded decision models (for example Jev)

A small classifier/decision model can be useful at genuinely ambiguous control boundaries:

- continue vs escalate after conflicting evidence
- whether the blast radius materially expanded
- whether another verification pass is justified when there is no single deterministic answer

Do **not** make it a mandatory hop for every command or trivial task.

Before adding one, compare it against a zero-cost deterministic policy such as:

```text
obvious tiny task -> Luna Low
normal work -> Luna Medium
complex bounded work -> Luna High
security/architecture/migration/repeated failure -> Sol High
```

Keep deterministic facts out of the decision model entirely. Compilation, tests, type checking, lint, formatting and diffs should be established by their real tools.

A typed output or confidence score is still a prediction, not proof. Measure whether the extra decision layer reduces retries/escalations enough to justify its latency, complexity and cost.

## `include_apps_instructions = false`

Codex has a configuration control for whether the `<apps_instructions>` developer block is injected.

Potential benefit:

- lower fixed instruction context in code-only workflows

Potential cost:

- weaker automatic awareness/orchestration of app/plugin capabilities

Recommendation: test this only in a dedicated code-only profile, not as a blind global default.

## Response-shaping plugins (for example Ponytail)

These may reduce overbuilding or code volume, but they also inject their own guidance and can add per-session/subagent context.

Recommendation:

- A/B test on the exact reasoning model you use.
- Do not assume benchmarks from another agent/model transfer directly.

## Additional context proxies / MCPs

Tools that compress logs, documents or arbitrary blobs can be useful if those are still a measured bottleneck.

But every added MCP may contribute:

- tool schemas
- server instructions
- more tool-selection decisions
- additional failure modes

Avoid stacking several tools that solve the same problem.

## Larger model context windows

Do not automatically increase the model context window for "efficiency".

A larger retained history can mean more context is carried forward before compaction. Use larger windows when the task needs them, not as a token-saving technique.
