#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'Invoke-CodexABTuiQualified.ps1'
if (-not (Test-Path -LiteralPath $script)) {
    throw 'QUALIFIED_LAUNCHER_NOT_FOUND'
}

# Only tests the interpreter probe; never invokes Codex, a model or a pilot.
$python = @(Get-Command python.exe -All -CommandType Application -ErrorAction Stop) |
    Where-Object { Test-Path -LiteralPath $_.Source -PathType Leaf } |
    Select-Object -First 1
if ($null -eq $python) { throw 'CI_PYTHON_APP_MISSING' }
Write-Host ('CI_PYTHON_RESOLUTION: application=' + [bool]($python.Source) +
            ' path_exists=' + (Test-Path -LiteralPath $python.Source -PathType Leaf))
& $script -ProbeOnly -PythonExe $python.Source
if (-not $?) { throw 'PYTHON_DIRECT_PROBE_FAILED' }

& $script -ProbeOnly
if (-not $?) { throw 'PYTHON_AUTO_PROBE_FAILED' }

$missing = Join-Path $env:TEMP 'codex-ab-nonexistent-interpreter-000000.exe'
if (Test-Path -LiteralPath $missing) { throw 'TEST_PRECONDITION_FAILED' }
try {
    & $script -ProbeOnly -PythonExe $missing
    throw 'EXPECTED_PYTHON_PROBE_REFUSAL'
}
catch {
    if ($_.Exception.Message -notmatch 'PYTHON_INTERPRETER_UNAVAILABLE_OR_ALIAS_ONLY') {
        throw
    }
}

# Fail before resolving Python or launching a model on unsafe option combos.
try {
    & $script -ProbeOnly -RunBaseline -Output 'DO_NOT_CREATE'
    throw 'EXPECTED_MODE_REFUSAL'
}
catch {
    if ($_.Exception.Message -notmatch 'INVALID_MODE_COMBINATION') { throw }
}
try {
    & $script -RunBaseline -Pilot 'DO_NOT_TOUCH' 
    throw 'EXPECTED_OUTPUT_REFUSAL'
}
catch {
    if ($_.Exception.Message -notmatch 'FRESH_OUTPUT_REQUIRED') { throw }
}
Write-Host 'Qualified TUI bootstrap synthetic PASS (no model, no pilot changes).'
