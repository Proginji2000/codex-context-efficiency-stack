[CmdletBinding()]
param(
    [switch]$InstallDependencies,
    [switch]$ConfigureCurrentRepository,
    [switch]$SkipRtk,
    [switch]$SkipCrg
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path $PSScriptRoot -Parent
$SourceRoot = Join-Path $RepoRoot 'claude'
$ClaudeHome = Join-Path $env:USERPROFILE '.claude'
$AgentsHome = Join-Path $ClaudeHome 'agents'
$SettingsPath = Join-Path $ClaudeHome 'settings.json'
$ClaudeMdPath = Join-Path $ClaudeHome 'CLAUDE.md'
$EfficiencyPath = Join-Path $ClaudeHome 'CLAUDE_CONTEXT_EFFICIENCY.md'
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $ClaudeHome "backups\context-efficiency-$Timestamp"

if (-not (Test-Path $SourceRoot -PathType Container)) {
    throw "Claude stack sources not found: $SourceRoot"
}

New-Item -ItemType Directory -Force -Path $ClaudeHome, $AgentsHome, $BackupRoot | Out-Null

function Backup-File {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (Test-Path $Path -PathType Leaf) {
        $relative = $Path.Substring($ClaudeHome.Length).TrimStart('\','/')
        $target = Join-Path $BackupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
        Copy-Item $Path $target -Force
    }
}

function Set-Property {
    param($Object, [string]$Name, $Value)
    if ($Object.PSObject.Properties.Name -contains $Name) {
        $Object.$Name = $Value
    } else {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value
    }
}

Write-Host '=== Claude Pro Context-Efficiency Stack Installer ==='
Write-Host "Claude home: $ClaudeHome"
Write-Host "Backup: $BackupRoot"

# Back up the pre-install state before RTK or this stack changes Claude files.
Backup-File $SettingsPath
Backup-File $ClaudeMdPath
Backup-File $EfficiencyPath

$agentNames = @('Explore','haiku-low','sonnet-medium','sonnet-high','opus-high','opus-xhigh')
foreach ($name in $agentNames) {
    Backup-File (Join-Path $AgentsHome "$name.md")
}

if (-not $SkipRtk) {
    $rtk = Get-Command rtk -ErrorAction SilentlyContinue
    if (-not $rtk -and $InstallDependencies) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Host '[RTK] Installing with winget...'
            & winget install --id rtk-ai.rtk --exact --accept-package-agreements --accept-source-agreements
            $rtk = Get-Command rtk -ErrorAction SilentlyContinue
        } else {
            Write-Warning 'winget not found; RTK was not installed.'
        }
    }
    if ($rtk) {
        Write-Host '[RTK] Initializing Claude Code integration...'
        & rtk init -g --auto-patch
    } else {
        Write-Warning 'RTK not found. Install rtk-ai/rtk, then run: rtk init -g --auto-patch'
    }
}

Copy-Item (Join-Path $SourceRoot 'CLAUDE_CONTEXT_EFFICIENCY.md') $EfficiencyPath -Force

$importLine = '@CLAUDE_CONTEXT_EFFICIENCY.md'
if (-not (Test-Path $ClaudeMdPath -PathType Leaf)) {
    Set-Content -Path $ClaudeMdPath -Value $importLine -Encoding utf8
} else {
    $existingClaude = Get-Content $ClaudeMdPath -Raw
    if ($existingClaude -notmatch '(?m)^@CLAUDE_CONTEXT_EFFICIENCY\.md\s*$') {
        Add-Content -Path $ClaudeMdPath -Value "`r`n$importLine" -Encoding utf8
    }
}

$settings = [pscustomobject]@{}
if (Test-Path $SettingsPath -PathType Leaf) {
    $rawSettings = Get-Content $SettingsPath -Raw
    if ($rawSettings.Trim()) {
        try {
            $settings = $rawSettings | ConvertFrom-Json
        } catch {
            throw "Existing Claude settings are invalid JSON. Restore/fix $SettingsPath before installing. Backup: $BackupRoot"
        }
    }
}

Set-Property $settings 'model' 'sonnet'
Set-Property $settings 'ultracode' $false
if (-not ($settings.PSObject.Properties.Name -contains 'env') -or $null -eq $settings.env) {
    Set-Property $settings 'env' ([pscustomobject]@{})
}
Set-Property $settings.env 'CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS' '2'
Set-Property $settings.env 'CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH' '1'

$settings | ConvertTo-Json -Depth 50 | Set-Content -Path $SettingsPath -Encoding utf8

foreach ($name in $agentNames) {
    $source = Join-Path $SourceRoot "agents\$name.md"
    if (-not (Test-Path $source -PathType Leaf)) { throw "Missing agent template: $source" }
    Copy-Item $source (Join-Path $AgentsHome "$name.md") -Force
}

if ($ConfigureCurrentRepository -and -not $SkipCrg) {
    $crg = Get-Command code-review-graph -ErrorAction SilentlyContinue
    if (-not $crg -and $InstallDependencies) {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if ($python) {
            Write-Host '[CRG] Installing Code Review Graph...'
            & python -m pip install -U 'code-review-graph[communities,enrichment]'
            $crg = Get-Command code-review-graph -ErrorAction SilentlyContinue
        } else {
            Write-Warning 'Python not found; Code Review Graph was not installed.'
        }
    }
    if ($crg) {
        Write-Host "[CRG] Configuring current repository: $((Get-Location).Path)"
        & code-review-graph install --platform claude-code
        & code-review-graph build
    } else {
        Write-Warning 'Code Review Graph not found. Run the CRG install/build commands later from each target repository.'
    }
}

Write-Host ''
Write-Host '[OK] Claude context-efficiency files installed.'
Write-Host '[OK] Default model: Sonnet; concurrent subagents: 2; nested spawning: disabled.'
Write-Host '[OK] Pre-install Claude files replaced by this installer were backed up.'
Write-Host "Backup location: $BackupRoot"
Write-Host ''
Write-Host 'Next: run scripts\verify-claude-pro-stack.ps1 and restart Claude Code if the agents directory did not exist before this install.'
