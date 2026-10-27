[CmdletBinding()]
param([switch]$SkipStagedProfile)

$replacement = Join-Path $PSScriptRoot 'update-codex-global.ps1'
if (-not (Test-Path $replacement -PathType Leaf)) {
    throw "Replacement updater not found: $replacement"
}

Write-Host '[INFO] This compatibility entrypoint now forwards to scripts\update-codex-global.ps1.'
& $replacement -SkipStagedProfile:$SkipStagedProfile
exit $LASTEXITCODE
