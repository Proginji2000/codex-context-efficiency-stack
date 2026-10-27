# GPT-6.1 Terra stack update — 27 October 2026

GPT-6.1 Terra was released on 26 October 2026 for Plus, Pro, Enterprise and Edu users in ChatGPT Work and Codex, and as `gpt-6.1-terra` in the API.

## Decision for this stack

Adopt Terra as an **intermediate capability tier**:

```text
Luna  -> routine / high-volume / cheapest
Terra -> scoped code fixes / everyday agentic work / visual & computer use
Sol   -> complex coding / architecture / security / risky changes
Astra -> exceptional final escalation
```

Default spawned work remains Luna Medium.

## Why

Terra's standard API pricing is $1/M input, $0.05/M cached input and $5/M output: 10x Luna's input/output price but half Sol's. OpenAI also states that the same Work/Codex allowance covers substantially more tasks with Terra than with Sol or Astra.

That makes Terra useful when a Luna attempt is likely to cause retries but Sol is unnecessary.

## New lanes

- `terra-medium`: scoped fixes, everyday agentic coding, visual/UI/computer-use.
- `terra-high`: difficult but bounded work before Sol.

No default Terra XHigh/Max lane is added because OpenAI continues to recommend Sol/Astra for the most complex coding tasks.

## Other October changes

- Decisions API became generally available on 22 October; tracked for future routing work but not used in the subscription stack because API usage is separately billed.
- Codex stable 0.164.0 adds reusable prompt presets and richer inline `/model` and `/permissions` controls. These improve ergonomics but do not require a routing-policy change.
- 12-hour API prompt caching is available, but it does not change included Work/Codex subscription accounting and is therefore not used as a routing assumption.
