# OpenAI DevDay 2026 impact on this stack

Checked 29 September 2026.

## Adopted now

### GPT-6.1 Sol

Normal strong escalation now uses `gpt-6.1-sol` instead of `gpt-6-sol`.

OpenAI states that GPT-6.1 Sol is available to Plus, Pro, Business, Enterprise and Edu users in Codex and Work, and through the API as `gpt-6.1-sol`. Standard API prices are $2/M input, $0.10/M cached input and $10/M output. The previous GPT-6 Sol cached-input price is $0.20/M.

Because subscription quota accounting depends on model, task, context, reasoning and tools, the repository retains `sol6-legacy-high` for controlled A/B measurement rather than assuming API price equals subscription burn.

### New escalation ladder

```text
Luna Low / Medium / High
    -> GPT-6.1 Sol High
    -> GPT-6.1 Sol XHigh
    -> Astra High
```

Astra remains a final escalation rather than a routine reviewer.

### `/agents`

The refreshed Codex CLI includes a new `/agents` view for delegating and tracking multiple tasks. This is operationally useful with the stack's default concurrency cap of 2, but it requires no special stack configuration.

## Not made core dependencies

### GPT-6.1 Sol Ultrafast

Coming soon. It targets speed (up to 8x faster token generation in Codex), not endurance. It is therefore excluded from the default quota-efficient route.

### Decisions API

Potentially useful later for bounded task classification/model routing. At DevDay it launched in limited preview, so the core stack remains deterministic and does not depend on it.

### Reusable Codex cloud environments

Useful for remote/cloud workflows and shared approved environments. The current repository remains focused on local Windows context efficiency; cloud-specific orchestration can be layered later.

### Code Review / Codex Security Cloud

Useful complementary review/security surfaces. They do not justify automatically duplicating every local verification pass.

## Project inheritance

Global `~/.codex/AGENTS.md` applies broadly, while repository-local `AGENTS.md` adds project instructions. Repository-local `.codex/config.toml` or project-specific role files can shadow global model-routing settings. Use `scripts/audit-project-inheritance.ps1` inside a project before assuming the new GPT-6.1 Sol routing is inherited unchanged.
