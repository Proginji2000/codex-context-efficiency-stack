$ErrorActionPreference = 'Continue'

Write-Host '=== Codex Context-Efficiency Stack Verification ==='

$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
Write-Host "Codex home: $CodexHome"

$config = Join-Path $CodexHome 'config.toml'
$agents = Join-Path $CodexHome 'AGENTS.md'
$rtkMd = Join-Path $CodexHome 'RTK.md'
$hooks = Join-Path $CodexHome 'hooks.json'
$agentDir = Join-Path $CodexHome 'agents'

$laneFiles = [ordered]@{
    'luna-low'    = Join-Path $agentDir 'luna-low.toml'
    'luna-medium' = Join-Path $agentDir 'luna-medium.toml'
    'luna-high'   = Join-Path $agentDir 'luna-high.toml'
    'sol-high'    = Join-Path $agentDir 'sol-high.toml'
    'astra-high'  = Join-Path $agentDir 'astra-high.toml'
}

Write-Host "`n[Files]"
@(
    $config,
    $agents,
    $rtkMd,
    $hooks
) | ForEach-Object {
    $status = if (Test-Path $_) { '[OK]' } else { '[--]' }
    "{0,-8} {1}" -f $status, $_
}

Write-Host "`n[RTK]"
$rtk = Get-Command rtk -ErrorAction SilentlyContinue
if ($rtk) {
    Write-Host "[OK] $($rtk.Source)"
    & rtk --version
} else {
    Write-Host '[--] rtk not found in PATH'
}

Write-Host "`n[Code Review Graph]"
$crg = Get-Command code-review-graph -ErrorAction SilentlyContinue
if ($crg) {
    Write-Host "[OK] $($crg.Source)"
    & code-review-graph --version
} else {
    Write-Host '[--] code-review-graph not found in PATH'
}

Write-Host "`n[Codex config checks]"
if (Test-Path $config) {
    if (Select-String -Path $config -Pattern '^tool_output_token_limit\s*=\s*4000\s*$' -Quiet) {
        Write-Host '[OK] tool_output_token_limit = 4000'
    } else {
        Write-Host '[--] tool_output_token_limit = 4000 not found exactly'
    }

    if (Select-String -Path $config -Pattern '^\[mcp_servers\.code-review-graph\]' -Quiet) {
        Write-Host '[OK] code-review-graph MCP configured'
    } else {
        Write-Host '[--] code-review-graph MCP block not found'
    }

    Write-Host "`n[Optional model-routing v2]"
    if (Select-String -Path $config -Pattern '^\[agents\]\s*$' -Quiet) {
        Write-Host '[OK] [agents] block found'
    } else {
        Write-Host '[--] [agents] block not found'
    }

    if (Select-String -Path $config -Pattern '^default_subagent_model\s*=\s*["'']gpt-6-luna["'']\s*$' -Quiet) {
        Write-Host '[OK] default subagent model = gpt-6-luna'
    } else {
        Write-Host '[--] default subagent model gpt-6-luna not found'
    }

    if (Select-String -Path $config -Pattern '^default_subagent_reasoning_effort\s*=\s*["'']medium["'']\s*$' -Quiet) {
        Write-Host '[OK] default subagent reasoning = medium'
    } else {
        Write-Host '[--] default subagent reasoning medium not found'
    }

    foreach ($lane in $laneFiles.Keys) {
        $escapedLane = [regex]::Escape($lane)
        if (Select-String -Path $config -Pattern "^\[agents\.$escapedLane\]\s*$" -Quiet) {
            Write-Host "[OK] role configured: $lane"
        } else {
            Write-Host "[--] role block not found: $lane"
        }
    }
} else {
    Write-Host '[--] config.toml not found; config checks skipped'
}

Write-Host "`n[Routing role files]"
foreach ($lane in $laneFiles.Keys) {
    $path = $laneFiles[$lane]
    if (-not (Test-Path $path)) {
        Write-Host "[--] $lane : $path"
        continue
    }

    $expectedModel = switch ($lane) {
        'sol-high'   { 'gpt-6-sol' }
        'astra-high' { 'gpt-6-astra' }
        default      { 'gpt-6-luna' }
    }
    $expectedEffort = switch ($lane) {
        'luna-low'    { 'low' }
        'luna-medium' { 'medium' }
        'luna-high'   { 'high' }
        'sol-high'    { 'high' }
        'astra-high'  { 'high' }
    }

    $modelPattern = '^model\s*=\s*["'']{0}["'']\s*$' -f [regex]::Escape($expectedModel)
    $effortPattern = '^model_reasoning_effort\s*=\s*["'']{0}["'']\s*$' -f [regex]::Escape($expectedEffort)
    $modelOk = Select-String -Path $path -Pattern $modelPattern -Quiet
    $effortOk = Select-String -Path $path -Pattern $effortPattern -Quiet

    if ($modelOk -and $effortOk) {
        Write-Host "[OK] $lane -> $expectedModel / $expectedEffort"
    } else {
        Write-Host "[--] $lane exists but model/reasoning does not match expected profile"
    }
}

Write-Host "`n[AGENTS checks]"
if (Test-Path $agents) {
    if (Select-String -Path $agents -Pattern '^@RTK\.md\s*$' -Quiet) {
        Write-Host '[OK] @RTK.md reference found'
    } else {
        Write-Host '[--] @RTK.md reference not found'
    }

    if (Select-String -Path $agents -Pattern 'Code Review Graph' -Quiet) {
        Write-Host '[OK] CRG guidance found'
    } else {
        Write-Host '[--] CRG guidance not found'
    }

    if (Select-String -Path $agents -Pattern 'luna-medium' -SimpleMatch -Quiet) {
        Write-Host '[OK] model-routing guidance found'
    } else {
        Write-Host '[--] model-routing guidance not found'
    }

    if (Select-String -Path $agents -Pattern 'Durable task state' -SimpleMatch -Quiet) {
        Write-Host '[OK] durable task-state guidance found'
    } else {
        Write-Host '[--] durable task-state guidance not found'
    }
}

Write-Host "`n[CRG registry]"
if ($crg) {
    & code-review-graph repos
}

Write-Host "`nDone. This script is read-only."
