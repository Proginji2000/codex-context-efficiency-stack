[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline = $true)]
    [AllowEmptyString()]
    [string]$JsonLine,
    [switch]$AsJson
)

# Opt-in filter for "codex exec --json" JSONL.
# It intentionally does not save, return or print event bodies, session IDs,
# prompts, command lines, tool output, model reasoning or private code.
# It does not read any Codex session directory or user configuration.
begin {
    $ErrorActionPreference = 'Stop'
    $eventCount = 0
    $completed = 0
    $failed = 0
    $usageTurns = 0
    $missingUsageTurns = 0
    $inputTokens = [long]0
    $cachedInputTokens = [long]0
    $outputTokens = [long]0
    $reasoningOutputTokens = [long]0
    $clock = [System.Diagnostics.Stopwatch]::StartNew()
}
process {
    if ([string]::IsNullOrWhiteSpace($JsonLine)) { return }

    try {
        $event = ConvertFrom-Json -InputObject $JsonLine -ErrorAction Stop
    } catch {
        throw 'Malformed Codex JSONL event (event contents intentionally omitted).'
    }

    $eventCount++
    $eventType = [string]$event.type
    if ($eventType -eq 'turn.failed') {
        $failed++
    } elseif ($eventType -eq 'turn.completed') {
        $completed++
        $usage = $event.usage
        if ($null -eq $usage) {
            $missingUsageTurns++
        } else {
            $usageTurns++
            foreach ($pair in @(
                @('input_tokens', 'inputTokens'),
                @('cached_input_tokens', 'cachedInputTokens'),
                @('output_tokens', 'outputTokens'),
                @('reasoning_output_tokens', 'reasoningOutputTokens')
            )) {
                $field = $pair[0]
                $raw = $usage.$field
                if ($null -eq $raw) { continue }
                $value = [long]0
                if (-not [long]::TryParse([string]$raw, [ref]$value) -or $value -lt 0) {
                    throw 'Invalid token count in completion usage (event contents omitted).'
                }
                switch ($pair[1]) {
                    'inputTokens' { $inputTokens += $value }
                    'cachedInputTokens' { $cachedInputTokens += $value }
                    'outputTokens' { $outputTokens += $value }
                    'reasoningOutputTokens' { $reasoningOutputTokens += $value }
                }
            }
        }
    }
}
end {
    $clock.Stop()
    $summary = [pscustomobject]@{
        source = 'codex exec --json'
        scope = 'noninteractive CLI stream only'
        complete_turns = $completed
        failed_turns = $failed
        turns_with_usage = $usageTurns
        complete_turns_missing_usage = $missingUsageTurns
        input_tokens = $inputTokens
        cached_input_tokens = $cachedInputTokens
        output_tokens = $outputTokens
        reasoning_output_tokens = $reasoningOutputTokens
        processed_events = $eventCount
        stream_processing_elapsed_s = [math]::Round($clock.Elapsed.TotalSeconds, 2)
        token_accounting = 'raw CLI event counters, not subscription quota'
    }

    if ($AsJson) {
        ConvertTo-Json -InputObject $summary -Depth 3
    } else {
        $summary | Format-List | Out-String -Width 140 | Write-Output
    }
}
