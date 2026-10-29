#!/usr/bin/env python3
"""P1.1 H1.2: real app-server thread/start POLICY-ECHO preflight only.

By default prints an OFFLINE plan. With explicit --execute-local-thread-probe
on non-admin Windows, launches exactly one pinned Codex 0.165.0 app-server
under a fresh CODEX_HOME and synthetic workspace; sends only initialize,
initialized, thread/start. NEVER turn/start, any tool or prompt. A reported
workspaceWrite policy is NOT proof of effective Windows MXC enforcement.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h1 = _load("Probe-CodexAB-AppServerH1.py", "p11_h1_transport")
policy = _load("Check-CodexAB-H12ThreadPolicy.py", "p11_h12_policy")
CONTRACT = "p1.1-appserver-h12-real-thread-echo-v1"
MAX_RECEIVED_MESSAGES = 32
INITIALIZE_TIMEOUT_S = 15
THREAD_TIMEOUT_S = 18
SAFE_CODES = frozenset({
    *h1.SAFE_FAILURE_CODES,
    "THREAD_RESPONSE_TIMEOUT", "THREAD_SERVER_EXITED",
    "THREAD_RPC_REJECTED", "THREAD_RPC_ID_MISMATCH",
    "THREAD_MESSAGE_INVALID", "THREAD_NOTIFICATION_UNEXPECTED",
    "THREAD_RESPONSE_TOO_LARGE", "THREAD_ECHO_VALIDATION_FAILED",
    "THREAD_RESPONSE_MISSING", "THREAD_MESSAGE_LIMIT_EXCEEDED",
    "EXTERNAL_SCRIPT_FAILURE", "REPO_DEPENDENCY_MISSING",
    "WORKSPACE_PROBE_PRECONDITION_FAILED",
    "THREAD_WARNING_WINDOWS_WORLD_WRITABLE",
    "THREAD_WARNING_CONFIG",
    "THREAD_WARNING_GENERAL",
    "THREAD_WARNING_GUARDIAN",
    "THREAD_ERROR_NOTIFICATION",
    "THREAD_WINDOWS_SANDBOX_SETUP_EVENT",
    "THREAD_PERMISSION_STATE_CHANGED",
    "THREAD_MODEL_VERIFICATION_EVENT",
    "THREAD_DEPRECATION_NOTICE",
    "THREAD_REMOTE_CONTROL_NOT_DISABLED",
    "THREAD_REMOTE_CONTROL_STATE_INVALID",
})


# Exact method strings from openai/codex rust-v0.165.0,
# app-server-protocol/src/protocol/common.rs (ServerNotification enum).
# Passive events contain data we do NOT inspect, persist, print or trust.
# Cap the count to prevent indefinite consumption of unsolicited messages.
PASSIVE_PRE_REPLY_NOTIFICATIONS = frozenset({
    "thread/started",
    "thread/status/changed",
    "skills/changed",
    "mcpServer/startupStatus/updated",
    "account/updated",
    "account/rateLimits/updated",
    "app/list/updated",
})

# These signals require an operator review; NEVER silently ignore them.
# Especially world-writable Windows temp/workspace paths cannot be treated as
# proof that the requested MXC policy provides isolation.
STOP_PRE_REPLY_NOTIFICATIONS = {
    "windows/worldWritableWarning": "THREAD_WARNING_WINDOWS_WORLD_WRITABLE",
    "windowsSandbox/setupCompleted": "THREAD_WINDOWS_SANDBOX_SETUP_EVENT",
    "configWarning": "THREAD_WARNING_CONFIG",
    "warning": "THREAD_WARNING_GENERAL",
    "guardianWarning": "THREAD_WARNING_GUARDIAN",
    "error": "THREAD_ERROR_NOTIFICATION",
    "deprecationNotice": "THREAD_DEPRECATION_NOTICE",
    "thread/settings/updated": "THREAD_PERMISSION_STATE_CHANGED",
    "model/verification": "THREAD_MODEL_VERIFICATION_EVENT",
}


class GateError(ValueError):
    """Only fixed, non-sensitive failure categories."""


def _safe_code(exc):
    if isinstance(exc, GateError):
        if len(exc.args) == 1 and exc.args[0] in SAFE_CODES:
            return exc.args[0]
        # Only the SHA-256 method-name digest is permitted outside the static
        # error allowlist. Never include event params, text, IDs, or paths.
        if (len(exc.args) == 2 and exc.args[0] == "THREAD_NOTIFICATION_UNEXPECTED"
                and isinstance(exc.args[1], str)
                and re.fullmatch(r"[0-9A-F]{12}", exc.args[1])):
            return "THREAD_NOTIFICATION_UNEXPECTED:METHOD_SHA256_" + exc.args[1]
    if isinstance(exc, h1.PreflightError):
        category = h1.safe_error_code(exc)
        return category if category in SAFE_CODES else "EXTERNAL_SCRIPT_FAILURE"
    return "EXTERNAL_SCRIPT_FAILURE"


def plan():
    return {
        "contract": CONTRACT,
        "mode": "PLAN_ONLY_NO_PROCESS",
        "target_cli": h1.VERSION,
        "requested_policy": {
            "model": policy.MODEL,
            "approval": "never",
            "sandbox": "workspace-write",
            "windows_sandbox": "mxc",
            "effort": "medium",
            "ephemeral": True,
        },
        "messages_planned": ["initialize", "initialized", "thread/start"],
        "real_messages_sent": 0,
        "model_calls_made": 0,
        "turn_start_sent": False,
        "worker_spawned": False,
        "runtime_policy_verified": False,
        "runtime_mxc_effectiveness_verified": False,
        "network_isolation_independently_verified": False,
        "requires_explicit_local_execution_flag": True,
        "candidate_merge_authorized": False,
    }


def _receive_thread_response(inbox, proc=None, timeout=THREAD_TIMEOUT_S):
    """Read one thread/start reply; ignore only bounded known notifications.

    Return only the matching response to the caller. No raw data are logged.
    """
    deadline = time.monotonic() + timeout
    count = 0
    while count < MAX_RECEIVED_MESSAGES:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GateError("THREAD_RESPONSE_TIMEOUT")
        try:
            typ, raw = inbox.get(timeout=min(0.25, remaining))
        except queue.Empty:
            if proc is not None and proc.poll() is not None:
                # Drain a queued final response before declaring child exit.
                try:
                    typ, raw = inbox.get(timeout=min(0.15, max(0.01, deadline - time.monotonic())))
                except queue.Empty:
                    raise GateError("THREAD_SERVER_EXITED") from None
            else:
                continue
        count += 1
        if typ == "too_large":
            raise GateError("THREAD_RESPONSE_TOO_LARGE")
        if typ != "line":
            raise GateError("THREAD_RESPONSE_MISSING")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise GateError("THREAD_MESSAGE_INVALID") from None
        if not isinstance(body, dict) or (
                "jsonrpc" in body and body["jsonrpc"] != "2.0"):
            raise GateError("THREAD_MESSAGE_INVALID")
        if "id" in body:
            if type(body["id"]) is not int or body["id"] != 2:
                raise GateError("THREAD_RPC_ID_MISMATCH")
            if "error" in body:
                raise GateError("THREAD_RPC_REJECTED")
            if not isinstance(body.get("result"), dict):
                raise GateError("THREAD_MESSAGE_INVALID")
            return body
        # A notification may arrive before the matching thread/start response.
        # Distinguish known, passive background updates from safety warnings.
        # Server requests (with id) and unknown events remain fail-closed.
        method = body.get("method")
        if not isinstance(method, str):
            raise GateError("THREAD_MESSAGE_INVALID")
        if method == "remoteControl/status/changed":
            # Official rust-v0.165.0 RemoteControlConnectionStatus enum:
            # disabled | connecting | connected | errored.
            # Read ONLY the state flag. Server name, installation ID and
            # environment ID are never copied, printed or persisted.
            params = body.get("params")
            if not isinstance(params, dict) or params.get("status") not in (
                    "disabled", "connecting", "connected", "errored"):
                raise GateError("THREAD_REMOTE_CONTROL_STATE_INVALID")
            if params["status"] != "disabled":
                raise GateError("THREAD_REMOTE_CONTROL_NOT_DISABLED")
            continue
        if method in STOP_PRE_REPLY_NOTIFICATIONS:
            raise GateError(STOP_PRE_REPLY_NOTIFICATIONS[method])
        if method not in PASSIVE_PRE_REPLY_NOTIFICATIONS:
            # The earlier generic code prevented forensic classification.
            # Hash ONLY the method name (not params or any message payload)
            # and FAIL CLOSED. The digest can be compared offline against
            # the exact pinned rust-v0.165.0 ServerNotification enum.
            fingerprint = hashlib.sha256(method.encode("utf-8")).hexdigest()[:12].upper()
            raise GateError("THREAD_NOTIFICATION_UNEXPECTED", fingerprint)
    raise GateError("THREAD_MESSAGE_LIMIT_EXCEEDED")


def perform_exchange(command, environment, root, home, workspace,
                     init_timeout=INITIALIZE_TIMEOUT_S, thread_timeout=THREAD_TIMEOUT_S):
    """One child and one thread/start. Caller may supply a FAKE executable for tests."""
    kw = {
        "cwd": root, "env": environment,
        "stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL, "bufsize": 0, "shell": False,
    }
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    try:
        proc = subprocess.Popen(list(command), **kw)
    except OSError:
        raise GateError("APP_SERVER_START_FAILED") from None
    inbox = queue.Queue(maxsize=MAX_RECEIVED_MESSAGES + 2)
    reader = threading.Thread(target=h1._reader, args=(proc.stdout, inbox), daemon=True)
    reader.start()
    try:
        h1._send(proc, {
            "id": 1, "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "p11-h12-thread-probe",
                    "title": "P1.1 thread policy audit",
                    "version": "0.1.0",
                },
                "capabilities": None,
            },
        })
        init = h1._wait_response(inbox, init_timeout, process=proc)
        if Path(init["codexHome"]).resolve(strict=False) != Path(home).resolve(strict=False):
            raise GateError("ISOLATED_HOME_MISMATCH")
        if init.get("platformOs") != ("windows" if os.name == "nt" else "linux"):
            raise GateError("PLATFORM_MISMATCH")
        h1._send(proc, {"method": "initialized"})
        request = policy.request_for_workspace(str(workspace))
        h1._send(proc, request)
        response = _receive_thread_response(inbox, proc=proc, timeout=thread_timeout)
        # Existing H1.2 validator is intentionally strict. Stop on mismatch
        # rather than broadening writable roots or permissions at runtime.
        try:
            summary = policy.validate(request, response, str(workspace), str(home))
        except (policy.PolicyError, TypeError, ValueError, KeyError):
            raise GateError("THREAD_ECHO_VALIDATION_FAILED") from None
        return {
            "status": "THREAD_START_DECLARED_POLICY_PASS_UNATTESTED",
            "contract": CONTRACT,
            "target_cli": h1.VERSION,
            "real_app_server_connected": True,
            "real_thread_created": True,
            "thread_start_sent": True,
            "turn_start_sent": False,
            "model_calls_made": 0,
            "worker_spawned": False,
            "approval_echo": summary["approval_echo"],
            "sandbox_echo": summary["sandbox_echo"],
            "network_access_echo": summary["network_access_echo"],
            "reasoning_effort_echo": summary["reasoning_effort_echo"],
            "ephemeral_echo": summary["ephemeral_echo"],
            "allowed_root_count": summary["allowed_root_count"],
            "instruction_source_count": summary["instruction_source_count"],
            "runtime_mxc_effectiveness_verified": False,
            "network_isolation_independently_verified": False,
            "worker_delegation_independently_verified": False,
            "complete_child_tree_cleanup_attested": False,
            "candidate_merge_authorized": False,
        }
    finally:
        if not h1._stop_child(proc):
            raise GateError("CHILD_CLEANUP_UNVERIFIED")


def run_local():
    if os.name != "nt":
        raise GateError("WINDOWS_ONLY_PREFLIGHT")
    if ctypes.windll.shell32.IsUserAnAdmin():
        raise GateError("ELEVATED_SESSION_FORBIDDEN")
    if not h1.CLI.is_file() or h1.CLI.is_symlink():
        raise GateError("PINNED_CLI_MISSING")
    try:
        cli_version = subprocess.run(
            [str(h1.CLI), "--version"], stdin=subprocess.DEVNULL,
            capture_output=True, check=False, timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise GateError("CLI_VERSION_PROBE_FAILED") from None
    if cli_version.returncode != 0 or cli_version.stdout.decode(
            "utf-8", "replace").strip() != h1.VERSION:
        raise GateError("PINNED_VERSION_MISMATCH")

    # A new HOME and workspace. Never inspect, modify or copy existing sessions.
    with tempfile.TemporaryDirectory(prefix="p11-h12-ephemeral-") as temporary:
        root = Path(temporary)
        home = root / "codex-home"
        workspace = root / "workspace"
        home.mkdir()
        workspace.mkdir()
        # No AGENTS.md and no project files in the synthetic workspace.
        env = h1.env_for_isolated_home(home)
        report = perform_exchange([str(h1.CLI), "app-server", "--stdio"],
                                  env, root, home, workspace)
    report["temporary_profile_and_workspace_deleted"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute-local-thread-probe", action="store_true",
        help="Explicitly start isolated app-server and one ephemeral thread; NO model turn",
    )
    args = parser.parse_args(argv)
    try:
        report = run_local() if args.execute_local_thread_probe else plan()
    except (GateError, h1.PreflightError, OSError, ValueError, TypeError) as exc:
        print("STOP: H12_REAL_THREAD_PROBE_FAILED:" + _safe_code(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
