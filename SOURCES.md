# Upstream references

Checked 29 September 2026 after OpenAI DevDay 2026.

## OpenAI Codex / DevDay 2026

- DevDay 2026 recap: GPT-6.1 Sol, Ultrafast, Codex cloud environments, refreshed CLI `/agents`, Code Review, Security Cloud, Decisions API and Agents API updates  
  https://openai.com/index/devday-2026-recap/

- GPT-6.1 Sol announcement, benchmarks, pricing and availability  
  https://openai.com/index/introducing-gpt-6-1-sol/

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

External decision models such as Jev remain optional. If one is added later, pin its API contract and pricing source here, keep its input bounded, and treat confidence as a routing signal rather than proof of correctness. The DevDay Decisions API may become another bounded classifier/routing option after broad availability and evaluation.
