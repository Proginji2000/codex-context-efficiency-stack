# Documentation index

Start here when installing, updating, troubleshooting or extending the Codex Context-Efficiency Stack.

## Choose by goal

| Goal | Read |
| --- | --- |
| Install/update on Windows | [English README](../README.md) · [Guide français](../README.fr.md) |
| Understand the Luna/Terra/Sol/Astra routing and orchestration-only parent | [Model Routing v4](MODEL_ROUTING_V4.md) |
| Adopt the stack gradually without disturbing a running project | [Safe staged rollout](SAFE_STAGED_ROLLOUT.md) |
| Understand the October Terra addition | [GPT-6.1 Terra update](TERRA_6_1_UPDATE.md) |
| Add Spec Kit / frontend-design, consider Shannon or HatchZip | [Optional integrations](OPTIONAL_INTEGRATIONS.md) |
| Resume long autonomous sessions without context replay | [Long-running tasks](LONG_RUNNING_TASKS.md) · [Existing sessions](EXISTING_SESSIONS.md) |
| Measure quotas, retries and completed work | [Measurement](MEASUREMENT.md) |
| Troubleshoot Codex and PowerShell on Windows | [Windows troubleshooting](WINDOWS_TROUBLESHOOTING.md) |
| Review the Claude Pro layer | [Claude Pro stack](CLAUDE_PRO_STACK.md) · [Claude Pro quick start](../CLAUDE_PRO.md) |
| Review older release decisions | [DevDay 2026](DEVDAY_2026_UPDATE.md) · [Optional experiments](OPTIONAL_EXPERIMENTS.md) |
| Verify upstream documentation | [Sources](../SOURCES.md) |

## Automatic visual UI dispatch

After the global stack update and one-time `install-frontend-design.ps1` installation, Luna routes substantive UI/frontend work to the `ui-implementer` Terra Medium worker. The worker is configured to use `frontend-design` implicitly when available; the user does not need to mention the skill. See [integration details](OPTIONAL_INTEGRATIONS.md#automatic-frontend-design-dispatch).

## Global context budget

The [27 October 2026 global AGENTS audit](CONTEXT_AUDIT_20261027.md) documents the static instruction reduction, preserved worker-only constraints and a controlled runtime A/B validation plan. `scripts/Test-GlobalContextPolicy.ps1` protects essential global routing and safety clauses in Windows CI.

## Multi-agent lifecycle and saturated threads

[Subagent lifecycle, V1/V2 cleanup and safe recovery](MODEL_ROUTING_V4.md#subagent-lifecycle-version-aware-operational-policy) documents bounded worker reuse, result collection and thread-limit handling. `scripts/Test-SubagentLifecyclePolicy.ps1` statically guards the instructions in Windows CI, without spawning workers.

## Project continuation and developer checks

[Project resume, Playwright MCP, Context7 and Gitleaks](DEVELOPER_EXTENSIONS.md) describes the read-only handoff, optional Windows MCP registration, local secret scan and acceptance tests. Shannon remains paused and no application scan is started by these tools.

## Required vs. opt-in

**Default foundation:** global routing config, orchestrator-only `AGENTS.md`, RTK where installed, Code Review Graph where indexed, and deterministic tests/checks.

**Task-triggered extensions:**
- [Anthropic frontend-design skill](../.agents/skills/frontend-design/SKILL.md): included in this repository, optional user-wide installer `scripts/install-frontend-design.ps1`.
- GitHub Spec Kit: install into a specific project only when a specification-driven workflow is warranted.
- Keygraph Shannon: authorized, isolated staging pentesting only; never default.
- HatchZip: manual recovery of disk space during archive extraction; never use automatically on retained evidence.

The global update script **does not install Spec Kit, Shannon, or HatchZip** and does not automatically activate the frontend-design skill outside this repository.

## First checks

From the cloned stack on Windows PowerShell:

```powershell
cd C:\Dev\codex-context-efficiency-stack
.\scripts\verify-stack.ps1
.\scripts\verify-staged-profile.ps1
```

Static verifiers check file contents/role references. They do not prove live model availability, worker delegation, skill invocation, or third-party tool behavior. Confirm those separately using an isolated representative task.

## Legacy route

[MODEL_ROUTING_V2.md](MODEL_ROUTING_V2.md) is maintained as a compatibility pointer. The active routing guide is [V4](MODEL_ROUTING_V4.md).
