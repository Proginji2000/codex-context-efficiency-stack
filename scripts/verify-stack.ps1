$ErrorActionPreference = 'Continue'

Write-Host '=== Codex Context-Efficiency Stack Verification ==='

$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
Write-Host "Codex home: $CodexHome"

$config = Join-Path $CodexHome 'config.toml'
$agents = Join-Path $CodexHome 'AGENTS.md'
$rtkMd = Join-Path $CodexHome 'RTK.md'
$hooks = Join-Path $CodexHome 'hooks.json'

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
}

Write-Host "`n[CRG registry]"
if ($crg) {
    & code-review-graph repos
}

Write-Host "`nDone. This script is read-only."
