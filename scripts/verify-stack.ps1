$ErrorActionPreference = 'Continue'

Write-Host '=== Codex Context-Efficiency Stack Verification (DevDay 2026) ==='

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
    foreach ($text in @('@RTK.md','gpt-6.1-sol','sol-xhigh','Quota discipline','Code Review Graph')) {
        if (Select-String -Path $agents -Pattern ([regex]::Escape($text)) -Quiet) { Write-Host "[OK] guidance: $text" } else { Write-Host "[--] guidance missing: $text" }
    }
}

Write-Host "`nDone. This script is read-only."
