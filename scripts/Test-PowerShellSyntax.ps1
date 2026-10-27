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
    # Windows PowerShell 5.1 reads BOM-less .ps1 files using the system ANSI
    # code page. UTF-8 smart punctuation can become a quote character and
    # silently break parsing. Our GitHub scripts must be ASCII or use a BOM.
    $rawBytes = [System.IO.File]::ReadAllBytes($file.FullName)
    $utf8Bom = ($rawBytes.Length -ge 3 -and $rawBytes[0] -eq 0xEF -and $rawBytes[1] -eq 0xBB -and $rawBytes[2] -eq 0xBF)
    $utf16Bom = ($rawBytes.Length -ge 2 -and (
        ($rawBytes[0] -eq 0xFF -and $rawBytes[1] -eq 0xFE) -or
        ($rawBytes[0] -eq 0xFE -and $rawBytes[1] -eq 0xFF)
    ))
    if (-not $utf8Bom -and -not $utf16Bom) {
        $unsafeByte = $false
        foreach ($rawByte in $rawBytes) {
            if ($rawByte -gt 127) {
                $unsafeByte = $true
                break
            }
        }
        if ($unsafeByte) {
            $failed = $true
            Write-Host "[FAIL] $($file.Name): Non-ASCII bytes without a BOM (unsafe on Windows PowerShell 5.1). Use ASCII source text or save as UTF-8 with BOM."
            continue
        }
    }

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
