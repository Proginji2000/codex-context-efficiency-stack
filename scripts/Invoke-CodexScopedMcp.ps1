[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('git', 'code', 'docs', 'ui')]
    [string]$Scope,

    [string]$ProjectDirectory = (Get-Location).Path,

    [string]$Prompt,

    [ValidateSet('read-only', 'workspace-write')]
    [string]$Sandbox = 'read-only',

    [switch]$Run,
    [switch]$AsJson
)

# Opt-in, invocation-scoped Codex MCP server selection.
# No global config edits, installations, model calls or process starts in preview.
# Does not read config.toml, auth.json, conversations or private project files.
$ErrorActionPreference = 'Stop'

$fullProject = (Resolve-Path -LiteralPath $ProjectDirectory -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath $fullProject -PathType Container)) {
    throw 'ProjectDirectory must be a readable existing directory.'
}
if ($Scope -eq 'git' -and $Sandbox -ne 'read-only') {
    throw 'Git audit scope requires read-only sandbox.'
}

# Keep approved project tooling available for scopes where it is needed.
# The UI lane keeps every configured MCP available, including node_repl
# (Codex Desktop browser features may depend on it).
$disabled = @()
switch ($Scope) {
    'git' { $disabled = @('code-review-graph', 'context7', 'node_repl', 'playwright') }
    'code' { $disabled = @('node_repl', 'playwright') }
    'docs' { $disabled = @('code-review-graph', 'node_repl', 'playwright') }
    'ui' { $disabled = @() }
}
$allServers = @('code-review-graph', 'context7', 'node_repl', 'playwright')
$enabled = @($allServers | Where-Object { $disabled -notcontains $_ })

# Host launcher overrides user config for this ONE invocation. A
# configured MCP entry is not evidence of runtime tool availability.
$arguments = @('exec', '-C', $fullProject, '--ephemeral',
               '--sandbox', $Sandbox)
foreach ($server in $disabled) {
    $arguments += '-c'
    $arguments += ('mcp_servers.{0}.enabled=false' -f $server)
}

if (-not $Run) {
    $report = [pscustomobject]@{
        mode = 'preview_only_no_codex_started'
        scope = $Scope
        sandbox = $Sandbox
        invocation_scoped_disabled_mcp = @($disabled)
        remaining_configured_mcp = @($enabled)
        uses_cli_config_overrides = $true
        global_config_changes = $false
        model_calls = 0
        note = 'Preview only. -Run and -Prompt are needed to invoke Codex.'
    }
    if ($AsJson) {
        $report | ConvertTo-Json -Depth 4
    } else {
        $report | Format-List | Out-String -Width 160 | Write-Output
    }
    return
}

if ([string]::IsNullOrWhiteSpace($Prompt)) {
    throw '-Prompt is required when -Run is specified.'
}
$executable = Get-Command codex -ErrorAction SilentlyContinue
if ($null -eq $executable) {
    throw 'Codex CLI was not found on PATH. No invocation was started.'
}

$arguments += $Prompt
# Explicit opt-in only: the script does not change any persistent settings.
& $executable.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw ("Codex exited with status {0}." -f $LASTEXITCODE)
}
