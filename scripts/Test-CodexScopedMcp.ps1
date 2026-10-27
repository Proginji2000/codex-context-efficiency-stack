[CmdletBinding()]
param()

# No Codex calls: preview-only behavior is evaluated using this checkout.
$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'Invoke-CodexScopedMcp.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'Missing scoped MCP launch script.'
}
$root = Split-Path $PSScriptRoot -Parent

$expected = @{
    git  = @('code-review-graph','context7','node_repl','playwright')
    code = @('node_repl','playwright')
    docs = @('code-review-graph','node_repl','playwright')
    ui   = @()
}
foreach ($scope in @('git','code','docs','ui')) {
    $raw = (& $launcher -ProjectDirectory $root -Scope $scope -AsJson | Out-String)
    $result = $raw | ConvertFrom-Json
    if ($result.mode -ne 'preview_only_no_codex_started' -or
        $result.scope -ne $scope -or
        $result.sandbox -ne 'read-only' -or
        $result.global_config_changes -ne $false -or
        $result.model_calls -ne 0) {
        throw "Unexpected preview contract for $scope."
    }
    $actual = @($result.invocation_scoped_disabled_mcp)
    if (($actual -join ',') -ne ($expected[$scope] -join ',')) {
        throw "Wrong disabled MCP list for $scope."
    }
    if ($raw.Contains($root) -or $raw.Contains('auth.json')) {
        throw "A private or filesystem path was exposed for $scope."
    }
}

$rejected = $false
try {
    $null = & $launcher -Scope git -ProjectDirectory $root -Sandbox workspace-write -AsJson
} catch { $rejected = $true }
if (-not $rejected) { throw 'Git scope allowed write sandbox.' }

$rejected = $false
try {
    $null = & $launcher -Scope git -ProjectDirectory (Join-Path $root 'does-not-exist') -AsJson
} catch { $rejected = $true }
if (-not $rejected) { throw 'Nonexistent project directory was accepted.' }

Write-Host '[OK] git, code, docs and UI preview scopes disable only intended configured MCPs.'
Write-Host '[OK] Read-only Git safety, filesystem path privacy, invalid path rejection.'
Write-Host 'PASS: No Codex binary executed, no quota consumed, no config changes.'
