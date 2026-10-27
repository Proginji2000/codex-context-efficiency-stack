[CmdletBinding()]
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

# Read-only static safety and context-size regression guard.
# Does not invoke Codex, alter user configuration, or measure model tokens.
$ErrorActionPreference = 'Stop'
$policyPath = Join-Path $Root 'templates\AGENTS.md'
if (-not (Test-Path -LiteralPath $policyPath -PathType Leaf)) {
    throw "Missing global policy template: $policyPath"
}

$source = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$baselineCharacters = 19846 # main snapshot immediately before the context audit
$maxCharacters = 14500     # guard rail, not a model token threshold

function Get-Section([string]$Heading, [string]$Text) {
    $escaped = [regex]::Escape($Heading)
    $rx = '(?ms)^### ' + $escaped + '\s*\r?\n(?<body>.*?)(?=^### |\z)'
    $m = [regex]::Match($Text, $rx)
    if (-not $m.Success) {
        throw "Missing policy section: $Heading"
    }
    return $m.Groups['body'].Value
}

function Test-Policy([string]$Text) {
    $clauses = [ordered]@{
        'Model routing and delegation' = @(
            'luna-low','luna-medium','luna-high','terra-medium','terra-high',
            'ui-implementer','sol-high','sol-xhigh','astra-high','sol6-legacy-high',
            'default spawned worker','frontend-design','deterministic'
        )
        'Orchestrator-only contract' = @(
            'Luna parent is an orchestrator only','Delegate all substantive',
            'even for a single non-trivial task','one writer per mutable scope',
            'No silent parent takeover','subagent tools or quota'
        )
        'Subagent lifecycle and saturation recovery' = @(
            'Before each delegation wave','Reuse before spawning','Collect before cleanup',
            'V1 runtime','close_agent','V2 runtime','interrupt_agent',
            'agent thread limit reached','at most once','Never force recovery'
        )
        'Optional specialized workflows' = @(
            'Spec Kit','ui-implementer','Shannon','HatchZip','RTK',
            'Code Review Graph'
        )
        'Automatic project resumption (delegated, bounded)' = @(
            'read-only Luna worker','Get-ProjectResume.ps1','worktrees',
            'project-owned','must not fetch'
        )
        'Conditional tools and quality gates' = @(
            'Playwright MCP','Context7 MCP','Gitleaks','Shannon',
            'untrusted data','worker scope','private code'
        )
        'Quota discipline' = @(
            'API token prices','not','Compare routing'
        )
        'Tests and deterministic verification' = @(
            'test/check','necessary coverage','Never hide'
        )
        'Hard output limits' = @(
            '4000 bytes','Do not truncate'
        )
        'Code Review Graph' = @(
            'repo_root','actual code/tests','stale'
        )
    }

    $failed = @()
    foreach ($heading in $clauses.Keys) {
        $body = Get-Section $heading $Text
        foreach ($fragment in $clauses[$heading]) {
            if ($body.IndexOf($fragment, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
                $failed += ("{0}: missing '{1}'" -f $heading, $fragment)
            }
        }
    }
    return $failed
}

$failures = @(Test-Policy $source)
if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Host "[FAIL] $_" }
    throw 'Required global orchestration, safety or tool guidance is missing.'
}

# Negative fixture guards against an inert test.
$mutated = $source.Replace('No silent parent takeover', 'Parent takeover allowed')
if ($mutated -eq $source -or @(Test-Policy $mutated).Count -eq 0) {
    throw 'Negative orchestrator-only policy fixture unexpectedly passed.'
}

$count = $source.Length
$words = @([regex]::Matches($source, '\S+')).Count
$utf8Bytes = [System.Text.Encoding]::UTF8.GetByteCount($source)
$reduction = 100.0 * ($baselineCharacters - $count) / $baselineCharacters
Write-Host ("[INFO] AGENTS.md: {0} characters, {1} UTF-8 bytes, {2} whitespace words." -f $count, $utf8Bytes, $words)
Write-Host ("[INFO] Previous: {0} characters; static character reduction: {1:N1}%." -f $baselineCharacters, $reduction)

if ($count -ge $baselineCharacters -or $count -gt $maxCharacters) {
    throw "Context budget exceeded: $count chars; guard max $maxCharacters. Review exceptions deliberately."
}

Write-Host '[OK] Core roles, delegation, lifecycle, security and verification rules retained.'
Write-Host '[OK] Negative parent-takeover fixture rejected.'
Write-Host 'PASS: Static context policy audit. Real token/quota and behavior A/B tests remain separate.'
