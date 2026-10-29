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


# New optional tools remain disabled by default; enabling is explicit and
# confined to the task scope, never a persistent global TOML change.
$cases = @(
    @{ Scope = 'code'; Params = @{ EnableSerena = $true }; Expected = 'serena'; RunMode = 'noninteractive_exec' },
    @{ Scope = 'ui'; Params = @{ EnableShadcn = $true }; Expected = 'shadcn'; RunMode = 'noninteractive_exec' },
    @{ Scope = 'ui'; Params = @{ EnableSerena = $true; EnableShadcn = $true; Interactive = $true }; Expected = 'serena,shadcn'; RunMode = 'interactive_tui' }
)
foreach ($testCase in $cases) {
    $params = @{ Scope = $testCase.Scope; ProjectDirectory = $root; AsJson = $true }
    foreach ($key in $testCase.Params.Keys) { $params[$key] = $testCase.Params[$key] }
    $raw = (& $launcher @params | Out-String)
    $result = $raw | ConvertFrom-Json
    if (($result.invocation_scoped_enabled_mcp -join ',') -ne $testCase.Expected -or
        $result.run_mode -ne $testCase.RunMode -or
        $result.model_calls -ne 0 -or $result.global_config_changes -ne $false) {
        throw "Invalid opt-in preview for $($testCase.Scope)."
    }
    if ($raw.Contains($root)) { throw 'Preview exposed a project path.' }
}
$plain = (& $launcher -Scope ui -ProjectDirectory $root -AsJson | Out-String) | ConvertFrom-Json
if (@($plain.invocation_scoped_enabled_mcp).Count -ne 0) {
    throw 'Optional MCPs were enabled without opt-in.'
}
foreach ($bad in @(
    @{ Scope = 'git'; EnableSerena = $true },
    @{ Scope = 'docs'; EnableShadcn = $true },
    @{ Scope = 'code'; EnableShadcn = $true }
)) {
    $params = @{ ProjectDirectory = $root; AsJson = $true }
    foreach ($key in $bad.Keys) { $params[$key] = $bad[$key] }
    $rejected = $false
    try { $null = & $launcher @params } catch { $rejected = $true }
    if (-not $rejected) { throw 'Out-of-scope optional MCP was allowed.' }
}

Write-Host '[OK] git, code, docs and UI preview scopes disable only intended configured MCPs.'
Write-Host '[OK] Read-only Git safety, filesystem path privacy, invalid path rejection.'
Write-Host 'PASS: No Codex binary executed, no quota consumed, no config changes.'
