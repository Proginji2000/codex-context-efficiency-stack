[CmdletBinding()]
param([switch]$SkipStagedProfile)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$AgentHome = Join-Path $CodexHome 'agents'
$ProfileAgentHome = Join-Path $CodexHome 'profiles\context-efficiency\agents'
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $CodexHome "backups\devday-2026-$Timestamp"
$ConfigPath = Join-Path $CodexHome 'config.toml'
$GlobalAgentsPath = Join-Path $CodexHome 'AGENTS.md'

New-Item -ItemType Directory -Force -Path $CodexHome,$AgentHome,$BackupRoot | Out-Null

function Backup-IfExists([string]$Path) {
    if (Test-Path $Path -PathType Leaf) {
        $relative = $Path.Substring($CodexHome.Length).TrimStart('\','/')
        $target = Join-Path $BackupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
        Copy-Item $Path $target -Force
    }
}

Write-Host '=== Codex global DevDay 2026 stack update ==='
Write-Host "Codex home: $CodexHome"
Write-Host "Backup: $BackupRoot"

Backup-IfExists $ConfigPath
Backup-IfExists $GlobalAgentsPath

$roleNames = @('luna-low','luna-medium','luna-high','sol-high','sol-xhigh','astra-high','sol6-legacy-high')
foreach ($role in $roleNames) { Backup-IfExists (Join-Path $AgentHome "$role.toml") }

Copy-Item (Join-Path $RepoRoot 'templates\AGENTS.md') $GlobalAgentsPath -Force
foreach ($role in $roleNames) { Copy-Item (Join-Path $RepoRoot "templates\agents\$role.toml") (Join-Path $AgentHome "$role.toml") -Force }

if (-not (Test-Path $ConfigPath -PathType Leaf)) {
    "tool_output_token_limit = 4000`r`n`r`n" | Set-Content $ConfigPath -Encoding utf8
    Get-Content (Join-Path $RepoRoot 'templates\config.routing.snippet.toml') -Raw | Add-Content $ConfigPath -Encoding utf8
    Write-Host '[OK] Created config.toml with the routing stack.'
} else {
    $configRaw = Get-Content $ConfigPath -Raw
    if ($configRaw -notmatch '(?m)^\[agents\]\s*$') {
        Add-Content $ConfigPath -Value "`r`n$(Get-Content (Join-Path $RepoRoot 'templates\config.routing.snippet.toml') -Raw)" -Encoding utf8
        Write-Host '[OK] Added complete [agents] routing configuration.'
    } else {
        $missingBlocks = [ordered]@{
            'sol-xhigh' = @'

[agents.sol-xhigh]
description = "Deep GPT-6.1 Sol escalation after Sol High remains unresolved; use before Astra when the scope is still bounded."
config_file = "agents/sol-xhigh.toml"
'@
            'sol6-legacy-high' = @'

[agents.sol6-legacy-high]
description = "Legacy GPT-6 Sol High retained for controlled A/B quota/performance tests or temporary compatibility fallback."
config_file = "agents/sol6-legacy-high.toml"
'@
        }
        foreach ($lane in $missingBlocks.Keys) {
            if ($configRaw -notmatch ('(?m)^\[agents\.' + [regex]::Escape($lane) + '\]\s*$')) {
                Add-Content $ConfigPath -Value $missingBlocks[$lane] -Encoding utf8
                Write-Host "[OK] Added role block: $lane"
            }
        }
    }
}

if (-not $SkipStagedProfile) {
    New-Item -ItemType Directory -Force -Path $ProfileAgentHome | Out-Null
    Copy-Item (Join-Path $RepoRoot 'templates\context-efficiency.config.toml') (Join-Path $CodexHome 'context-efficiency.config.toml') -Force
    foreach ($role in $roleNames) { Copy-Item (Join-Path $RepoRoot "templates\agents\$role.toml") (Join-Path $ProfileAgentHome "$role.toml") -Force }
    Write-Host '[OK] Refreshed opt-in staged profile.'
}

Write-Host '[OK] Global AGENTS and role files refreshed.'
Write-Host '[INFO] Existing project-local .codex/config.toml files are intentionally untouched.'
Write-Host '[INFO] Restart Codex to load new role definitions.'
Write-Host "[INFO] Run: pwsh -ExecutionPolicy Bypass -File .\scripts\verify-stack.ps1"
