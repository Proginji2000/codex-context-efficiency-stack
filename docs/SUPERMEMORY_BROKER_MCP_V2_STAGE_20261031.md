# Supermemory ↔ Codex — broker + MCP offline stage V2 (31/10/2026)

**Status:** prototype tested OFFLINE only; no deployment, no Windows identity changes, no production key, no Codex model call. [Safety gate](SUPERMEMORY_CODEX_SECURITY_GATE_2026-10-31.md), [canonical handoff](CODEX_STACK_HANDOFF_2026-10-31.md).

## Deliverable

Conversation artifact `Supermemory_Readonly_Broker_MCP_Offline_V2_20261031.zip`, **SHA256 `A0A40F07D0C4272647D54E3839A5163067BE48ACF5F9D509C07B8165FDD811B5`**. This ZIP is a downloadable artifact in the original ChatGPT conversation, **not yet a file committed to this GitHub repository**. Its five files:

- `README.md`: topology and explicit security limitations.
- `broker.py`: local read-only HTTP broker, `POST /search` only, pinned namespace, client token, upstream `127.0.0.1:6767`, no redirects, request/response limits, simple rate limiter.
- `mcp_readonly_bridge.py`: JSON-RPC stdio MCP exposing only `search(query)`, reading **limited broker token**, never the Supermemory production API key.
- `tests/test_broker_mcp.py`: mocked HTTP tests and MCP stdio child-process test.
- `Invoke-BrokerOfflineQualification.ps1`: portable PowerShell 5.1 test invocation.

**Local preparation verification in assistant container (Linux):** `python -B -m unittest discover -s tests -q` → **24 tests PASS**, no actual Docker, Ollama, Supermemory or Codex calls. The ZIP SHA256 above is verified from the generated artifact. **Windows run is NOT YET verified.**

## User's next command, after downloading ZIP into Downloads

Use PowerShell 5.1: verify ZIP SHA256, extract it to a unique temporary folder, run `Invoke-BrokerOfflineQualification.ps1`, inspect `BROKER_MCP_OFFLINE_TESTS_PASS`, clean temporary extraction, no production changes. Never unzip into the local adapter branch and never run `broker.py` with production credentials yet.

## Important limitations

**The broker code is not a security boundary on its own.** Its built-in thread server is still prototype-grade: no bounded worker concurrency, service hardening, machine-level ACL enforcement, operational rotation, robust client identity controls, or full audit/rollback. It binds localhost, but this does not segregate Windows users or prevent another local process from reaching the service. The real API key must be retained in a trusted service identity. Codex must run under a restricted **different identity or VM** unable to access Docker, the production secret, protected files or service controls. Its accessible broker token must be limited to read-only search on the project namespace.

The previously observed `V3_DOCKER_FAILURE_CLASS=ACCESS_DENIED` demonstrated Docker daemon refusal **in one MXC sandboxed child command only**; it cannot prove the parent Codex or MCP runtime is similarly restricted. **Do not give the real Supermemory API key to a Codex process or its MCP subprocess.**

## After offline Windows PASS

1. Decide a trusted broker identity and a genuinely restricted Codex identity/VM, then document ACLs, service command/ownership, network boundaries and emergency shutdown.
2. Exercise positive search / negative write, namespace and direct secret/Docker access from the actual restricted identity.
3. Connect `mcp_readonly_bridge.py` using only the limited token under a single disposable Codex invocation, with a capped canary and no model escalation; preserve the existing global MCP and hooks untouched.
4. Once accepted, review and integrate code via separate PR; the existing local branch `codex/supermemory-local-adapter-20261030` HEAD `e4fd34e` remains unmodified. Avoid destroying or overwriting it with a forced pull.
