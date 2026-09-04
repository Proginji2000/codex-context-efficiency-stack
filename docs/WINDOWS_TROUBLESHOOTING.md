# Windows troubleshooting

## `code-review-graph` command not found

Confirm the Python package exists:

```powershell
python.exe -m pip show code-review-graph
python.exe -m pip --version
```

Find the Microsoft Store/user Scripts directory:

```powershell
$Scripts = python.exe -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))"
Get-ChildItem "$Scripts" -Filter "code-review-graph*"
```

Test directly:

```powershell
& "$Scripts\code-review-graph.exe" --help
```

Add to user PATH if necessary.

## Confirm Codex home

```powershell
Write-Host "USERPROFILE = $env:USERPROFILE"
Write-Host "CODEX_HOME  = $env:CODEX_HOME"

Test-Path "$env:USERPROFILE\.codex\config.toml"
Get-Item "$env:USERPROFILE\.codex\config.toml" -ErrorAction SilentlyContinue |
    Select-Object FullName, Length, LastWriteTime
```

Be careful with this typo:

```powershell
# Wrong: resolves like C:\Users\name.codex\...
"$env:USERPROFILE.codex\config.toml"

# Correct
"$env:USERPROFILE\.codex\config.toml"
```

## CRG build works but `update` fails

CRG incremental updates require Git diffing.

Typical error:

```text
Not in a git repository. 'update' requires git for diffing.
```

Options:

- use `build` for a non-Git directory, or
- initialize/version the project with Git, create a clean `.gitignore`, make a baseline commit, then rebuild CRG once.

After that, `code-review-graph update` can work incrementally.

## `Last updated: never`

Run a full build and confirm it reaches its final summary:

```powershell
code-review-graph build
code-review-graph status
```

A healthy status should have a real timestamp and, in Git repos, a branch/commit.

## `igraph not available`

Install the communities extra:

```powershell
python.exe -m pip install -U "code-review-graph[communities]"
```

Rebuild. A successful enriched build should mention Leiden/igraph community detection.

## Python enrichment

```powershell
python.exe -m pip install -U "code-review-graph[enrichment]"
```

This installs Jedi for Python call-resolution enrichment.
