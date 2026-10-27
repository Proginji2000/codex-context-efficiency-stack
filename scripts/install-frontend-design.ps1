[CmdletBinding()]
param([switch]$Force)

# Opt-in installer for the vendored, unmodified Apache-2.0 frontend-design skill.
# No network fetches and no changes to ~/.codex/config.toml or ~/.codex/AGENTS.md.
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Source = Join-Path $RepoRoot '.agents\skills\frontend-design'
$Destination = Join-Path $HOME '.agents\skills\frontend-design'
$Files = @('SKILL.md','LICENSE.txt')

foreach ($name in $Files) {
    if (-not (Test-Path -LiteralPath (Join-Path $Source $name) -PathType Leaf)) {
        throw "Missing vendored skill file: $name"
    }
}

if (Test-Path -LiteralPath $Destination) {
    if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
        throw "Skill destination exists but is not a directory: $Destination"
    }
    $same = $true
    foreach ($name in $Files) {
        $src = Join-Path $Source $name
        $dst = Join-Path $Destination $name
        if (-not (Test-Path -LiteralPath $dst -PathType Leaf)) { $same = $false; break }
        if ((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash) {
            $same = $false
            break
        }
    }
    if ($same) {
        Write-Host "[OK] frontend-design skill already installed: $Destination"
        return
    }
    if (-not $Force) {
        throw "A different frontend-design skill exists at $Destination. Inspect it and rerun with -Force only if replacement is intended."
    }
    $backup = Join-Path $HOME ('.agents\skill-backups\frontend-design-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $Destination -Destination $backup -Recurse -Force
    Write-Host "[OK] Backup: $backup"
} else {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
}

foreach ($name in $Files) {
    Copy-Item -LiteralPath (Join-Path $Source $name) -Destination (Join-Path $Destination $name) -Force
}
Write-Host "[OK] Installed frontend-design skill: $Destination"
Write-Host '[INFO] This installer does not modify global routing or enable any external service.'
Write-Host '[INFO] The ui-implementer worker will load frontend-design automatically for applicable UI tasks.'
Write-Host '[INFO] Restart Codex if the newly installed skill is not discovered.'
