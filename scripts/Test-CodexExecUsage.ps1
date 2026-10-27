[CmdletBinding()]
param()

# Synthetic JSONL regression; real conversation files are not accessed.
$ErrorActionPreference = 'Stop'
$filter = Join-Path $PSScriptRoot 'Convert-CodexExecUsage.ps1'
if (-not (Test-Path -LiteralPath $filter -PathType Leaf)) {
    throw 'Missing Codex usage filter.'
}

$fixture = @(
    '{"type":"thread.started","thread_id":"PRIVATE_THREAD_MARKER"}'
    '{"type":"item.completed","item":{"type":"agent_message","text":"PRIVATE_PROMPT_AND_SOURCE_MARKER"}}'
    '{"type":"turn.started"}'
    '{"type":"turn.completed","usage":{"input_tokens":120,"cached_input_tokens":60,"output_tokens":25,"reasoning_output_tokens":4}}'
    '{"type":"turn.failed","error":{"message":"PRIVATE_ERROR_MARKER"}}'
    '{"type":"turn.completed","usage":{"input_tokens":30,"cached_input_tokens":10,"output_tokens":7,"reasoning_output_tokens":2}}'
    '{"type":"turn.completed"}'
)
$raw = ($fixture | & $filter -AsJson | Out-String)
$summary = $raw | ConvertFrom-Json

if ($summary.complete_turns -ne 3 -or $summary.failed_turns -ne 1 -or
    $summary.turns_with_usage -ne 2 -or $summary.complete_turns_missing_usage -ne 1 -or
    $summary.input_tokens -ne 150 -or $summary.cached_input_tokens -ne 70 -or
    $summary.output_tokens -ne 32 -or $summary.reasoning_output_tokens -ne 6 -or
    $summary.processed_events -ne 7) {
    throw 'Unexpected filtered token or turn counters.'
}
foreach ($sentinel in @('PRIVATE_THREAD_MARKER','PRIVATE_PROMPT_AND_SOURCE_MARKER','PRIVATE_ERROR_MARKER')) {
    if ($raw.Contains($sentinel)) {
        throw 'An event body was exposed in the sanitized summary.'
    }
}

$rejected = $false
try {
    $null = @('this is not valid JSON and contains PRIVATE_CONTENT') | & $filter -AsJson | Out-String
} catch {
    $rejected = $true
    if ($_.ToString().Contains('PRIVATE_CONTENT')) {
        throw 'A malformed input event was echoed into an error.'
    }
}
if (-not $rejected) { throw 'Malformed JSON was not rejected.' }

Write-Host '[OK] Multiple turn counters, missing usage and non-persistence of private event fields.'
Write-Host '[OK] Malformed input is rejected without echoing the event.'
Write-Host 'PASS: Synthetic Codex exec JSONL usage filter tests.'
