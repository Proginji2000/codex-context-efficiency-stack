[CmdletBinding()]
param([string]$ProjectPath = (Get-Location).Path)

$ErrorActionPreference = 'Continue'
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$resolved = (Resolve-Path $ProjectPath).Path
$localConfig = Join-Path $resolved '.codex\config.toml'
$localAgents = Join-Path $resolved 'AGENTS.md'
$localCodexDir = Join-Path $resolved '.codex'

Write-Host '=== Codex project inheritance audit ==='
Write-Host "Project: $resolved"
Write-Host "Global Codex home: $CodexHome"

Write-Host "`n[Global layer]"
foreach ($p in @((Join-Path $CodexHome 'AGENTS.md'),(Join-Path $CodexHome 'config.toml'))) { if (Test-Path $p) { Write-Host "[OK] $p" } else { Write-Host "[--] $p" } }

Write-Host "`n[Project layer]"
if (Test-Path $localAgents) { Write-Host '[INFO] Repository AGENTS.md exists: global instructions still apply, with project-specific instructions layered for this repository.' } else { Write-Host '[OK] No repository AGENTS.md detected.' }
if (Test-Path $localConfig) {
    Write-Host '[WARN] Project-local .codex/config.toml exists and may override global routing/model settings.'
    $raw = Get-Content $localConfig -Raw
    foreach ($model in @('gpt-6-sol','gpt-6.1-sol','gpt-6-astra','gpt-6-luna')) {
        $count = ([regex]::Matches($raw,[regex]::Escape($model))).Count
        if ($count -gt 0) { Write-Host "[INFO] local config references $model ($count)" }
    }
    $roleHeaders = Select-String -Path $localConfig -Pattern '^\[agents\.[^\]]+\]\s*$' | ForEach-Object { $_.Line.Trim() }
    foreach ($header in $roleHeaders) { Write-Host "[INFO] local role: $header" }
} else {
    Write-Host '[OK] No project-local .codex/config.toml: global routing is not shadowed by a local config file.'
}

if (Test-Path $localCodexDir -PathType Container) {
    Write-Host "[INFO] .codex directory exists: $localCodexDir"
}

Write-Host "`n[Conclusion]"
if (Test-Path $localConfig) {
    Write-Host 'AUDIT REQUIRED: do not assume GPT-6.1 Sol routing is inherited. Compare the local roles/config before migration.'
} else {
    Write-Host 'GLOBAL ROUTING INHERITED: project-specific AGENTS/rules may still add instructions, but no local Codex config shadows the global model routing.'
}
