[CmdletBinding()]
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

# Read-only PowerShell 5.1+ parser gate. It never runs the tested scripts.
$ErrorActionPreference = 'Stop'
$scriptDir = Join-Path $Root 'scripts'
if (-not (Test-Path -LiteralPath $scriptDir -PathType Container)) {
    throw "Scripts directory missing: $scriptDir"
}
$files = @(Get-ChildItem -LiteralPath $scriptDir -File -Filter '*.ps1' | Sort-Object Name)
if ($files.Count -eq 0) { throw "No .ps1 files found in $scriptDir" }

$failed = $false
foreach ($file in $files) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $file.FullName, [ref]$tokens, [ref]$errors
    )
    if ($errors -and $errors.Count -gt 0) {
        $failed = $true
        Write-Host "[FAIL] $($file.Name)"
        foreach ($issue in $errors) {
            Write-Host ("  line {0}, col {1}: {2}" -f $issue.Extent.StartLineNumber, $issue.Extent.StartColumnNumber, $issue.Message)
        }
    } else {
        Write-Host "[OK] $($file.Name)"
    }
}

if ($failed) {
    throw 'One or more PowerShell scripts contain syntax errors. This check is read-only.'
}
Write-Host "PASS: Parsed $($files.Count) script(s); no syntax errors."
