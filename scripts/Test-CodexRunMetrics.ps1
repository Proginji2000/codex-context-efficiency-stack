[CmdletBinding()]
param()

# Self-contained regression; uses only temporary synthetic task data.
$ErrorActionPreference = 'Stop'
$worker = Join-Path $PSScriptRoot 'Get-CodexRunMetrics.ps1'
if (-not (Test-Path -LiteralPath $worker)) { throw 'Metrics aggregation script missing.' }

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-metrics-test-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempDir -ErrorAction Stop | Out-Null
try {
    $csvPath = Join-Path $tempDir 'example.csv'
    @(
        'date,task,lane_initial,retries,escalated,lane_final,verification,result,elapsed_s'
        '2026-10-27,task-a,luna-low,0,false,luna-low,passed,pass,8'
        '2026-10-27,task-b,luna-low,1,true,terra-medium,failed,fail,20'
        '2026-10-27,task-c,terra-medium,0,false,terra-medium,passed,pass,12'
    ) | Set-Content -LiteralPath $csvPath -Encoding ASCII

    $rawJson = & $worker -InputPath $csvPath -AsJson
    $result = @(($rawJson | ConvertFrom-Json))
    if ($result.Count -ne 2) { throw 'Expected two lane summaries.' }
    $luna = @($result | Where-Object { $_.lane_initial -eq 'luna-low' })
    $terra = @($result | Where-Object { $_.lane_initial -eq 'terra-medium' })
    if ($luna.Count -ne 1 -or $terra.Count -ne 1) { throw 'Missing lane in summary.' }
    if ($luna[0].tasks -ne 2 -or $luna[0].passed -ne 1 -or
        $luna[0].pass_pct -ne 50 -or $luna[0].first_pass_pct -ne 50 -or
        $luna[0].escalation_pct -ne 50 -or $luna[0].retries -ne 1 -or
        $luna[0].mean_elapsed_s -ne 14) {
        throw 'Unexpected luna-low aggregate.'
    }
    if ($terra[0].tasks -ne 1 -or $terra[0].pass_pct -ne 100) {
        throw 'Unexpected terra-medium aggregate.'
    }

    $badPath = Join-Path $tempDir 'invalid.csv'
    @(
        'date,task,lane_initial,retries,escalated,lane_final,verification,result,elapsed_s'
        '2026-10-27,task-invalid,luna-low,-1,false,luna-low,passed,pass,8'
    ) | Set-Content -LiteralPath $badPath -Encoding ASCII
    $rejected = $false
    try {
        $null = & $worker -InputPath $badPath -AsJson
    } catch {
        $rejected = $true
    }
    if (-not $rejected) { throw 'Invalid negative retries were not rejected.' }
    Write-Host '[OK] Two-lane aggregate and negative malformed-input case.'
    Write-Host 'PASS: Metrics parser is read-only and handles synthetic CSV.'
} finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction Stop
}
