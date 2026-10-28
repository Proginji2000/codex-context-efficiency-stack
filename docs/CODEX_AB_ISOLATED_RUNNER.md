# P1.1 — Isolated Windows Codex AGENTS A/B runner

**Status: prepared; real Codex executions have not occurred.** This runner does not change the live Codex home, existing projects, global permissions, or PR #14.

## Isolation model

The script [Run-CodexAB.py](../scripts/Run-CodexAB.py) creates an explicitly named *new* output directory with two CODEX_HOME directories:

- baseline-home: reads the local, currently installed global AGENTS.md.
- candidate-home: downloads only the candidate AGENTS.md from the immutable PR #14 commit 80bb5d9eaa09d141075176ea363e93765e9f41cc, unless --candidate-file is specified.
- Both use exactly the same versioned worker role templates and a minimal routing-only configuration built from templates/config.routing.snippet.toml.
- All trial workspaces are new, disposable Git repositories with the same deterministic HEAD. No active project is mounted or written.

**Important limitation:** This is a *routing-only/no-MCP* experiment, not a faithful replica of the full user MCP configuration. The full stack requires a later, separately controlled benchmark. This experiment isolates AGENTS.md without reusing user MCP secrets.

Never copy authentication files, tokens, existing Codex session directories, or caches between homes. Each isolated home requires its own user-driven login. Authentication may store secrets inside these two homes; never upload, share, or commit those folders.

The runner also strips inherited CODEX_SQLITE_HOME, OPENAI_API_KEY, CODEX_API_KEY, CODEX_ACCESS_TOKEN and OPENAI_BASE_URL **only in its Codex child processes**. This prevents a shared SQLite state path or a host API-key configuration from silently changing the authentication/billing basis of the A/B run. The calling PowerShell environment remains unchanged. Verify that the interactive logins in both homes use the intended ChatGPT subscription, not API-key billing.

## Step 1 — prepare (no model quota)

In PowerShell, after the new code is present on main:

~~~powershell
cd C:\Dev\codex-context-efficiency-stack
git pull --ff-only
python .\scripts\Test-Run-CodexAB.py
python .\scripts\Run-CodexAB.py prepare --output C:\Dev\codex-ab-pr14-pilot
~~~

The program rejects an existing output directory. It records distinct SHA256 fingerprints and does not modify the working configuration. Fetching the pinned candidate AGENTS text requires access to raw.githubusercontent.com. If the candidate file is already present on disk, specify --candidate-file instead.

## Step 2 — authenticate each isolated home

~~~powershell
$oldCodexHome = $env:CODEX_HOME
try {
    $env:CODEX_HOME = 'C:\Dev\codex-ab-pr14-pilot\baseline-home'
    codex login
    $env:CODEX_HOME = 'C:\Dev\codex-ab-pr14-pilot\candidate-home'
    codex login
}
finally {
    $env:CODEX_HOME = $oldCodexHome
}
python .\scripts\Run-CodexAB.py status --output C:\Dev\codex-ab-pr14-pilot
~~~

These logins require the user's explicit interactive authentication. A successful login status does not establish that the specified model is accessible; a live run must confirm that independently.

## Step 3 — first pair (uses real quota)

~~~powershell
python .\scripts\Run-CodexAB.py run --output C:\Dev\codex-ab-pr14-pilot --pairs 1 --execute
~~~

This performs two Codex CLI invocations, baseline then candidate. Each is instructed to delegate a small correction to luna-medium while Luna Medium remains the parent orchestrator. The runner separately verifies the Python tests, the only authorized tracked-file change, Git diff whitespace, elapsed time and available CLI token counters.

Raw JSONL events are processed in memory and never saved by the runner. Only aggregate usage and fixed booleans are written to anonymized-results.json. The process stops on the first runtime or verification failure; it does not escalate models, bypass permissions or retry indefinitely.

### Evidence limits

Some Codex versions fail to emit reliable spawn_agent events in exec JSONL despite actual delegation. Absence of the event is **not proof of non-delegation**. Conversely, presence of an event does not independently demonstrate that the parent never implemented or tested code. Consequently parent_orchestrated remains false (= **unverified**) in the output. Independent real worker evidence is required before anyone revises that assertion. Do not treat model prose alone as this evidence.

The retries counter covers only additional turns visible through the CLI stream, not every internal retry. A timeout kills the invoked CLI process but does not establish that every descendant has exited: inspect relevant processes before attempting fresh runs or cleaning up.

## Step 4 — three paired trials (six real Codex invocations)

After a successful first-pair pilot, create a **different new** output directory (example: C:\Dev\codex-ab-pr14-full), repeat preparation and separate authentication there, then:

~~~powershell
python .\scripts\Run-CodexAB.py run --output C:\Dev\codex-ab-pr14-full --pairs 3 --execute
python .\scripts\Compare-CodexAB.py --input C:\Dev\codex-ab-pr14-full\anonymized-results.json
~~~

The comparator may return an inconclusive result or a behavioral regression while the parent role remains unverified; do not force or fabricate a pass. Even a successful six-run comparison would measure CLI token counters, not ChatGPT subscription quota. PR #14 remains unmerged until behavior, permissions and a representative full-MCP scenario are independently reviewed.

See [general benchmark protocol](CODEX_AB_BENCHMARK.md) and [qualification roadmap](QUALIFICATION_ROADMAP_2026.md).

References:
- https://learn.chatgpt.com/docs/config-file/config-advanced
- https://developers.openai.com/codex/non-interactive
- https://github.com/openai/codex/issues/34919
