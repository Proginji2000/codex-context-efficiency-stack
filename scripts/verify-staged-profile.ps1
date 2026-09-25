$ErrorActionPreference = 'Continue'

Write-Host '=== Codex Context-Efficiency Staged Profile Verification ==='

$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$ProfileConfig = Join-Path $CodexHome 'context-efficiency.config.toml'
$ProfileAgents = Join-Path $CodexHome 'profiles\context-efficiency\agents'

Write-Host "Codex home: $CodexHome"
Write-Host "Profile config: $ProfileConfig"

$ok = $true

Write-Host "`n[Codex CLI]"
$codex = Get-Command codex -ErrorAction SilentlyContinue
if ($codex) {
    $versionText = (& codex --version 2>$null | Out-String).Trim()
    Write-Host "[OK] $versionText"
} else {
    Write-Host '[--] codex not found in PATH'
    $ok = $false
}

Write-Host "`n[Opt-in profile]"
if (Test-Path $ProfileConfig -PathType Leaf) {
    Write-Host '[OK] context-efficiency.config.toml exists'
} else {
    Write-Host '[--] context-efficiency.config.toml missing'
    $ok = $false
}

$lanes = [ordered]@{
    'luna-low'    = @('gpt-6-luna', 'low')
    'luna-medium' = @('gpt-6-luna', 'medium')
    'luna-high'   = @('gpt-6-luna', 'high')
    'sol-high'    = @('gpt-6-sol', 'high')
    'astra-high'  = @('gpt-6-astra', 'high')
}

Write-Host "`n[Isolated role files]"
foreach ($lane in $lanes.Keys) {
    $path = Join-Path $ProfileAgents "$lane.toml"
    if (-not (Test-Path $path -PathType Leaf)) {
        Write-Host "[--] missing: $path"
        $ok = $false
        continue
    }

    $expectedModel = $lanes[$lane][0]
    $expectedEffort = $lanes[$lane][1]
    $modelOk = Select-String -Path $path -Pattern ('^model\s*=\s*["'']{0}["'']\s*$' -f [regex]::Escape($expectedModel)) -Quiet
    $effortOk = Select-String -Path $path -Pattern ('^model_reasoning_effort\s*=\s*["'']{0}["'']\s*$' -f [regex]::Escape($expectedEffort)) -Quiet

    if ($modelOk -and $effortOk) {
        Write-Host "[OK] $lane -> $expectedModel / $expectedEffort"
    } else {
        Write-Host "[--] $lane exists but model/reasoning does not match expected values"
        $ok = $false
    }
}

Write-Host "`n[Profile references]"
if (Test-Path $ProfileConfig -PathType Leaf) {
    foreach ($lane in $lanes.Keys) {
        $expected = "profiles/context-efficiency/agents/$lane.toml"
        if (Select-String -Path $ProfileConfig -Pattern ([regex]::Escape($expected)) -Quiet) {
            Write-Host "[OK] profile references $lane"
        } else {
            Write-Host "[--] profile does not reference $expected"
            $ok = $false
        }
    }

    if (Select-String -Path $ProfileConfig -Pattern '^tool_output_token_limit\s*=\s*4000\s*$' -Quiet) {
        Write-Host '[OK] tool_output_token_limit = 4000'
    } else {
        Write-Host '[--] tool_output_token_limit = 4000 missing'
        $ok = $false
    }
}

Write-Host "`n[Isolation]"
Write-Host '[INFO] This verifier does not modify or invoke the active Codex configuration.'
Write-Host '[INFO] It does not edit ~/.codex/config.toml, ~/.codex/AGENTS.md, hooks, or project files.'
Write-Host '[INFO] The staged profile remains inactive unless Codex is explicitly launched with --profile context-efficiency.'

Write-Host ''
if ($ok) {
    Write-Host 'PASS: staged profile is installed and internally consistent.'
    exit 0
} else {
    Write-Host 'FAIL: staged profile has one or more missing/mismatched items.'
    exit 1
}
