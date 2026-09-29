# Model Routing v3 (DevDay 2026 refresh): Luna-first, GPT-6.1 Sol escalation

This layer keeps the original context-efficiency design but updates the strong-model path after OpenAI DevDay on 29 September 2026.

Core rules:

1. Use deterministic software for facts.
2. Use the cheapest sufficient lane for generation.
3. Escalate only when evidence justifies it.
4. Keep context bounded with targeted reads, concise tool output, skills and subagents.
5. Preserve subscription quota by inserting GPT-6.1 Sol High and XHigh before Astra.

## Why GPT-6.1 Sol replaces GPT-6 Sol in the normal path

OpenAI describes GPT-6.1 Sol as a major upgrade to GPT-6 Sol for agentic coding, computer use and professional work. Its standard API input/output prices remain $2/$10 per million tokens, while cached input falls from $0.20 to $0.10. OpenAI reports GPT-6.1 Sol exceeding GPT-6 Sol's best DeepSWE v1.1 score by 6.4 percentage points at lower reasoning effort and cost.

API pricing is not a direct measurement of ChatGPT Plus/Pro subscription quota burn. Therefore this stack keeps a `sol6-legacy-high` lane only for controlled A/B measurements while routing normal strong work to GPT-6.1 Sol.

## Lanes

| Lane | Model | Reasoning | Intended work |
| --- | --- | --- | --- |
| `luna-low` | `gpt-6-luna` | `low` | tiny mechanical work |
| `luna-medium` | `gpt-6-luna` | `medium` | normal development, tests, localized bugs |
| `luna-high` | `gpt-6-luna` | `high` | complex but bounded debugging/refactors |
| `sol-high` | `gpt-6.1-sol` | `high` | architecture, security-sensitive changes, risky migrations, repeated Luna failure |
| `sol-xhigh` | `gpt-6.1-sol` | `xhigh` | very hard bounded work after Sol High remains unresolved |
| `astra-high` | `gpt-6-astra` | `high` | exceptional end-to-end difficulty / unresolved Sol XHigh |
| `sol6-legacy-high` | `gpt-6-sol` | `high` | A/B quota/performance measurement or compatibility fallback only |

## Recommended escalation

```text
Luna Medium
  -> deterministic checks
  -> localized failure: one retry
  -> deterministic checks
  -> Luna High
  -> deterministic checks
  -> unresolved/high-risk: GPT-6.1 Sol High
  -> deterministic checks
  -> still unresolved but bounded: GPT-6.1 Sol XHigh
  -> deterministic checks
  -> exceptional end-to-end difficulty only: Astra High
```

The extra Sol XHigh step is deliberate: GPT-6.1 Sol is positioned much closer to Astra than GPT-6 Sol was, while Astra remains substantially more expensive in API terms. Subscription quota behavior must still be measured empirically.

## GPT-6 Sol legacy benchmark lane

Use `sol6-legacy-high` only when explicitly testing whether GPT-6.1 Sol is more quota-efficient on the user's subscription. Keep the paired tasks comparable:

- same repository and similar scope
- similar context size
- same reasoning effort where possible
- same verification gate
- record quota before/after when visible
- record retries, wall-clock time and pass/fail outcome

Do not make the legacy lane part of normal automatic routing.

## DevDay Codex features relevant to this stack

- `/agents` improves visibility into delegated work and is useful with the stack's conservative concurrency policy.
- Reusable Codex cloud environments are valuable for remote/cloud workflows, but they do not replace the local Windows routing layer.
- The new Code Review experience and Codex Security Cloud are complementary product surfaces, not reasons to duplicate routine reviews locally.
- Decisions API is promising for future routing/classification, but it launched in limited preview; it is not a mandatory dependency of this stack.
- GPT-6.1 Sol Ultrafast is intentionally not part of the endurance route. It is a speed tier, not a quota-saving mechanism.

## Completion gate

A task is complete only when the requested behavior is implemented, relevant deterministic checks pass, the final diff matches scope, and no known failure is hidden. Use model judgment to interpret ambiguity, not to replace compiler/tests/type/lint/diff evidence.

## Context efficiency

Keep the original rules: search before broad reads, use CRG when it materially narrows scope, bound tool output, avoid repeated unchanged reads, use narrow subagent context, and compact completed investigation phases.

## External decision models

Jev or another bounded decision model remains optional. It can classify genuinely ambiguous task boundaries, but the deterministic scheduler should retain authority over quota, cooldowns, retries, provider availability and hard safety/verification rules.
