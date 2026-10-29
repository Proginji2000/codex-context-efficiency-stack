#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'Invoke-CodexABTuiQualified.ps1'
if (-not (Test-Path -LiteralPath $script)) {
    throw 'QUALIFIED_LAUNCHER_NOT_FOUND'
}

# Only tests the interpreter probe; never invokes Codex, a model or a pilot.
& $script -ProbeOnly
if (-not $?) { throw 'PYTHON_PROBE_FAILED' }

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
