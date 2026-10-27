$ErrorActionPreference = 'Continue'

Write-Host '=== Codex Context-Efficiency Stack Verification (Terra 6.1 refresh) ==='

$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$config = Join-Path $CodexHome 'config.toml'
$agents = Join-Path $CodexHome 'AGENTS.md'
$rtkMd = Join-Path $CodexHome 'RTK.md'
$hooks = Join-Path $CodexHome 'hooks.json'
$agentDir = Join-Path $CodexHome 'agents'
$laneFiles = [ordered]@{
    'luna-low'         = @((Join-Path $agentDir 'luna-low.toml'),'gpt-6-luna','low')
    'luna-medium'      = @((Join-Path $agentDir 'luna-medium.toml'),'gpt-6-luna','medium')
    'luna-high'        = @((Join-Path $agentDir 'luna-high.toml'),'gpt-6-luna','high')
    'terra-medium'     = @((Join-Path $agentDir 'terra-medium.toml'),'gpt-6.1-terra','medium')
    'terra-high'       = @((Join-Path $agentDir 'terra-high.toml'),'gpt-6.1-terra','high')
    'ui-implementer'   = @((Join-Path $agentDir 'ui-implementer.toml'),'gpt-6.1-terra','medium')
    'sol-high'         = @((Join-Path $agentDir 'sol-high.toml'),'gpt-6.1-sol','high')
    'sol-xhigh'        = @((Join-Path $agentDir 'sol-xhigh.toml'),'gpt-6.1-sol','xhigh')
    'astra-high'       = @((Join-Path $agentDir 'astra-high.toml'),'gpt-6-astra','high')
    'sol6-legacy-high' = @((Join-Path $agentDir 'sol6-legacy-high.toml'),'gpt-6-sol','high')
}

Write-Host "Codex home: $CodexHome"
Write-Host "`n[Core files]"
@($config,$agents,$rtkMd,$hooks) | ForEach-Object { $status = if (Test-Path $_) {'[OK]'} else {'[--]'}; "{0,-8} {1}" -f $status,$_ }

Write-Host "`n[Executables]"
foreach ($name in @('codex','rtk','code-review-graph')) { $cmd = Get-Command $name -ErrorAction SilentlyContinue; if ($cmd) { Write-Host "[OK] $name -> $($cmd.Source)" } else { Write-Host "[--] $name not found" } }

Write-Host "`n[Codex config]"
if (Test-Path $config) {
    foreach ($pattern in @('^tool_output_token_limit\s*=\s*4000\s*$','^\[agents\]\s*$','^default_subagent_model\s*=\s*["'']gpt-6-luna["'']\s*$')) {
        if (Select-String -Path $config -Pattern $pattern -Quiet) { Write-Host "[OK] $pattern" } else { Write-Host "[--] missing: $pattern" }
    }
    foreach ($lane in $laneFiles.Keys) {
        $header = '^\[agents\.' + [regex]::Escape($lane) + '\]\s*$'
        if (Select-String -Path $config -Pattern $header -Quiet) { Write-Host "[OK] role configured: $lane" } else { Write-Host "[--] role block not found: $lane" }
    }
}

Write-Host "`n[Role files]"
foreach ($lane in $laneFiles.Keys) {
    $path,$expectedModel,$expectedEffort = $laneFiles[$lane]
    if (-not (Test-Path $path)) { Write-Host "[--] missing $lane : $path"; continue }
    $modelOk = Select-String -Path $path -Pattern ('^model\s*=\s*["'']{0}["'']\s*$' -f [regex]::Escape($expectedModel)) -Quiet
    $effortOk = Select-String -Path $path -Pattern ('^model_reasoning_effort\s*=\s*["'']{0}["'']\s*$' -f [regex]::Escape($expectedEffort)) -Quiet
    if ($modelOk -and $effortOk) { Write-Host "[OK] $lane -> $expectedModel / $expectedEffort" } else { Write-Host "[--] mismatch: $lane" }
}

Write-Host "`n[AGENTS]"
if (Test-Path $agents) {
    $agentChecks = [ordered]@{
        '@RTK.md'          = '@RTK.md'
        'GPT-6.1 Terra'    = 'GPT-6.1 Terra'
        'terra-medium'     = 'terra-medium'
        'ui-implementer'   = 'ui-implementer'
        'GPT-6.1 Sol'      = 'GPT-6.1 Sol'
        'sol-xhigh'        = 'sol-xhigh'
        'Quota discipline' = 'Quota discipline'
        'Code Review Graph'= 'Code Review Graph'
        'Orchestrator-only contract' = '### Orchestrator-only contract'
        'Automatic project resumption' = '### Automatic project resumption (delegated, bounded)'
        'Conditional tools and quality gates' = '### Conditional tools and quality gates'
    }
    foreach ($label in $agentChecks.Keys) {
        $text = $agentChecks[$label]
        if (Select-String -Path $agents -Pattern ([regex]::Escape($text)) -Quiet) { Write-Host "[OK] guidance: $label" } else { Write-Host "[--] guidance missing: $label" }
    }
}

Write-Host "`n[Frontend design skill]"
$frontendSkill = Join-Path $HOME '.agents\skills\frontend-design\SKILL.md'
$frontendLicense = Join-Path $HOME '.agents\skills\frontend-design\LICENSE.txt'
if ((Test-Path -LiteralPath $frontendSkill -PathType Leaf) -and (Test-Path -LiteralPath $frontendLicense -PathType Leaf)) {
    Write-Host "[OK] frontend-design globally installed: $frontendSkill"
} else {
    Write-Host '[--] frontend-design is not installed user-wide. Run .\scripts\install-frontend-design.ps1 from the stack repository.'
}
Write-Host "`n[Optional tools — not required for core stack]"
foreach ($name in @('gitleaks','node','npm')) {
    $optionalCommand = Get-Command $name -ErrorAction SilentlyContinue
    if ($optionalCommand) {
        Write-Host "[OK] $name -> $($optionalCommand.Source)"
    } else {
        Write-Host "[--] $name not found (optional; see docs/DEVELOPER_EXTENSIONS.md)"
    }
}
if (Test-Path -LiteralPath $config -PathType Leaf) {
    foreach ($serverName in @('playwright','context7')) {
        $needle = '^\[mcp_servers\.' + [regex]::Escape($serverName) + '\]\s*$'
        if (Select-String -LiteralPath $config -Pattern $needle -Quiet) {
            Write-Host "[OK] MCP $serverName configured (connection NOT verified)"
        } else {
            Write-Host "[--] MCP $serverName not registered globally (optional)"
        }
    }
}
Write-Host '[INFO] Get-ProjectResume.ps1 and Test-SecretGate.ps1 are opt-in helpers for worker tasks.'
Write-Host '[INFO] Policy presence is a static check, not proof that Codex spawned subagents.'
Write-Host '[INFO] This verifier cannot prove implicit skill activation; confirm via a delegated UI task.'
Write-Host "`nDone. This script is read-only."
