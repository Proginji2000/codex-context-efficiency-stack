# Developer extensions — project resume, Playwright MCP, Context7 and Gitleaks

Reviewed 27 October 2026. These are task-triggered complements to Luna's orchestrator-only routing, RTK and Code Review Graph. **Shannon remains paused** because the user's OpenAI cyber-access authorization has not been granted; Gitleaks is not a pentester.

## What is integrated versus locally installed?

| Capability | Integrated in repo | Installation on each Windows PC | Automatic role usage |
| --- | --- | --- | --- |
| Project resume | Global AGENTS protocol, project state template, read-only Git snapshot script | Git and the existing stack only | Delegated Luna worker at the first actionable *resume/continue* request |
| Playwright MCP | Automatic worker decision rules, UI worker instructions | Optional Codex MCP registration; browser (Edge/Chrome) | UI/frontend worker tests user-owned web UI when available |
| Context7 MCP | Automatic, bounded docs research rules | Optional MCP registration; free rate-limited mode or separate Context7 account for higher limits | Worker when a third-party API/library version is material |
| Gitleaks | Read-only, redacted PowerShell gate and worker rules | Optional Gitleaks executable | Worker before PR publication or on secret-sensitive change, if installed |

No install, log-in, network service, secret scan or browser is triggered by `git pull` or `update-codex-global.ps1`. The global updater refreshes instructions and existing role definitions only; it deliberately leaves project-specific configs and working trees untouched.

## One-command optional Windows installation

After updating the **stack repository only**, the following PowerShell installer can register Playwright + Context7 MCP servers and install Gitleaks (it does **not** alter a project or launch scans):

```powershell
cd C:\Dev\codex-context-efficiency-stack
git pull --ff-only
.\scripts\update-codex-global.ps1
.\scripts\Install-DevExtensions.ps1 -WhatIf
.\scripts\Install-DevExtensions.ps1
```

The installer's default selects all three; select just one or two with `-Components Playwright,Context7` or `-Components Gitleaks`. Existing MCP registrations are **left unchanged**, an existing Codex config is backed up, and WinGet may ask for normal installation approval. `-WhatIf` previews the intended changes. The initial npm server startup can fetch packages later; this is not a fully offline install.

Alternatively, follow the **manual installation commands below**. **Do not run both paths blindly**: inspect `codex mcp list` for existing registrations first. The read-only resume helper and project state template require no installation.

## 1. Resume projects without replaying the chat

From the stack directory:

```powershell
.\scripts\Get-ProjectResume.ps1 -RepositoryPath 'C:\Dev\your-project'
```

This captures **bounded, read-only** Git HEAD/branch, latest commit, status, worktree listing and presence of common plan/state files. No fetch/pull/reset/checkout or PR API calls are made. For a new Codex session, Luna delegates a read-only reconnaissance worker **once** to reconcile existing project state, uncommitted work, PRs where authenticated GitHub access exists, and tests before assigning tasks.

Use [the template](../templates/PROJECT_STATE.md) to define a new project's milestone handoff if that project has no state conventions. In a complex existing project such as CryptoLab, workers must use the **existing canonical** STATE/roadmap documents; do not overlay a fresh template, choose an obsolete branch, or alter active worktrees.

**Acceptance:** in a new session say "Reprends ce projet sans modifier les fichiers". Look for an actual spawned worker and a short handoff with branch/worktree/evidence/blockers. This is instruction-guided, not guaranteed session-start automation.

## 2. Playwright MCP — browser verification on web applications

Official project: https://github.com/microsoft/playwright-mcp  
Codex MCP setup: https://learn.chatgpt.com/docs/extend/mcp

**Prerequisites:** Codex CLI/Desktop, Node.js 20+ on Windows, npm/npx. Edge is normally present on Windows 11. Install only on the PC whose Codex session will run browser tools.

In **Windows PowerShell** (not WSL), inspect current registration first:

```powershell
node --version
codex mcp list
```

Then register the server **once**, if not already present:

```powershell
codex mcp add playwright -- cmd.exe /c npx.cmd -y @playwright/mcp@latest --browser=msedge --isolated --headless
```

