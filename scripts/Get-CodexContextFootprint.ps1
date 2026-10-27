[CmdletBinding()]
param(
    [string]$ProjectDirectory = (Get-Location).Path,
    [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }),
    [string]$CandidatePath,
    [switch]$AsJson
)

# Read-only static footprint inventory. NO Codex invocation, token usage APIs,
# transcript/session access, or editing user configuration.
# Reports only counts and relative labels, never file contents, MCP server
# names, paths, tokens, credentials or environment variable values.
$ErrorActionPreference = 'Stop'
$cwd = (Resolve-Path -LiteralPath $ProjectDirectory -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath $cwd -PathType Container)) {
    throw 'ProjectDirectory must be an existing directory.'
}

function Get-FileSize([string]$File) {
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { return $null }
    $info = Get-Item -LiteralPath $File -ErrorAction Stop
    $text = [System.IO.File]::ReadAllText($info.FullName, [System.Text.Encoding]::UTF8)
    return [pscustomobject]@{ characters = $text.Length; bytes = [long]$info.Length }
}

$global = Get-FileSize (Join-Path $CodexHome 'AGENTS.md')
$rtk = Get-FileSize (Join-Path $CodexHome 'RTK.md')

# Find the closest Git repository root without invoking git (which may hang).
$cursor = New-Object System.IO.DirectoryInfo($cwd)
$root = $null
while ($null -ne $cursor) {
    if (Test-Path -LiteralPath (Join-Path $cursor.FullName '.git')) {
        $root = $cursor.FullName
        break
    }
    $cursor = $cursor.Parent
}
if ($null -eq $root) { $root = $cwd }

# Only visit the Git root -> requested working-directory chain.
$chain = New-Object 'System.Collections.Generic.List[string]'
$cursor = New-Object System.IO.DirectoryInfo($cwd)
while ($null -ne $cursor) {
    $chain.Insert(0, $cursor.FullName)
    if ([string]::Equals($cursor.FullName, $root, [StringComparison]::OrdinalIgnoreCase)) {
        break
    }
    $cursor = $cursor.Parent
}

$projectInstructions = @()
$level = 0
foreach ($folder in $chain) {
    $override = Join-Path $folder 'AGENTS.override.md'
    $standard = Join-Path $folder 'AGENTS.md'
    $path = $null
    if (Test-Path -LiteralPath $override -PathType Leaf) {
        $path = $override
        $kind = 'AGENTS.override.md'
    } elseif (Test-Path -LiteralPath $standard -PathType Leaf) {
        $path = $standard
        $kind = 'AGENTS.md'
    }
    if ($null -ne $path) {
        $size = Get-FileSize $path
        $projectInstructions += [pscustomobject]@{
            scope = if ($level -eq 0) { 'project_root' } else { 'project_subdirectory' }
            depth = $level
            file_kind = $kind
            characters = $size.characters
            bytes = $size.bytes
        }
    }
    $level++
}

$config = Join-Path $CodexHome 'config.toml'
$mcpCount = $null
$agentConfigCount = $null
if (Test-Path -LiteralPath $config -PathType Leaf) {
    # Never return or print raw config; may contain secrets or private MCP URLs.
    $configuration = [System.IO.File]::ReadAllText($config, [System.Text.Encoding]::UTF8)
    $mcpCount = [regex]::Matches($configuration, '(?m)^\s*\[mcp_servers\.[^\]\r\n]+\]\s*$').Count
    $agentConfigCount = [regex]::Matches($configuration, '(?m)^\s*\[agents\.[^\]\r\n]+\]\s*$').Count
    $configuration = $null
}

$agentDir = Join-Path $CodexHome 'agents'
$roleCount = 0
$roleBytes = [long]0
if (Test-Path -LiteralPath $agentDir -PathType Container) {
    foreach ($role in @(Get-ChildItem -LiteralPath $agentDir -Filter '*.toml' -File -ErrorAction Stop)) {
        $roleCount++
        $roleBytes += [long]$role.Length
    }
}

$projectChars = 0
foreach ($entry in $projectInstructions) { $projectChars += $entry.characters }
$knownInstructionChars = $projectChars
if ($null -ne $global) { $knownInstructionChars += $global.characters }

$candidate = $null
if (-not [string]::IsNullOrWhiteSpace($CandidatePath)) {
    $candidate = Get-FileSize $CandidatePath
    if ($null -eq $candidate) { throw 'CandidatePath must be an existing readable file.' }
}

$comparison = $null
if ($null -ne $global -and $null -ne $candidate) {
    $comparison = [pscustomobject]@{
        current_global_characters = $global.characters
        candidate_global_characters = $candidate.characters
        character_difference = $candidate.characters - $global.characters
        percent_reduction = if ($global.characters -gt 0) {
            [math]::Round(100 * ($global.characters - $candidate.characters) / $global.characters, 2)
        } else { $null }
    }
}

$report = [pscustomobject]@{
    kind = 'static_file_inventory_not_live_prompt_or_token_count'
    global_agents = $global
    project_agent_files = @($projectInstructions)
    project_instruction_characters = $projectChars
    global_plus_project_instruction_characters = $knownInstructionChars
    rtk_reference_file = $rtk
    role_toml_files_installed = $roleCount
    role_toml_total_bytes = $roleBytes
    configured_mcp_server_blocks = $mcpCount
    configured_agent_role_blocks = $agentConfigCount
    candidate_comparison = $comparison
    limitations = 'Files and TOML blocks only: cannot establish runtime injection, MCP schemas, actual token counts, subagent usage, prompt cache, quota or performance.'
}
if ($AsJson) {
    $report | ConvertTo-Json -Depth 6
} else {
    $report | Format-List | Out-String -Width 160 | Write-Output
}
