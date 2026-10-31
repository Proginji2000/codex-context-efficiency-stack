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

## Windows PowerShell 5.1 qualification — PASS, 31 October 2026

The operator executed the exact checksum-pinned, single-run offline ZIP test from `Downloads`. The PowerShell transcript provides:
```text
BROKER_MCP_V2_INTEGRITY_PASS
NO_CODEX_NO_DOCKER_NO_OLLAMA_NO_PRODUCTION_API
Ran 24 tests in 6.751s
OK
BROKER_MCP_OFFLINE_TESTS_PASS
NO_SECRETS_NO_PRODUCTION_CHANGES
BROKER_MCP_V2_WINDOWS_PASS
```

**Decision:** offline prototype V2 code/protocol is now qualified on Windows as well as the preparation environment, with no live server, no real key, no Codex model call and no production data touched. The test wrapper removed its uniquely created temporary extraction directory. **This is NOT a live search, not a secure deployment, and not evidence that the operator and Codex identities are isolated.** Avoid rerunning 24 tests absent code changes.

**Next gate:** read-only Windows identity / ACL and port availability inventory, without creating accounts or changing Docker permissions. After deciding the restricted runner account and broker trust account/VM, add concrete service hardening, ACL tests, rollback, and a real negative test from the restricted identity. The agent's inherited environment and Docker access are explicitly in scope. Only then stage a live broker and a capped real Codex→MCP→broker→Supermemory query, with a limited client token exposed to MCP but **never** the production API key.

## Windows identity preflight — operator transcript, 31 October 2026

The operator executed an unchanged read-only PowerShell 5.1 inventory:

```text
CURRENT_TOKEN_ADMIN=False
PARENT_SUPERMEMORY_KEY_PRESENT=False
DOCKER_USERS_GROUP_PRESENT=True
STANDARD_ACCOUNT_CANDIDATES=2
ACCOUNT_INVENTORY_COMPLETE
BROKER_PORT_6811=NO_LISTENER
NO_ACCOUNTS_CREATED
NO_PERMISSIONS_CHANGED
NO_SECRETS_READ
WINDOWS_IDENTITY_PREFLIGHT_COMPLETE
```

**Scope and limits:** `CURRENT_TOKEN_ADMIN=False` means the current process is not running with an enabled Administrator role; it does **not** establish that the underlying Windows user is not an administrator or cannot access Docker. This operator has already proven access to Docker outside MXC. The inventory counted exactly two **enabled local users not directly listed** in local Administrators/docker-users; **these two are not yet approved runner candidates**. They could include the current Docker-capable operator account, built-in/system identities, service accounts or users with indirect/transitive privileges. `NO_LISTENER` is a point-in-time observation, not a reserved port.

**Next gate, no mutation:** a single local-identity classification with no account names/SIDs in output. Recreate the filtering; count current-user overlaps, built-in/system SIDs (RID < 1000), password policy, and inspect whether any *other* candidate remains for an isolated runner. Print ordinal candidate flags only, never passwords, account names or profile paths. If none can be deemed plausible, design a **new dedicated standard account** rather than repurpose WDAGUtilityAccount/Guest/DefaultAccount/service principals. No account should be created until deliberate design and authorization. No inference about effective denial of Docker or access to the production key may be made without testing the actual selected identity's token and ACLs. Avoid repeating MXC, broker offline, and Supermemory baseline tests.

## Windows local account classification — operator verified (31 October 2026)

Operator PowerShell output: `INITIAL_CANDIDATES=2`, `CURRENT_USER_OVERLAPS=0`, `BUILTIN_RID_ACCOUNTS=0`, `OTHER_LOCAL_ACCOUNTS=2`, `OTHER_PASSWORD_REQUIRED=2`, `INDIRECT_PERMISSIONS_NOT_VERIFIED`, `ACCOUNT_CLASSIFICATION_PASS`, `NO_ACCOUNTS_OR_PERMISSIONS_CHANGED`, `WINDOWS_ACCOUNT_CLASSIFICATION_COMPLETE`.

These two *enabled local accounts* are not the current account, have a RID at least 1000, require a password, and were not **directly listed** in local Administrators or docker-users. They are **candidates for further review, not approved restricted identities**. They may be in use by services, scheduled tasks or a distinct application, may have indirect groups/privileges, access to sensitive files, existing sessions or Docker credentials. The filter does not assess these factors.

