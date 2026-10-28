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

The program rejects an existing output directory. It records distinct SHA256 fingerprints and does not modify the working configuration. It first tries the exact pinned PR #14 Git object already in the local checkout; only when unavailable does it request the immutable raw GitHub URL. A known local file can be provided through --candidate-file.

On Windows, the launcher resolves the explicit `codex.exe` / `codex.cmd` / `codex.bat` path rather than calling a bare `codex` process. This also handles npm installations where Python finds an extensionless POSIX shim or `codex.ps1` even though PowerShell can run Codex. The same resolved launcher is used for `--version`, `login status` and `exec`; no reinstall or execution-policy change is required.

**If prepare fails, STOP there. Do not run login, status or run.** The script prints an intentionally restricted diagnostic code, for example:
- `OUTPUT_ALREADY_EXISTS`: choose a NEW folder, and inspect the previous folder without deleting anything;
- `BASELINE_UNAVAILABLE`: verify where the active global `AGENTS.md` is installed; pass `--baseline` if required;
- `CANDIDATE_FETCH_FAILED`: fetch the PR #14 candidate separately or ensure the pinned Git commit is present; `--candidate-file` accepts a local copy;
- `CODEX_UNAVAILABLE` or `CODEX_START_FAILED`: the `codex` command works in PowerShell but is not available as an executable to Python, or cannot launch;
- `PREPARE_WRITE_FAILED`: incomplete experiment folder may exist; do not overwrite; use a fresh output folder after diagnosis.

The runner never prints raw exception text, URLs with credentials, tokens or the contents of any configuration file. An exception outside those predictable prepare conditions still uses the generic safe STOP message and warrants investigation.

When rerunning after a failed first preparation, change the output path, for example from `C:\Dev\codex-ab-pr14-pilot` to `C:\Dev\codex-ab-pr14-pilot-v2`. Change it **consistently** for preparation, login, status and run. The preparation step itself consumes no model quota.

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

## Controlled single-call tool/delegation probe (only after offline diagnostics)

If the existing pilot failed with **zero tracked edits**, but authentication, feature flags, AGENTS visibility, model catalog and native Doctor all pass, the old raw CLI output is unavailable. Do not rerun the complete A/B benchmark. A **single opt-in model invocation** can test whether the parent-and-worker pair can read a disposable marker using tool calls, without changing files.

~~~powershell
cd C:\Dev\codex-context-efficiency-stack
python .\scripts\Test-Probe-CodexAB-Tools.py
if ($LASTEXITCODE -ne 0) { throw 'Offline probe tests failed' }

python .\scripts\Probe-CodexAB-Tools.py --pilot C:\Dev\codex-ab-pr14-pilot-v3 --output C:\Dev\codex-ab-tools-probe-v1 --timeout 90 --execute
if ($LASTEXITCODE -ne 0) { Write-Warning 'Probe reported runtime failure: inspect the sanitized JSON only' }
~~~

