$ErrorActionPreference = 'Continue'

$ClaudeHome = Join-Path $env:USERPROFILE '.claude'
$SettingsPath = Join-Path $ClaudeHome 'settings.json'
$ClaudeMdPath = Join-Path $ClaudeHome 'CLAUDE.md'
$EfficiencyPath = Join-Path $ClaudeHome 'CLAUDE_CONTEXT_EFFICIENCY.md'
$AgentsHome = Join-Path $ClaudeHome 'agents'
$ok = $true

Write-Host '=== Claude Pro Context-Efficiency Stack Verification ==='
Write-Host "Claude home: $ClaudeHome"

Write-Host "`n[Claude Code]"
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
    $version = (& claude --version 2>$null | Out-String).Trim()
    Write-Host "[OK] $version"
} else {
    Write-Host '[--] claude not found in PATH'
    $ok = $false
}

Write-Host "`n[Settings]"
$settings = $null
if (Test-Path $SettingsPath -PathType Leaf) {
    try {
        $settings = Get-Content $SettingsPath -Raw | ConvertFrom-Json
        Write-Host '[OK] settings.json parses as JSON'
    } catch {
        Write-Host '[--] settings.json is invalid JSON'
        $ok = $false
    }
} else {
    Write-Host '[--] settings.json missing'
    $ok = $false
}

if ($settings) {
    if ($settings.model -eq 'sonnet') { Write-Host '[OK] default model = sonnet' } else { Write-Host '[--] default model is not sonnet'; $ok = $false }
    if ($settings.ultracode -eq $false) { Write-Host '[OK] ultracode disabled by default' } else { Write-Host '[--] ultracode is not explicitly false'; $ok = $false }
    if ($settings.env.CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS -eq '2') { Write-Host '[OK] concurrent subagents = 2' } else { Write-Host '[--] concurrent subagent limit mismatch'; $ok = $false }
    if ($settings.env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH -eq '1') { Write-Host '[OK] nested spawning disabled' } else { Write-Host '[--] subagent spawn depth mismatch'; $ok = $false }
}

Write-Host "`n[Global instructions]"
if ((Test-Path $EfficiencyPath -PathType Leaf) -and (Test-Path $ClaudeMdPath -PathType Leaf)) {
    $hasImport = Select-String -Path $ClaudeMdPath -Pattern '^@CLAUDE_CONTEXT_EFFICIENCY\.md\s*$' -Quiet
    if ($hasImport) { Write-Host '[OK] CLAUDE.md imports context-efficiency instructions' } else { Write-Host '[--] CLAUDE.md import missing'; $ok = $false }
} else {
    Write-Host '[--] global context-efficiency instruction file missing'
    $ok = $false
}

Write-Host "`n[Agents]"
$expected = [ordered]@{
    'Explore'       = @('haiku', $null)
    'haiku-low'     = @('haiku', $null)
    'sonnet-medium' = @('sonnet', 'medium')
    'sonnet-high'   = @('sonnet', 'high')
    'opus-high'     = @('opus', 'high')
    'opus-xhigh'    = @('opus', 'xhigh')
}
foreach ($name in $expected.Keys) {
    $path = Join-Path $AgentsHome "$name.md"
    if (-not (Test-Path $path -PathType Leaf)) {
        Write-Host "[--] missing agent: $name"
        $ok = $false
        continue
    }
    $model = $expected[$name][0]
    $effort = $expected[$name][1]
    $modelOk = Select-String -Path $path -Pattern ("^model:\s*{0}\s*$" -f [regex]::Escape($model)) -Quiet
    $effortOk = $true
    if ($effort) { $effortOk = Select-String -Path $path -Pattern ("^effort:\s*{0}\s*$" -f [regex]::Escape($effort)) -Quiet }
    if ($modelOk -and $effortOk) { Write-Host "[OK] $name -> $model$(if ($effort) { " / $effort" })" } else { Write-Host "[--] $name has unexpected model/effort"; $ok = $false }
}

Write-Host "`n[RTK]"
$rtk = Get-Command rtk -ErrorAction SilentlyContinue
if ($rtk) {
    $rtkVersion = (& rtk --version 2>$null | Out-String).Trim()
    Write-Host "[OK] $rtkVersion"
    & rtk gain 2>$null | Select-Object -First 12
} else {
    Write-Host '[INFO] RTK not found; stack works, but terminal-output compression is not active.'
}

Write-Host "`n[Code Review Graph]"
$crg = Get-Command code-review-graph -ErrorAction SilentlyContinue
if ($crg) {
    Write-Host '[OK] code-review-graph available'
    & code-review-graph status 2>$null | Select-Object -First 20
} else {
    Write-Host '[INFO] code-review-graph not found; install/configure it per project when useful.'
}

if ($claude -and (Test-Path $AgentsHome -PathType Container)) {
    Write-Host "`n[Suggested Claude diagnostics]"
    Write-Host "Run inside Claude Code: /status, /context, /tasks"
    Write-Host "Optional prompt audit: /doctor prompt-audit"
}

Write-Host ''
if ($ok) {
    Write-Host 'PASS: Claude Pro context-efficiency stack is installed and internally consistent.'
    exit 0
} else {
    Write-Host 'FAIL: one or more required stack components are missing or inconsistent.'
    exit 1
}