**Next targeted read-only check:** count, per pseudonymous candidate ordinal, Win32_Service StartName and scheduled-task Principal.UserId references plus direct local group memberships, without printing account names, SIDs, task names or service names. If either enumeration fails or counts are ambiguous, report `INCONCLUSIVE` rather than zero. Do not alter or repurpose an existing account based only on this classification. Prefer a dedicated newly authorized standard runner if existing candidates belong to other applications. No secret may be inherited by Codex/MCP; the real Supermemory key remains only in a separate trusted broker identity. Actual negative tests under that identity still required.

## Windows account-usage audit — operator transcript, 31 October 2026

The operator repeated the same **two local candidate accounts** (not the operator, RID >= 1000, password required, not direct members of local Administrators or docker-users) and executed a read-only scan of accessible `Win32_Service.StartName` and `Get-ScheduledTask` principals:

```text
ACCOUNT_1_SERVICE_REFERENCES=0
ACCOUNT_1_TASK_REFERENCES=0
ACCOUNT_2_SERVICE_REFERENCES=0
ACCOUNT_2_TASK_REFERENCES=0
VISIBLE_SERVICE_TASK_AUDIT_PASS
NO_ACCOUNT_NAMES_OR_SIDS_PRINTED
NO_SYSTEM_CHANGES
ACCOUNT_USAGE_AUDIT_COMPLETE
```

**Interpretation:** the two accounts had no exact-alias matches in the service or scheduled-task principals **visible to that enumeration**. This does **not** establish that either account is unused or safe to repurpose: account aliases, indirect service launch, scheduled task visibility, user profile contents and application ownership, indirect group privileges and effective Docker/secret access remain outside this test. Do **not** silently adopt or modify them.

**Architecture decision / proposed default:** stop repeating account census. Prefer creating a **dedicated restricted local `codex-runner` identity**, under a deliberately approved administrative provisioning step, unless the operator explicitly confirms that an existing candidate is theirs and can be dedicated exclusively to this project. Codex runner has no local Administrators or docker-users membership, no host Docker access, no production API key, no access to trusted broker's credential store. The broker must have a distinct identity, fixed namespace/route and least-privilege client token. Do not copy the operator's `.codex` auth/profile, SSH keys, vault or cached cloud credentials into that account. The proposed Windows account creation, ACL setting, broker service and MCP connection are **not yet executed**; establish a rollback plan and request explicit operator approval before mutating OS accounts or trusted secret stores.

**Next actionable milestone:** design a reversible one-time Windows provisioning plan for the dedicated runner (preflight for name collision, admin requirement, secure password prompt, `Users` membership, deny Docker/secret access, independent Codex auth, narrowly-scoped disposable workspace). Qualify the runner token with actual negative Docker/credential/host-shares probes before exposing a synthetic broker token. Perform live Supermemory API access only afterward.

## Important limitations

**The broker code is not a security boundary on its own.** Its built-in thread server is still prototype-grade: no bounded worker concurrency, service hardening, machine-level ACL enforcement, operational rotation, robust client identity controls, or full audit/rollback. It binds localhost, but this does not segregate Windows users or prevent another local process from reaching the service. The real API key must be retained in a trusted service identity. Codex must run under a restricted **different identity or VM** unable to access Docker, the production secret, protected files or service controls. Its accessible broker token must be limited to read-only search on the project namespace.

The previously observed `V3_DOCKER_FAILURE_CLASS=ACCESS_DENIED` demonstrated Docker daemon refusal **in one MXC sandboxed child command only**; it cannot prove the parent Codex or MCP runtime is similarly restricted. **Do not give the real Supermemory API key to a Codex process or its MCP subprocess.**

## After offline Windows PASS

1. Decide a trusted broker identity and a genuinely restricted Codex identity/VM, then document ACLs, service command/ownership, network boundaries and emergency shutdown.
2. Exercise positive search / negative write, namespace and direct secret/Docker access from the actual restricted identity.
3. Connect `mcp_readonly_bridge.py` using only the limited token under a single disposable Codex invocation, with a capped canary and no model escalation; preserve the existing global MCP and hooks untouched.
4. Once accepted, review and integrate code via separate PR; the existing local branch `codex/supermemory-local-adapter-20261030` HEAD `e4fd34e` remains unmodified. Avoid destroying or overwriting it with a forced pull.
