# Upstream references

Checked 27 October 2026.

## OpenAI Codex / model routing

- GPT-6.1 Terra announcement: availability, coding/computer-use positioning, and Work/Codex allowance guidance  
  https://openai.com/index/introducing-gpt-6-1-terra/

- GPT-6.1 Terra model reference: reasoning through max; $1/M input, $0.05/M cached input, $5/M output  
  https://developers.openai.com/api/docs/models/gpt-6.1-terra

- OpenAI model-selection guide: Luna for scoped/high-volume work, Terra for scoped code fixes/computer use, Sol for complex projects, Astra for frontier work  
  https://developers.openai.com/api/docs/guides/model-selection

- Codex subagents: current local clients delegate after direct requests or applicable AGENTS.md/skill instructions  
  https://learn.chatgpt.com/docs/agent-configuration/subagents

- Codex 0.164.0 release notes: presets and richer inline /model and /permissions controls  
  https://github.com/openai/codex/releases


- DevDay 2026 recap: GPT-6.1 Sol, Ultrafast, Codex cloud environments, refreshed CLI `/agents`, Code Review, Security Cloud, Decisions API and Agents API updates  
  https://openai.com/index/devday-2026-recap/

- GPT-6.1 Sol announcement, benchmarks, pricing and availability  
  https://openai.com/index/introducing-gpt-6-1-sol/

- GPT-6.1 Sol API model reference (`low`, `medium`, `high`, `xhigh`, `max`; $2/M input, $0.10/M cached input, $10/M output)  
  https://developers.openai.com/api/docs/models/gpt-6.1-sol

- GPT-6 Sol model reference and pricing baseline  
  https://developers.openai.com/api/docs/models/gpt-6-sol

- Codex configuration reference (`model`, `model_reasoning_effort`, `agents.*`, custom role config files)  
  https://learn.chatgpt.com/docs/config-file/config-reference

- AGENTS.md custom instructions  
  https://learn.chatgpt.com/docs/agent-configuration/agents-md

- MCP in Codex  
  https://learn.chatgpt.com/docs/extend/mcp

- Codex configuration basics  
  https://learn.chatgpt.com/docs/config-file/config-basic

- Agents API configuration and durable managed-agent sessions  
  https://developers.openai.com/api/docs/guides/agents-api/configuration

- GPT-6 model guidance  
  https://developers.openai.com/api/docs/guides/latest-model

- OpenAI Help: Codex subscription usage depends on model, execution environment, task complexity, context, reasoning, speed and tools  
  https://help.openai.com/fr-fr/articles/11369540-using-codex-with-your-chatgpt-plan

- OpenAI Codex source (`tool_output_token_limit`)  
  https://github.com/openai/codex/blob/main/codex-rs/core/src/config/mod.rs

## Anthropic Claude Code

- Model aliases, model selection, effort levels and auto-compaction  
  https://code.claude.com/docs/en/model-config

- Custom subagents, per-agent model/effort and isolated contexts  
  https://code.claude.com/docs/en/sub-agents

- Settings files and precedence  
  https://code.claude.com/docs/en/settings

- CLAUDE.md / AGENTS.md, imports, progressive disclosure and path-scoped rules  
  https://code.claude.com/docs/en/memory

## RTK

- RTK repository  
  https://github.com/rtk-ai/rtk

- Codex integration  
  https://github.com/rtk-ai/rtk/tree/develop/hooks/codex

- Claude Code integration  
  https://github.com/rtk-ai/rtk/tree/develop/hooks/claude

## Code Review Graph

- CRG repository  
  https://github.com/tirth8205/code-review-graph

- CRG usage and platform installation  
  https://github.com/tirth8205/code-review-graph/blob/main/docs/USAGE.md

- CRG FAQ  
  https://github.com/tirth8205/code-review-graph/blob/main/docs/FAQ.md

## External decision models

External decision models such as Jev remain optional. If one is added later, pin its API contract and pricing source here, keep its input bounded, and treat confidence as a routing signal rather than proof of correctness. The Decisions API is now GA and remains a candidate for bounded classification, but API calls are billed separately from Work/Codex subscription usage.


## Optional tools and skill provenance (reviewed 27 October 2026)

- GitHub Spec Kit, official upstream and Codex integration:
  https://github.com/github/spec-kit
  https://github.com/github/spec-kit/blob/main/docs/integrations/codex.md
  https://github.com/github/spec-kit/blob/main/docs/installation.md

- Anthropic frontend-design skill; Apache License 2.0, skill + license copied unchanged into this repository:
  https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
  https://github.com/anthropics/skills/blob/main/skills/frontend-design/LICENSE.txt
  Upstream Git blob SHA-1 of SKILL.md: `a5333457c414d20d625f307df945842c0952ecc3`
  Upstream Git blob SHA-1 of LICENSE.txt: `f433b1a53f5b830a205fd2df78e2b34974656c7b`

- Codex official skill discovery locations and user-wide `$HOME/.agents/skills`:
  https://learn.chatgpt.com/docs/build-skills

- Keygraph Shannon active authorized-only penetration testing, Pi/Codex subscription path, AGPL-3.0:
  https://github.com/KeygraphHQ/shannon
  https://github.com/KeygraphHQ/shannon/blob/main/docs/ai-providers.md

- HatchZip in-place archive extraction and original archive consumption:
  https://hatchzip.dev/
  https://github.com/xevrion/hatchzip

- Optional tool assessment, installation and safeguards:
  docs/OPTIONAL_INTEGRATIONS.md
