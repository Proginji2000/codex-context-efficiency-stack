# Claude Pro context-efficiency stack

This repository now contains an opt-in Claude Code stack alongside the existing Codex stack.

Start here: [`docs/CLAUDE_PRO_STACK.md`](docs/CLAUDE_PRO_STACK.md).

Windows quick start:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\install-claude-pro-stack.ps1
pwsh -ExecutionPolicy Bypass -File .\scripts\verify-claude-pro-stack.ps1
```

To also install missing RTK / Code Review Graph dependencies and configure CRG for the repository you are currently in:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\install-claude-pro-stack.ps1 -InstallDependencies -ConfigureCurrentRepository
```

The default lane is Sonnet. Haiku is used for cheap exploration and tiny work; Opus is reserved for escalation. Fable is never selected automatically by this stack.
