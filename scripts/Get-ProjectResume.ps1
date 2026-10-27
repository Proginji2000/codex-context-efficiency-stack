[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [ValidateRange(1, 50)][int]$MaxLines = 12
)

# Read-only, bounded project snapshot for a delegated resume/reconnaissance worker.
# Does not checkout, merge, reset, fetch, pull, write or launch agents.
$ErrorActionPreference = 'Stop'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git is required.' }
$rootResult = @(& git -C $RepositoryPath rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or $rootResult.Count -eq 0) { throw "Not a Git working tree: $RepositoryPath" }
$root = $rootResult[0].Trim()

Write-Output "=== READ-ONLY PROJECT RESUME ==="
Write-Output "Root: $root"
$head = @(& git -C $root rev-parse --short=12 HEAD 2>$null)
$branch = @(& git -C $root branch --show-current 2>$null)
$last = @(& git -C $root log -1 --format='%h %cd %s' --date=short 2>$null)
Write-Output ("HEAD: " + ($head -join ''))
Write-Output ("Branch: " + $(if ($branch) { $branch -join '' } else { '(detached)' }))
Write-Output ("Latest commit: " + ($last -join ''))

Write-Output "--- Working tree (bounded, no untracked file contents) ---"
$status = @(& git -C $root status --short --untracked-files=normal 2>$null)
if ($status.Count -eq 0) {
    Write-Output '(clean)'
} else {
    $status | Select-Object -First $MaxLines | ForEach-Object { Write-Output $_ }
    if ($status.Count -gt $MaxLines) { Write-Output ("... " + ($status.Count - $MaxLines) + ' more entries omitted') }
}

Write-Output "--- Worktrees (bounded) ---"
$worktrees = @(& git -C $root worktree list 2>$null)
$worktrees | Select-Object -First $MaxLines | ForEach-Object { Write-Output $_ }
if ($worktrees.Count -gt $MaxLines) { Write-Output '... additional worktrees omitted' }

Write-Output "--- Known state and planning files (names only) ---"
$names = @('STATE.md', 'PLANS.md', 'docs/STATE.md', 'docs/ROADMAP.md', 'ROADMAP.md')
$found = $false
foreach ($name in $names) {
    $path = Join-Path $root $name
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $found = $true
        Write-Output $name
    }
}
if (-not $found) { Write-Output '(none at conventional locations; do not create one automatically)' }
Write-Output 'Worker must reconcile any state document with live Git facts and current tests before proposing edits.'
