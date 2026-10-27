# Opt-in Codex CLI JSONL usage — without reading saved chats

Codex CLI noninteractive `codex exec --json` emits a JSON Lines event stream. On completed turns, the event often includes `usage.input_tokens`, `usage.cached_input_tokens`, `usage.output_tokens`, and `usage.reasoning_output_tokens`.

Source: https://learn.chatgpt.com/docs/non-interactive-mode

## Local, permission-preserving collection

`scripts/Convert-CodexExecUsage.ps1` filters a **new, explicitly initiated CLI execution**. It accepts JSONL through the PowerShell pipeline and emits *only aggregated counters*. It does not read `~/.codex` histories or user config, persist the raw event stream, print prompt contents, commands, reasoning, tool output or conversation/thread IDs. It does parse each JSON event transiently in memory; run it only on your own authorized tasks. The report is kept in memory until explicitly saved by you.

Example from an approved, **non-sensitive test repository**:

```powershell
# Invoke only in a safe directory you control. This demonstration does not modify files.
codex exec --json --sandbox read-only "Delegate a read-only worker to report the branch and current HEAD, then finish." |
    .\scripts\Convert-CodexExecUsage.ps1 -AsJson
```

The preceding example assumes you are in the stack checkout; if running from another working directory, replace the relative path with the full path to `Convert-CodexExecUsage.ps1`. `codex exec` is a **new invocation**, not a measurement of an already-running Desktop/TUI conversation. Its regular tool and network permissions remain subject to the CLI's normal runtime restrictions. Do not use `--yolo` or elevate permissions for measurement.

On Windows, **do not use** `2>&1` before the filter: it only accepts JSONL from stdout. Standard error remains visible separately, so errors are not silently suppressed. The CLI command itself can still require authentication; this filter never installs or configures Codex.

For synthetic tests without invoking Codex:

```powershell
.\scripts\Test-CodexExecUsage.ps1
```

## Data contract

Example sanitized report:

```json
{
  "source": "codex exec --json",
  "scope": "noninteractive CLI stream only",
  "complete_turns": 1,
  "failed_turns": 0,
  "turns_with_usage": 1,
  "complete_turns_missing_usage": 0,
  "input_tokens": 120,
  "cached_input_tokens": 60,
  "output_tokens": 25,
  "reasoning_output_tokens": 4,
  "processed_events": 4,
  "stream_processing_elapsed_s": 0.1,
  "token_accounting": "raw CLI event counters, not subscription quota"
}
```

This is an *illustrative synthetic example*, not a real usage measurement. Token counters cover the emitted turns, not necessarily the sum of each delegated model's private metering or all subscription activity; one `turn.completed` event can lack `usage`, in which case the report flags it rather than claiming zero usage. `stream_processing_elapsed_s` measures pipeline processing, not full task latency. For actual elapsed task time, use an external clock or a separately instrumented wrapper.

**Not measured:** Codex Desktop usage, historical TUI sessions, subscription credits/quota, per-worker accounting, first-pass quality or retry classification. See [task-level outcome metrics](MEASUREMENT.md#optional-csv-metrics-aggregation-codex-cli-0164) for the separate, explicit CSV assessment.

## Data protection boundaries

- No background monitoring, OTel exporter, network endpoint, session-log scraping, global configuration changes, raw event files or telemetry uploads.
- Treat the code/prompt in the newly initiated test as sensitive even though the **filtered output** omits it. Codex still processes the original prompt and the tool chain remains subject to normal security controls.
- Do not pipe arbitrary private transcripts or unknown non-Codex JSON into this filter.
- Run in an isolated, approved test checkout, not in a sensitive in-progress worktree.
- The filter is not a security boundary against malicious/compromised process behavior; its safety is its narrow data handling and the user's explicit opt-in.
