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

And less of this:

- recursive tree dumps
- entire logs pasted into context
- full test suites after every one-line change
- repeatedly reopening large unchanged files
- giant MCP/tool outputs with no filtering

## A/B test optional layers

For plugins or additional MCPs, compare similar tasks with the layer enabled/disabled.

Measure:

- completion quality
- number of tool calls
- shell-output savings
- source bytes/tokens read
- total elapsed time
- failures caused by missing context

A "token saver" that causes extra retries can be a net loss.
