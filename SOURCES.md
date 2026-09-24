# Upstream references

Checked 24 September 2026.

## OpenAI Codex

- Codex configuration reference (`model`, `model_reasoning_effort`, `agents.*`, custom role config files)  
  https://learn.chatgpt.com/docs/config-file/config-reference

- AGENTS.md custom instructions  
  https://learn.chatgpt.com/docs/agent-configuration/agents-md

- MCP in Codex  
  https://learn.chatgpt.com/docs/extend/mcp

- Codex configuration basics  
  https://learn.chatgpt.com/docs/config-file/config-basic

- Rethinking skills and prompts for GPT-6 Astra: keep `AGENTS.md` current and load task-specific context progressively  
  https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra

- Using skills for open-source software maintenance: repository skills, concise descriptions and deterministic scripts  
  https://developers.openai.com/blog/skills-agents-sdk

- Agents API configuration: model and reasoning configuration can be updated for subsequent session turns  
  https://developers.openai.com/api/docs/guides/agents-api/configuration

- GPT-6 Luna model reference  
  https://developers.openai.com/api/docs/models/gpt-6-luna

- GPT-6 model guidance  
  https://developers.openai.com/api/docs/guides/latest-model

- Reasoning model guidance  
  https://developers.openai.com/api/docs/guides/reasoning

- OpenAI Codex source (`tool_output_token_limit`)  
  https://github.com/openai/codex/blob/main/codex-rs/core/src/config/mod.rs

## RTK

- RTK repository  
  https://github.com/rtk-ai/rtk

- Codex integration notes  
  https://github.com/rtk-ai/rtk/tree/develop/hooks/codex

## Code Review Graph

- CRG repository  
  https://github.com/tirth8205/code-review-graph

- CRG FAQ  
  https://github.com/tirth8205/code-review-graph/blob/main/docs/FAQ.md

- Windows PowerShell hooks discussion  
  https://github.com/tirth8205/code-review-graph/discussions/501

- Codex PostToolUse stdin / broken-pipe issue  
  https://github.com/tirth8205/code-review-graph/issues/493

- Codex existing-runtime / MCP availability discussion  
  https://github.com/tirth8205/code-review-graph/issues/841

## External decision models

External decision models such as Jev are deliberately not required by this repository. If one is added later, pin its API contract and pricing source here, and treat confidence as a routing signal rather than proof of correctness.
