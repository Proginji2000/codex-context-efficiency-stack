[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [switch]$AsJson
)

# Read-only aggregation of user-supplied, sanitized task-level measurements.
# Never reads Codex session files, auth data, telemetry or private worktrees.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
    throw "Metrics CSV not found: $InputPath"
}
$rows = @(Import-Csv -LiteralPath $InputPath)
if ($rows.Count -eq 0) {
    throw 'Metrics CSV contains no data rows.'
}

$required = @('date','task','lane_initial','retries','escalated','lane_final','verification','result','elapsed_s')
$fields = @($rows[0].PSObject.Properties.Name)
foreach ($field in $required) {
    if ($fields -notcontains $field) {
        throw "Missing required CSV column: $field"
    }
}

$allowedResults = @('pass','fail','blocked')
$allowedEscalation = @('true','false')
$valid = @()
foreach ($row in $rows) {
    $taskId = [string]$row.task
    if ([string]::IsNullOrWhiteSpace($taskId)) { throw 'A row has an empty task field.' }
    $retries = 0
    if (-not [int]::TryParse([string]$row.retries,[ref]$retries) -or $retries -lt 0) {
        throw "Invalid nonnegative integer retries for task: $taskId"
    }
    $elapsed = 0.0
    $elapsedText = ([string]$row.elapsed_s).Replace(',', '.')
    if (-not [double]::TryParse($elapsedText,
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref]$elapsed) -or [double]::IsNaN($elapsed) -or [double]::IsInfinity($elapsed) -or $elapsed -lt 0) {
        throw "Invalid nonnegative elapsed_s for task: $taskId"
    }
    $escalated = ([string]$row.escalated).ToLowerInvariant()
    $result = ([string]$row.result).ToLowerInvariant()
    if ($allowedEscalation -notcontains $escalated) { throw "Invalid escalated for task: $taskId" }
    if ($allowedResults -notcontains $result) { throw "Invalid result for task: $taskId" }
    if ([string]::IsNullOrWhiteSpace([string]$row.lane_initial) -or
        [string]::IsNullOrWhiteSpace([string]$row.lane_final)) {
        throw "Missing lane for task: $taskId"
    }
    $valid += [pscustomobject]@{
        task = $taskId
        lane_initial = [string]$row.lane_initial
        lane_final = [string]$row.lane_final
        retries = $retries
        escalated = ($escalated -eq 'true')
        result = $result
        elapsed_s = $elapsed
    }
}

$summary = @($valid | Group-Object -Property lane_initial | Sort-Object Name | ForEach-Object {
    $groupRows = @($_.Group)
    $total = $groupRows.Count
    $passed = @($groupRows | Where-Object { $_.result -eq 'pass' }).Count
    $firstPass = @($groupRows | Where-Object { $_.result -eq 'pass' -and $_.retries -eq 0 -and -not $_.escalated }).Count
    $blocked = @($groupRows | Where-Object { $_.result -eq 'blocked' }).Count
    $escalations = @($groupRows | Where-Object { $_.escalated }).Count
    $totalRetries = ($groupRows | Measure-Object -Property retries -Sum).Sum
    $avgSeconds = ($groupRows | Measure-Object -Property elapsed_s -Average).Average
    [pscustomobject]@{
        lane_initial = $_.Name
        tasks = $total
        passed = $passed
        blocked = $blocked
        pass_pct = [math]::Round(100.0 * $passed / $total, 1)
        first_pass_pct = [math]::Round(100.0 * $firstPass / $total, 1)
        escalation_pct = [math]::Round(100.0 * $escalations / $total, 1)
        retries = [int]$totalRetries
        mean_elapsed_s = [math]::Round($avgSeconds, 1)
    }
})

if ($AsJson) {
    ConvertTo-Json -InputObject $summary -Depth 3
} else {
    $summary | Format-Table -AutoSize | Out-String -Width 160 | Write-Output
}