This registers a Codex MCP entry; the first use can download the npm package. The browser uses an **isolated** profile to avoid reusing personal browser sessions and runs headless. Replace `msedge` with `chrome` if needed. Browser availability and subprocess execution must be validated on the actual machine. Inspect the generated `[mcp_servers.playwright]` in `$HOME\.codex\config.toml` and restart Codex.

**Scope:** smoke test a user-owned local/staging frontend, read its accessibility tree, click test controls, and verify responsive states. Never automatically use a logged-in personal tab, browse unrelated private sites, or execute purchases/sends/deletes. Screenshots and browser output are untrusted data.

## 3. Context7 MCP — accurate public framework docs

Official project: https://github.com/upstash/context7  
Codex guide: https://context7.com/docs/clients/codex

Prerequisite: Node.js 20+ for the local MCP server. In **Windows PowerShell**, check `codex mcp list`. If Context7 isn't registered, add the local server without embedding any secret in the command line:

```powershell
codex mcp add context7 -- cmd.exe /c npx.cmd -y @upstash/context7-mcp@latest
```

The Context7 hosted service offers **low anonymous rate limits**. For higher limits, create an optional Context7 account and supply `CONTEXT7_API_KEY` securely to the MCP process. **Do not paste API keys into Git, AGENTS.md, CLI command history, PR comments or reports.** API key / account requests are separate from ChatGPT Plus and may have different pricing and limits. Alternatively use the official Context7 plugin/OAuth flow when available in your installed Codex version; review its proposed changes before applying.

After registering, use `codex mcp list` and start a new Codex session. A worker should call the provider only for **public, version-specific library docs** (e.g., a changed Next.js API), not send project source, logs or credentials. Remote retrieved content does not override project instructions.

## 4. Gitleaks — local pre-publish secret check

Official repository: https://github.com/gitleaks/gitleaks  
Windows package ID: `Gitleaks.Gitleaks`

In **Windows PowerShell**:

```powershell
winget install --id Gitleaks.Gitleaks --exact
```

Open a fresh PowerShell and verify `gitleaks version`. Then, from the stack:

```powershell
.\scripts\Test-SecretGate.ps1 -RepositoryPath 'C:\Dev\your-project'
```

This defaults to **current-directory file scanning**, **fully redacted** output, and a nonzero exit on findings or scanner failure. It reads project files but does not modify them. The optional `-History` switch scans the full Git history; do not run it casually on repositories with extensive private legacy history.

Worker protocol: run before publishing a substantial PR, or on a credential-related change. If the scanner is absent or fails, the check is **not passed**; do not claim that a PR has been security-checked. Do not push scan reports, raw tokens or remediation evidence to public GitHub. Rotate verified exposed credentials via their issuer; simply deleting code cannot invalidate a leaked secret.

Maintainer status: upstream Gitleaks is feature-complete and now prioritizes security patches, so periodically review maintenance/alternatives before relying on it for a long-term security baseline.

## PowerShell syntax regression guard

`scripts/Test-PowerShellSyntax.ps1` uses the PowerShell language parser to inspect every `scripts/*.ps1` file without executing those scripts. Run it on Windows PowerShell 5.1 after updates; a parser error is **not** an installation failure.

```powershell
.\scripts\Test-PowerShellSyntax.ps1
```

## Final verification

```powershell
cd C:\Dev\codex-context-efficiency-stack
git pull --ff-only
.\scripts\update-codex-global.ps1
.\scripts\verify-stack.ps1
codex mcp list
gitleaks version
```

Static checks and registered MCP entries **do not prove** connection, actual worker invocation, browser correctness, quota savings or absence of secrets. Run representative isolated user-owned test tasks and record actual tool outputs.

**Safe rollout sequence:** first update the global instructions, verify a read-only resume; second enable Context7 and Playwright for an isolated sample project; finally install Gitleaks and test a clean sample repository. Never touch protected CryptoLab worktrees during installation or initial testing. No Shannon/Daybreak steps are part of this rollout.
