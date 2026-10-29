#requires -Version 5.1
<#
.SYNOPSIS
  Fail-closed P1.1 TUI preflight from Windows PowerShell; never installs Python.
.DESCRIPTION
  Resolve a real Python >=3.11 interpreter (not a broken WindowsApps alias).
  Run offline tests, diagnose and both arm policy checks before optionally
  starting ONE baseline canary. ProbeOnly never touches pilot nor a model.
  All operations execute in a single script: failure stops subsequent gates.
#>
[CmdletBinding()]
param(
    [string]$Pilot,
    [string]$PythonExe,
    [switch]$ProbeOnly,
    [switch]$RunBaseline,
    [string]$Output
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($ProbeOnly -and $RunBaseline) { throw 'STOP: INVALID_MODE_COMBINATION' }
if (-not $ProbeOnly -and [string]::IsNullOrWhiteSpace($Pilot)) {
    throw 'STOP: PILOT_REQUIRED'
}
if ($RunBaseline -and [string]::IsNullOrWhiteSpace($Output)) {
    throw 'STOP: FRESH_OUTPUT_REQUIRED'
}

function Test-PythonRuntime {
    param([string]$CommandPath, [string[]]$Prefix = @())
    if ([string]::IsNullOrWhiteSpace($CommandPath) -or
        -not (Test-Path -LiteralPath $CommandPath -PathType Leaf)) {
        return $null
    }
    try {
        $probeArgs = @($Prefix) + @(
            '-c',
            'import sys,tomllib;print(sys.executable if sys.version_info >= (3,11) else None)'
        )
        $lines = @(& $CommandPath @probeArgs 2>$null)
        $code = $LASTEXITCODE
        if ($code -ne 0) { return $null }
        foreach ($line in $lines) {
            $line = [string]$line
            $resolved = $line.Trim()
            if ([System.IO.Path]::IsPathRooted($resolved) -and
                [System.IO.Path]::GetExtension($resolved).Equals(
                    '.exe', [System.StringComparison]::OrdinalIgnoreCase) -and
                (Test-Path -LiteralPath $resolved -PathType Leaf)) {
                return $resolved
            }
        }
    }
    catch { return $null }
    return $null
}

function Resolve-QualifiedPython {
    param([string]$ExplicitPythonExe)
    $candidates = New-Object 'System.Collections.Generic.List[object]'

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPythonExe)) {
        $path = [System.IO.Path]::GetFullPath($ExplicitPythonExe)
        $candidates.Add([pscustomobject]@{ Path = $path; Prefix = @() })
    }
    else {
        foreach ($name in @('py.exe', 'py')) {
            foreach ($command in @(Get-Command $name -All -ErrorAction SilentlyContinue)) {
                if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
                    foreach ($version in @('-3.13', '-3')) {
                        $candidates.Add([pscustomobject]@{
                            Path = [string]$command.Source
                            Prefix = @($version)
                        })
                    }
                }
            }
        }
        foreach ($name in @('python.exe', 'python3.exe')) {
            foreach ($command in @(Get-Command $name -All -ErrorAction SilentlyContinue)) {
                if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
                    $candidates.Add([pscustomobject]@{
                        Path = [string]$command.Source
                        Prefix = @()
                    })
                }
            }
        }
        foreach ($root in @($env:LOCALAPPDATA, $env:ProgramFiles)) {
            if ([string]::IsNullOrWhiteSpace($root)) { continue }
            foreach ($ver in @('Python313', 'Python314', 'Python312', 'Python311')) {
                foreach ($path in @(
                    (Join-Path $root ('Programs\Python\' + $ver + '\python.exe')),
                    (Join-Path $root ($ver + '\python.exe'))
                )) {
                    $candidates.Add([pscustomobject]@{ Path = $path; Prefix = @() })
                }
            }
        }
    }

    foreach ($candidate in $candidates) {
        $path = Test-PythonRuntime -CommandPath $candidate.Path -Prefix $candidate.Prefix
        if (-not [string]::IsNullOrWhiteSpace($path)) {
            # A launcher may resolve to a different executable; verify direct launch.
            $direct = Test-PythonRuntime -CommandPath $path
            if ($null -ne $direct -and
                $direct.Equals($path, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $direct
            }
        }
    }
    throw 'STOP: PYTHON_INTERPRETER_UNAVAILABLE_OR_ALIAS_ONLY'
}

function Invoke-PythonRequired {
    param([string]$Interpreter, [string]$Script, [string[]]$Arguments,
          [string]$FailureCode)
    & $Interpreter $Script @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('STOP: ' + $FailureCode) }
}

$interpreter = Resolve-QualifiedPython -ExplicitPythonExe $PythonExe
Write-Host 'PYTHON_INTERPRETER_VERIFIED (Python >=3.11; direct execution passed).'
if ($ProbeOnly) {
    Write-Host 'PROBE_PASS: no Codex CLI or model calls.'
    return
}

$tui = Join-Path $PSScriptRoot 'Run-CodexAB-TUI-Canary.py'
$tests = Join-Path $PSScriptRoot 'Test-Run-CodexAB-TUI-Canary.py'
if (-not (Test-Path -LiteralPath $tui -PathType Leaf) -or
    -not (Test-Path -LiteralPath $tests -PathType Leaf)) {
    throw 'STOP: TUI_SCRIPTS_NOT_FOUND'
}
Invoke-PythonRequired -Interpreter $interpreter -Script $tests -Arguments @() -FailureCode 'OFFLINE_TESTS_FAILED'

$raw = @(& $interpreter $tui diagnose --pilot $Pilot)
if ($LASTEXITCODE -ne 0) { throw 'STOP: DIAGNOSE_PROCESS_FAILED' }
$raw | Out-Host
try { $diag = ($raw -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'STOP: DIAGNOSE_RESPONSE_INVALID' }
if ($null -eq $diag -or $diag.preflight_ready -ne $true) {
    throw 'STOP: V4_PROFILE_NOT_READY_NO_MODEL_LAUNCHED'
}

foreach ($arm in @('baseline', 'candidate')) {
    Invoke-PythonRequired -Interpreter $interpreter -Script $tui -Arguments @('policy', '--pilot', $Pilot, '--arm', $arm) -FailureCode ('POLICY_' + $arm.ToUpperInvariant() + '_FAILED')
}
Write-Host 'PREFLIGHT_PASS: tests, diagnostic, both arm policies.'
if (-not $RunBaseline) {
    Write-Host 'NO_MODEL_LAUNCHED: add -RunBaseline and -Output for one explicit test.'
    return
}
if (Test-Path -LiteralPath $Output) { throw 'STOP: OUTPUT_ALREADY_EXISTS' }

Invoke-PythonRequired -Interpreter $interpreter -Script $tui -Arguments @(
    'run', '--pilot', $Pilot, '--arm', 'baseline', '--output', $Output,
    '--approval', 'never', '--windows-sandbox', 'mxc',
    '--python-test-fallback-hint', '--execute'
) -FailureCode 'BASELINE_TUI_FAILED'
Write-Host 'BASELINE_TUI_WRAPPER_PASS: inspect worker lifecycle separately.'