This creates a **new disposable Git checkout** inside the probe directory and places a random 32-digit hexadecimal marker in \`marker.txt\`, not included in the model prompt. It uses the original isolated **baseline** Codex profile and Luna Medium, with \`--sandbox read-only --ephemeral\`. The parent is instructed to dispatch one \`luna-medium\` read-only worker to retrieve the marker. The script stops after **one invocation** (up to 90 seconds), never retries, never escalates permissions, never runs the candidate or reads unrelated files. Unlike the earlier A/B task, the fixture requires **no writes** during the model turn. This consumes model quota.

Only allowlisted booleans, counters, exit code, timing and coarse error categories are displayed/saved in \`sanitized-probe-result.json\`. The synthetic marker is retained only in the disposable Git fixture as the test input; its **value is never printed or copied into the sanitized report**. Model replies, commands, stderr and raw Codex JSONL are never printed or persisted. A matching marker demonstrates the model got its contents somehow; **it does not independently prove that a worker, rather than the parent, did the read**, because V2 collaboration events may be missing from JSONL. An absent marker cannot by itself distinguish a tool-absence defect from model noncompliance; consult the sanitized classification and exit code.

**Follow-up on 2026-10-28 probe:** the first read-only probe ended `BLOCKED_OR_UNVERIFIED` with one generic completed collab event, no marker, CLI exit 0 and stderr present. This is **not** proof that no worker was spawned: upstream openai/codex issues [#41590](https://github.com/openai/codex/issues/41590) and [#34919](https://github.com/openai/codex/issues/34919) document missing V2 `spawn_agent` events in `codex exec --json`. Local incident record: [project issue #34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34). **Do not repeat the same probe**. Future probes (only when separately justified and authorized) will additionally distinguish allowlisted `spawn_agent`, `wait`, `send_input`, `close_agent` events by status and classify stderr by fixed category without retaining message contents. This is prospective telemetry only and cannot reconstruct events discarded by the first two `--ephemeral` invocations.

When running in an interactive PowerShell prompt, keep every \`if (...) { ... } else { ... }\` block in the **same invocation**, or omit \`else\`. The earlier detached \`else\` errors were shell parsing, not Codex errors.

Do not modify or delete the failed \`pilot-v3\` evidence. If the single-call probe fails or remains ambiguous, prefer a tracked upstream bug with the sanitized signature over repeated trial-and-error model calls.

## No-quota probe for resolved Luna model and actual instruction discovery

After confirming that both isolated homes report multi_agent=true but the original baseline still edited zero files, check two additional **read-only CLI debug surfaces** before spending any further model tokens:

~~~powershell
cd C:\Dev\codex-context-efficiency-stack
python .\scripts\Test-Check-CodexAB-ModelPrompt.py
python .\scripts\Check-CodexAB-ModelPrompt.py --output C:\Dev\codex-ab-pr14-pilot-v3
~~~

This script uses the exact isolated homes and the preserved disposable baseline working tree as cwd for both arms. It executes only Codex CLI debug commands:
- \`codex debug models --bundled\`: obtains the local **bundled** model metadata. It prints only gpt-6-luna's model identifier, multi_agent_version, tool_mode, shell_type and presence. A bundled catalog is **not** proof of the actual live model/tool configuration.
- \`codex --model gpt-6-luna -c model_reasoning_effort=medium debug prompt-input\`: constructs the diagnostic model-visible input for the disposable test worktree. It prints **only** whether a distinctive substring of the expected AGENTS.md appears in the reconstructed input. It never prints the prompt text, full catalog, model internal instructions, auth details, private paths or session content.

The raw output is held in subprocess memory only and discarded after parsing; nothing is persisted by the script. No generative turn is invoked. Marker presence helps establish that the AGENTS instruction path is configured, but does not prove the model saw collaboration tools or could execute a shell. Marker absence may be a CLI diagnostic-surface limitation and requires investigation, not assumption that the policy is disabled.

Do not use \`codex debug app-server send-message-v2\` for this no-quota check: unlike the above debug commands, that tool sends an actual turn. Do not upload raw debug models/prompt-input output: these commands can expose internal model instruction templates and local context.

## No-quota multi-agent feature preflight after a baseline with zero tracked edits

If the historical pilot ran exactly once and changed no tracked files, do not run candidate or rerun baseline yet. First inspect whether the **isolated** Codex homes have the expected model collaboration feature flags:

~~~powershell
cd C:\Dev\codex-context-efficiency-stack
python .\scripts\Test-Check-CodexAB-Features.py
python .\scripts\Check-CodexAB-Features.py --output C:\Dev\codex-ab-pr14-pilot-v3
~~~

This reads only the two experiment \`config.toml\` files, hashes their \`AGENTS.md\` files and calls \`codex features list\` with each isolated \`CODEX_HOME\`. It is **read-only and makes zero model calls**. Its printed JSON is limited to allowlisted agent/feature settings and booleans; no tokens, auth.json, sessions, raw CLI output or code are read. A disabled \`multi_agent\` flag is a **candidate explanation**, not proof that the model was unable to spawn; model catalog metadata and MultiAgent V2 can affect the effective tool surface. Do not toggle V2 just to make a test pass: there are known compatibility/observability issues.

The isolated test homes were deliberately rebuilt from only the routing snippet, not from the user's entire effective configuration. Therefore a missing feature flag in the isolated config is a meaningful difference from an interactive smoke test using the normal profile. Inspect results before modifying any config; if changes are necessary, create a **fresh paired experiment** with the same settings for both arms rather than mutating the already preserved pilot.

## Existing failed trial: inspect it without Codex quota

If a pilot prints \`tests=FAIL\`, this combines several independent checks: Python unittest, Git diff whitespace, unexpected modified files, untracked files and an old literal-text assertion. It **does not** alone prove that Python tests failed.

Do **not** immediately run another live trial or manually edit \`anonymized-results.json\`. On the same machine, after updating this repository, run:

~~~powershell
python .\scripts\Test-Run-CodexAB.py
python .\scripts\Run-CodexAB.py inspect --output C:\Dev\codex-ab-pr14-pilot-v3
~~~

The \`inspect\` command only rechecks the disposable local test repository and reads the already-anonymized result. It launches **no Codex process**, does **not** call login, and does **not** consume model quota. It prints a fixed JSON object with the input/cached/uncached/output token counters plus separate **booleans** for test success, source-only change, Git whitespace check and untracked-file check. It does not print source files, test output, model messages, raw events or credentials.

The inspection now also reports `tracked_modified_file_count`, `total_py_changed` and `unexpected_tracked_modifications`. This distinguishes **zero edits** from **edits to the wrong tracked file**, without printing filenames or source content. These values are calculated from the existing disposable Git checkout and never alter the stored original result.

For subsequent **separately authorized** trials, a new `trial-diagnostics.json` sidecar records only the CLI exit code, timeout status, presence of stderr, and counts of allowlisted JSONL event types (command start/completion, file change, collaborative tool and error). It never saves stderr contents, commands, prompts, model messages, paths, credentials or raw JSONL. The earlier failed pilot cannot retroactively recover this data: its sidecar does not exist.

Official current Codex documentation confirms `--sandbox workspace-write` allows editing in non-interactive mode; the deprecated `--full-auto` flag is not used. Do not broaden the sandbox based solely on an unknown failure. See https://learn.chatgpt.com/docs/non-interactive-mode and https://learn.chatgpt.com/docs/agent-approvals-security.

The previous acceptance gate also required the exact substring \`prix * quantite\`, so a mathematically equivalent fix such as \`quantite * prix\` could have been misclassified as FAIL. The updated runner uses functional tests plus bounded Git changes instead; \`inspect\` shows both the old literal gate and the corrected functional gate so an earlier result can be interpreted **without rewriting its original evidence**. A complete re-run still requires a new experiment directory and another explicit \`--execute\`.

If the original command returned early, the saved run does **not** contain the Codex subprocess exit code or raw stderr. \`inspect\` cannot reconstruct those values. The reason for an **actual** model failure may therefore remain unproven without another separately authorized diagnostic; do not infer it from absent events.

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
