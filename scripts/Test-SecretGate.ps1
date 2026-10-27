[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [switch]$History
)

# Explicit local secret-detection gate: read-only and fully redacted output.
# Exit 0 = no findings, 1 = findings, 2 = setup / scanner failure.
$ErrorActionPreference = 'Stop'
$scanner = Get-Command gitleaks -ErrorAction SilentlyContinue
if (-not $scanner) {
    Write-Error 'Gitleaks is not on PATH. Install with: winget install -e --id Gitleaks.Gitleaks'
    exit 2
}
if (-not (Test-Path -LiteralPath $RepositoryPath -PathType Container)) {
    Write-Error "Not a directory: $RepositoryPath"
    exit 2
}
$root = (Resolve-Path -LiteralPath $RepositoryPath).Path
if ($History) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Error 'Git is required for a history scan.'
        exit 2
    }
    $commandName = 'git'
    Write-Host "[INFO] Gitleaks: scanning Git history under $root (read-only)."
} else {
    $commandName = 'dir'
    Write-Host "[INFO] Gitleaks: scanning current files under $root (read-only)."
}

& $scanner.Source $commandName --redact=100 --no-banner --log-level=error $root
$result = $LASTEXITCODE
switch ($result) {
    0 { Write-Host '[OK] No matching leaked secrets detected.'; exit 0 }
    1 { Write-Host '[FAIL] Potential secrets detected. Do not publish; review and rotate confirmed credentials.'; exit 1 }
    default { Write-Error "Gitleaks failed with exit code $result (not a clean pass)."; exit 2 }
}
