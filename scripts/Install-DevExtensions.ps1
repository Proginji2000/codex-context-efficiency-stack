[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Playwright','Context7','Gitleaks')]
    [string[]]$Components = @('Playwright','Context7','Gitleaks')
)

# Explicit one-time installer. Does NOT run browser tasks, scan repositories,
# access private project files, or activate Shannon.
$ErrorActionPreference = 'Stop'
$componentsSelected = @($Components | Select-Object -Unique)
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$config = Join-Path $codexHome 'config.toml'

$needsMcp = $componentsSelected -contains 'Playwright' -or $componentsSelected -contains 'Context7'
if ($needsMcp) {
    $codex = Get-Command codex -ErrorAction SilentlyContinue
    if (-not $codex) { throw 'Codex CLI was not found. Install/repair Codex first.' }
    if (-not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) {
        throw 'npx.cmd is missing. Install Node.js/npm on Windows first.'
    }
    $rawList = (& $codex.Source mcp list 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "Could not list existing Codex MCP servers: $rawList" }
    if (Test-Path -LiteralPath $config -PathType Leaf) {
        $backupRoot = Join-Path $codexHome ('backups\mcp-extension-install-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
        if ($PSCmdlet.ShouldProcess($config, "Backup existing Codex config under $backupRoot")) {
            New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
            Copy-Item -LiteralPath $config -Destination (Join-Path $backupRoot 'config.toml') -Force
            Write-Host "[OK] Codex config backup: $backupRoot"
        }
    }
}

function Test-McpPresent([string]$Name, [string]$ListText) {
    # Codex prints an aligned table with a 'Name' column. Never overwrite a
    # registered server automatically, even if its command differs.
    return ($ListText -match ('(?im)^\s*' + [regex]::Escape($Name) + '\s+'))
}

if ($componentsSelected -contains 'Playwright') {
    if (Test-McpPresent 'playwright' $rawList) {
        Write-Host '[OK] Playwright MCP already registered; left unchanged.'
    } elseif ($PSCmdlet.ShouldProcess('~/.codex/config.toml', 'Register isolated headless Playwright MCP')) {
        & $codex.Source mcp add playwright -- cmd.exe /c npx.cmd -y @playwright/mcp@latest --browser=msedge --isolated --headless
        if ($LASTEXITCODE -ne 0) { throw 'Playwright MCP registration failed.' }
        Write-Host '[OK] Registered Playwright MCP; first use may download its npm package.'
    }
}

if ($componentsSelected -contains 'Context7') {
    if (Test-McpPresent 'context7' $rawList) {
        Write-Host '[OK] Context7 MCP already registered; left unchanged.'
    } elseif ($PSCmdlet.ShouldProcess('~/.codex/config.toml', 'Register rate-limited Context7 MCP without any stored key')) {
        & $codex.Source mcp add context7 -- cmd.exe /c npx.cmd -y @upstash/context7-mcp@latest
        if ($LASTEXITCODE -ne 0) { throw 'Context7 MCP registration failed.' }
        Write-Host '[OK] Registered Context7 MCP. Anonymous limits may apply.'
    }
}

if ($componentsSelected -contains 'Gitleaks') {
    if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
        Write-Host '[OK] Gitleaks already installed; left unchanged.'
    } else {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            throw 'WinGet is missing. Install Gitleaks manually from the official releases.'
        }
        if ($PSCmdlet.ShouldProcess('Gitleaks.Gitleaks', 'Install Gitleaks with WinGet')) {
            & winget install --id Gitleaks.Gitleaks --exact --source winget --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -ne 0) { throw 'WinGet did not successfully install Gitleaks.' }
            Write-Host '[OK] WinGet completed. Open a new PowerShell to refresh PATH before running gitleaks.'
        }
    }
}

Write-Host '[INFO] No repository has been scanned or modified. No Shannon scan has been launched.'
Write-Host '[INFO] Restart Codex and use codex mcp list, then verify with scripts/verify-stack.ps1.'
Write-Host '[INFO] Registered MCP does not equal a successful connection; run an isolated, owned-app test.'
