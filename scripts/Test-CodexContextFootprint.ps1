[CmdletBinding()]
param()

# Synthetic, local-only inventory test. No Codex binary or account calls.
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'Get-CodexContextFootprint.ps1'
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    throw 'Static context footprint inventory script missing.'
}

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('codex-footprint-fixture-' + [guid]::NewGuid().ToString('N'))
$codexRoot = Join-Path $tmp 'codexhome'
$project = Join-Path $tmp 'repo'
$nested = Join-Path $project 'src'
$roles = Join-Path $codexRoot 'agents'
foreach ($dir in @($tmp, $codexRoot, $project, $nested, $roles, (Join-Path $project '.git'))) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

try {
    $globalText = 'global agent policy'
    $repoText = 'repository rules'
    $childText = 'child override rules'
    $candidateText = 'shorter'
    Set-Content -LiteralPath (Join-Path $codexRoot 'AGENTS.md') -Value $globalText -NoNewline -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $codexRoot 'RTK.md') -Value 'optional rtk' -NoNewline -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $project 'AGENTS.md') -Value $repoText -NoNewline -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $nested 'AGENTS.md') -Value 'shadowed' -NoNewline -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $nested 'AGENTS.override.md') -Value $childText -NoNewline -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $roles 'luna-low.toml') -Value 'model = "fake"' -NoNewline -Encoding ASCII
    $candidate = Join-Path $tmp 'candidate.md'
    Set-Content -LiteralPath $candidate -Value $candidateText -NoNewline -Encoding ASCII
    @(
        '[mcp_servers.private_alpha]'
        'command = "npx"'
        '[mcp_servers.private_alpha.env]'
        'API_KEY = "NEVER_DISCLOSE_SECRET_SENTINEL"'
        '[mcp_servers.private_beta]'
        'url = "https://PRIVATE_URL_SENTINEL.invalid"'
        '[mcp_servers.private_beta.http_headers]'
        'Authorization = "PRIVATE_BEARER_SENTINEL"'
        '[mcp_servers."private.dot.name"]'
        'command = "python"'
        '[mcp_servers."private.dot.name".env]'
        'TOKEN = "PRIVATE_DOTTED_SENTINEL"'
        '[mcp_servers.private_gamma]'
        'command = "node"'
        '[mcp_servers.private_gamma.env]'
        'TOKEN = "PRIVATE_GAMMA_SENTINEL"'
        '[mcp_servers.private_gamma.metadata]'
        'test = "PRIVATE_METADATA_SENTINEL"'
        '[agents.luna-low]'
        'config_file = "PRIVATE_PATH_SENTINEL"'
    ) | Set-Content -LiteralPath (Join-Path $codexRoot 'config.toml') -Encoding ASCII

    $raw = (& $scriptPath -CodexHome $codexRoot -ProjectDirectory $nested -CandidatePath $candidate -AsJson | Out-String)
    $r = $raw | ConvertFrom-Json
    Write-Host ("[INFO] Synthetic MCP servers={0}; headers incl. nested={1}; agent tables={2}." -f $r.configured_mcp_server_blocks, $r.mcp_config_table_headers_including_subtables, $r.configured_agent_role_blocks)
    if ($r.kind -ne 'static_file_inventory_not_live_prompt_or_token_count' -or
        $r.global_agents.characters -ne $globalText.Length -or
        $r.project_agent_files.Count -ne 2 -or
        $r.project_agent_files[0].file_kind -ne 'AGENTS.md' -or
        $r.project_agent_files[1].file_kind -ne 'AGENTS.override.md' -or
        $r.project_instruction_characters -ne ($repoText.Length + $childText.Length) -or
        $r.global_plus_project_instruction_characters -ne ($globalText.Length + $repoText.Length + $childText.Length) -or
        $r.role_toml_files_installed -ne 1 -or
        $r.configured_mcp_server_blocks -ne 4 -or
        $r.mcp_config_table_headers_including_subtables -ne 9 -or
        $r.configured_agent_role_blocks -ne 1 -or
        $r.candidate_comparison.character_difference -ne ($candidateText.Length - $globalText.Length)) {
        throw 'Unexpected static footprint inventory or comparison results.'
    }

    foreach ($private in @('NEVER_DISCLOSE_SECRET_SENTINEL','PRIVATE_URL_SENTINEL','PRIVATE_PATH_SENTINEL','PRIVATE_BEARER_SENTINEL','PRIVATE_DOTTED_SENTINEL','PRIVATE_GAMMA_SENTINEL','PRIVATE_METADATA_SENTINEL','private_alpha','private_beta','private.dot.name','private_gamma',$tmp)) {
        if ($raw.Contains($private)) { throw 'Private config detail or path leaked in the inventory.' }
    }

    $rejected = $false
    try {
        $null = & $scriptPath -CodexHome $codexRoot -ProjectDirectory $nested -CandidatePath (Join-Path $tmp 'missing.md') -AsJson
    } catch {
        $rejected = $true
    }
    if (-not $rejected) { throw 'Nonexistent optional candidate was not rejected.' }

    Write-Host '[OK] Global, inherited project and override-file sizes.'
    Write-Host '[OK] Four MCP servers vs nine headers (nested env/metadata/HTTP blocks) and quoted dotted names.'
    Write-Host '[OK] MCP/role counts without leaking secrets, server names or local paths.'
    Write-Host '[OK] Candidate comparison and missing-file negative case.'
    Write-Host 'PASS: Static Codex context footprint inventory regression.'
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force
}
