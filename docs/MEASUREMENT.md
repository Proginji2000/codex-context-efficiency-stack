# Measuring whether the stack helps

Do not judge the setup from installation alone. Measure it on real agentic development work.

## RTK

After a normal Codex session:

```powershell
rtk gain
```

Interpret this as savings on **RTK-processed command output**, not total model/context usage.

## CRG

Check graph size:

```powershell
code-review-graph status
```

For a change-aware review:

```powershell
code-review-graph detect-changes --brief
```

Current CRG versions can print an estimated context-savings panel comparing raw changed-file context with graph context.

## Repository hygiene metric

In a Git repository:

```powershell
git ls-files | Measure-Object
```

Compare that with:

```powershell
code-review-graph status
```

If CRG is indexing huge generated/vendor/runtime areas, fix Git tracking and/or `.code-review-graphignore` before adding another optimizer.

## Model-routing metrics

For the optional Luna/Sol routing layer, record real tasks rather than estimating the distribution in advance.

At minimum track:

- task identifier
- selected lane (`luna-low`, `luna-medium`, `luna-high`, `sol-high`)
- task category
- whether the first implementation passed verification
- number of retries
- whether escalation occurred
- final lane that completed the task
- relevant deterministic checks
- elapsed time
- quota/token/cost information when the client exposes it

A compact CSV shape is enough:

```text
date,task,lane_initial,retries,escalated,lane_final,verification,result,elapsed_s
```

Useful derived metrics:

```text
first-pass success rate by lane
escalation rate
retry rate
Sol share of completed tasks
failed-verification rate
median elapsed time by lane
successful tasks per unit of quota/cost
```

Do not optimize for the lowest Sol percentage by itself. If overly aggressive Luna routing causes repeated retries, the system may consume more quota and more wall-clock time overall.

## Escalation-quality check

Review escalations periodically.

For each Sol escalation, ask:

- Did deterministic evidence actually justify escalation?
- Could Luna High have completed it with one more well-targeted attempt?
- Did the task become security-sensitive, architectural, migration-heavy or broadly uncertain?
- Was Sol used merely as a reviewer even though tests/build/diff had already established completion?

Also review tasks that stayed on Luna but required many retries. Those may indicate that the routing threshold is too aggressive in the other direction.

## Qualitative checklist

A successful setup should produce more of this:

- targeted graph queries before large reads
- small source ranges instead of whole-file dumps
- targeted tests during iteration
- quiet test output, detailed failures only
- targeted diffs during iteration
- complete relevant validation before completion
- fewer repeated reads of unchanged code
- fewer repeated `git status`/`git diff` calls
- large raw logs written to disk and sampled selectively
- subagents receiving bounded task-specific context
- Luna handling routine work without unnecessary Sol review
- Sol appearing mainly at real architectural/risk/failure boundaries

And less of this:

- recursive tree dumps
- entire logs pasted into context
- full test suites after every one-line change
- repeatedly reopening large unchanged files
- giant MCP/tool outputs with no filtering
- spawning a routing/reviewer agent after every tiny action
- escalating solely because a stronger model is available

## A/B test optional layers

For plugins, decision models or additional MCPs, compare similar tasks with the layer enabled/disabled.

Measure:

- completion quality
- number of tool calls
- shell-output savings
- source bytes/tokens read
- total elapsed time
- retries and escalations
- failures caused by missing context

A "token saver" that causes extra retries can be a net loss. A routing model that adds latency to obvious decisions can also be a net loss.
