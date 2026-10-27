[CmdletBinding()]
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

# Read-only static policy regression test. No Codex agents are spawned or closed.
$ErrorActionPreference = 'Stop'
$policyPath = Join-Path $Root 'templates\AGENTS.md'
if (-not (Test-Path -LiteralPath $policyPath -PathType Leaf)) {
    throw "Missing AGENTS policy template: $policyPath"
}
$source = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8

$sectionPattern = '(?ms)^### Subagent lifecycle and saturation recovery\s*\r?\n(?<body>.*?)(?=^### |\z)'
$sectionMatch = [regex]::Match($source, $sectionPattern)
if (-not $sectionMatch.Success) {
    throw 'Missing dedicated subagent lifecycle section in templates/AGENTS.md.'
}
$body = $sectionMatch.Groups['body'].Value

$checks = [ordered]@{
    'Inspect actual worker status before delegation' = @('Before each delegation wave', 'list_agents')
    'Reuse only compatible reachable workers' = @('Reuse before spawning', 'same compatible scope')
    'Honor concurrency and writer ownership' = @('concurrency cap', 'one-writer-per-scope')
    'Collect worker evidence before cleanup' = @('Collect before cleanup', 'terminal worker report')
    'V1 safe closure is conditional' = @('V1 runtime', 'close_agent', 'after')
    'V2 has no close_agent tool' = @('V2 runtime', 'without', 'close_agent')
    'Interrupt is not a replacement for close' = @('interrupt_agent', 'does not free a thread slot')
    'Bounded retry after saturation' = @('agent thread limit reached', 'at most once', 'capacity change')
    'No dangerous recovery or parent takeover' = @('Never force recovery', 'silently switching Luna')
    'Honest final evidence' = @('Traceability', 'not runtime thread reclamation')
}

function Get-PolicyFailures([string]$Policy) {
    $failures = @()
    foreach ($checkName in $checks.Keys) {
        foreach ($required in $checks[$checkName]) {
            if ($Policy.IndexOf($required, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
                $failures += ("{0}: missing '{1}'" -f $checkName, $required)
            }
        }
    }
    return $failures
}

$failures = @(Get-PolicyFailures $body)
if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Host "[FAIL] $_" }
    throw 'Subagent lifecycle policy regression detected.'
}

# Ensure this new section did not replace the original orchestrator-only policy
# or strip existing UI dispatch / quota routing instructions.
$invariants = @(
    '### Orchestrator-only contract',
    '**No silent parent takeover:**',
    '### Model routing and delegation',
    'ui-implementer',
    'terra-medium',
    'sol-high',
    '### Quota discipline'
)
foreach ($required in $invariants) {
    if ($source.IndexOf($required, [StringComparison]::Ordinal) -lt 0) {
        throw "Required pre-existing stack invariant missing: $required"
    }
}

# Self-test: a deliberately corrupted retry guard must fail the same checks.
$mutated = $body.Replace('at most once', 'unbounded')
if ($mutated -eq $body) {
    throw 'The negative regression fixture did not change the policy.'
}
if (@(Get-PolicyFailures $mutated).Count -eq 0) {
    throw 'Negative regression fixture unexpectedly passed.'
}

Write-Host '[OK] V1/V2 agent lifecycle, bounded recovery and existing orchestration invariants.'
Write-Host '[OK] Negative regression fixture correctly rejected.'
Write-Host 'PASS: Static subagent lifecycle policy checks passed (no runtime agents used).'
