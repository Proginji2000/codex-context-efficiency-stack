# Optional integrations — vetted 27 October 2026

This file separates the **always-on foundation** from optional, task-specific tools. None of these four additions should be auto-invoked on every prompt. The Luna parent remains an orchestrator and delegates substantive work to bounded agents.

## Existing foundation (unchanged)

| Component | Purpose | Default |
| --- | --- | --- |
| RTK | Keep terminal output from bloating model context | Retained |
| Code Review Graph (CRG) | Narrow code/symbol/dependency exploration | Retained when an index is available |
| Luna/Terra/Sol/Astra workers | Route tasks by capability and quota | Retained |
| Deterministic compiler/tests/lint/diff | Establish completion evidence | Required by relevant acceptance gates |

RTK and CRG do **not** implement feature specification, visual design, penetration testing, or disk-space-efficient extraction. The additions below are complementary rather than replacements.

## 1. GitHub Spec Kit — recommended, per-project opt-in

Source: https://github.com/github/spec-kit  
Codex integration: https://github.com/github/spec-kit/blob/main/docs/integrations/codex.md  
Installation: https://github.com/github/spec-kit/blob/main/docs/installation.md

**Use when:** creating a feature with ambiguous requirements, multiple milestones, formal acceptance criteria, or a multi-agent dependency graph. Avoid full spec-driven ceremony for a typo or a one-line fix.

- Supported Codex integration key: `codex`.
- The current integration writes skills to `.agents/skills/speckit-<command>/SKILL.md`.
- Typical stages: constitution -> specification -> plan -> tasks -> implementation -> convergence.
- Spec Kit produces planning artifacts; it **does not replace** the runtime Luna orchestrator, role assignment, worktree isolation, review gates or deterministic tests.
- Installing a project integration may modify project files including `.codex/config.toml` / event handlers. Review the changes before committing. Never bootstrap directly into a sensitive active branch/worktree.

Prerequisites on Windows: Python 3.11+, `uv` (or pipx/pip), Git and Codex. Optional CLI installation:

```powershell
uv tool install specify-cli
specify version
```

For a **new** disposable pilot repository:

```powershell
specify init speckit-pilot --integration codex --script ps
```

For an **existing Spec Kit** project, per the official integration docs:

```powershell
specify integration install codex
```

Do not run `specify init --here --force` inside CryptoLab (or any ongoing project) as part of this stack update. Review changes and permissions before enabling optional event handlers. Skill selection in Codex uses a dollar prefix such as `$speckit-specify`.

## 2. Anthropic frontend-design — integrated as an optional Codex skill

Original: https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md  
License: Apache 2.0 (`LICENSE.txt` distributed alongside the skill).

The **unmodified upstream skill and license** are vendored at `.agents/skills/frontend-design/`. Codex discovers that repo-scoped skill when this stack repository itself is open.

To make it available across your local Windows Codex projects, **explicitly opt in**:

```powershell
cd C:\Dev\codex-context-efficiency-stack
.\scripts\install-frontend-design.ps1
```

Target: `$HOME\.agents\skills\frontend-design\`. If a conflicting user skill is present, the installer stops. An intentional replacement uses `-Force` after reviewing the changes; a timestamped backup is saved first.

In Codex, ask an implementation/UI worker to use `$frontend-design` for a new dashboard, web page, landing page, or major UI redesign. For nonvisual Rust, CLI, SQL, or tests, don't load it. The skill is visual/design guidance, **not** a UI test framework; still run accessibility, build and responsive screenshot checks.

**Licensing and provenance:** this copy comes from Anthropic's `anthropics/skills`, `skills/frontend-design`, Apache 2.0. Preserve `LICENSE.txt` if redistributing. The stack does not claim authorship of the upstream skill.

## 3. Keygraph Shannon — restricted, manual security audit only

Source: https://github.com/KeygraphHQ/shannon  
Provider guide: https://github.com/KeygraphHQ/shannon/blob/main/docs/ai-providers.md  
License: AGPL-3.0.

**Shannon is an active exploit-based pentester** for running web applications and APIs with available source code. It can create users, make requests and alter state. Do **not** wire it into a generic `AGENTS.md` instruction, default updater, periodic automation, or normal CI job.

Before any scan:

1. The user explicitly chooses an **owned/authorized**, isolated, disposable **development or staging** target, never production or an unidentified public endpoint.
2. Record scope, allowed hostnames, test accounts, data reset plan, rate limits and written authorization where relevant.
3. Run in a segregated Docker environment. Keep credentials out of Git and the terminal transcript. Secure reports and logs; do not auto-push exploit details.
4. Verify prerequisites (Node.js 18+, Docker, network access, supported model/provider, cyber safeguards) and expected cost/quota consumption.
5. Treat results as untrusted candidates pending independent review. Never bypass project risk/security gates or auto-merge security fixes.

Shannon documentation says the latest release can also use an **OpenAI Codex Plus/Pro subscription** via a separate *Pi* login, with a documented `openai-codex:gpt-6-sol` model. This is **not** automatic reuse of the active Codex app session, nor proof that GPT-6.1 is supported in Shannon. An API-key path can incur additional billed costs. Test only after explicit user approval of scope and credentials.

Shannon is most suitable for a running web app/API, not as a substitute for CryptoLab's financial-correctness gates or for static Rust review.

## 4. HatchZip — optional manual disk utility, not an agent skill

Site: https://hatchzip.dev/  
Source: https://github.com/xevrion/hatchzip

HatchZip extracts large ZIP/7z/RAR/tar archives while progressively reclaiming space from the **source archive**. It is useful for exceptionally large archives on disks with little free space, not for normal Codex routing.

- **Destructive by design:** the original archive is consumed/shortened as extraction progresses. Never automatically use it on the only copy of a release artifact, backup, evidence archive, or data that requires immutable retention.
- Prefer ordinary 7-Zip/tar extraction when enough space is available and retaining the original archive matters.
- Download only the appropriate official release, inspect checksums/signatures when published, and review source/release provenance; the project's site warns that Windows binaries are currently **not code-signed**.
- No background daemon, scheduler, MCP service or Codex auto-hook is installed by this stack.

## Orchestration decision table

| Request | Preferred flow |
| --- | --- |
| Routine coding, tests, evidence | Luna worker + CRG/RTK + deterministic checks |
| New feature with significant requirements/dependencies | Spec Kit **if selected** -> bounded specialist workers -> gated verification |
| Website/dashboard/UI design | UI worker with optional `$frontend-design` -> build + responsive/visual checks |
| Authorized staging web/API penetration test | Explicit Shannon security workflow, isolated and manual |
| Disk-starved extraction of a disposable archive | User-run HatchZip, after checking source/archive retention |

## Adoption policy

- Opt-in tools are never silently installed or granted elevated permissions by the global updater.
- Do not let third-party tools modify protected CryptoLab worktrees, run exploitation, delete archive evidence, or change CI without explicit scoped authorization.
- Run one representative pilot and measure task completion, deterministic pass rate, added context, maintenance overhead and subscription usage before widening adoption.
- Confirm observed worker activity in Codex's agents view. Documentation and `AGENTS.md` alone do not prove delegation.
