#!/usr/bin/env python3
"""H1: explicitly gated Codex 0.165.0 stdio initialize-only preflight.

Default: no process, no network, no file changes. --execute-local-preflight
starts exactly one fresh-profile app-server for initialize/initialized only.
Never sends thread/start, turn/start, tool calls, prompts, or credentials.
The child may perform startup I/O; network/MXC policy is NOT attested here.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

CLI = Path(r"C:\Dev\codex-cli-0165\node_modules\.bin\codex.cmd")
VERSION = "codex-cli 0.165.0"
MAX_LINE = 131072
SAFE_ENV = frozenset({
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
    "APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
    "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432",
    "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "OS",
})


class PreflightError(Exception):
    """Fixed non-sensitive diagnostic codes."""


SAFE_FAILURE_CODES = frozenset({
    "WINDOWS_ONLY_PREFLIGHT", "ELEVATED_SESSION_FORBIDDEN",
    "PINNED_CLI_MISSING", "CLI_VERSION_PROBE_FAILED",
    "PINNED_VERSION_MISMATCH", "APP_SERVER_START_FAILED",
    "STDIN_WRITE_FAILED", "INITIALIZE_RESPONSE_TIMEOUT",
    "SERVER_EXITED_BEFORE_INITIALIZE", "INVALID_STDIO_RESPONSE",
    "INVALID_JSON_RESPONSE", "INVALID_JSONRPC_VERSION", "RPC_ID_MISMATCH",
    "INITIALIZE_RPC_REJECTED", "INITIALIZE_REPLY_SCHEMA_MISMATCH",
    "UNEXPECTED_STDIO_NOTIFICATION", "TOO_MANY_INITIALIZE_MESSAGES",
    "ISOLATED_HOME_MISMATCH", "PLATFORM_MISMATCH",
    "CHILD_CLEANUP_UNVERIFIED",
})


def safe_error_code(exc):
    """Export ONLY fixed internal categories; never expose paths or stderr."""
    if isinstance(exc, PreflightError) and len(exc.args) == 1:
        code = exc.args[0]
        if isinstance(code, str) and code in SAFE_FAILURE_CODES:
            return code
    return "OTHER_LOCAL_PREFLIGHT_FAILURE"


def plan():
    return {
        "contract": "p1.1-appserver-h1-stdio-initialize-only-v1",
        "mode": "PLAN_ONLY_NO_PROCESS",
        "target_cli": VERSION,
        "transport": "stdio://",
        "messages_to_send": ["initialize", "initialized"],
        "thread_start_sent": False,
        "turn_start_sent": False,
        "model_calls_made": 0,
        "temporary_codex_home_required": True,
        "network_activity_independently_verified": False,
        "sandbox_mxc_effectiveness_verified": False,
        "no_existing_profile_used": True,
        "requires_explicit_local_execution_flag": True,
    }


def env_for_isolated_home(home, source=None):
    source = source if source is not None else os.environ
    result = {key: value for key, value in source.items()
              if key.upper() in SAFE_ENV and isinstance(value, str)}
    result["CODEX_HOME"] = str(home)
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def _reader(pipe, output):
    try:
        while True:
            raw = pipe.readline(MAX_LINE + 1)
            if not raw:
                output.put(("eof", None))
                break
            if len(raw) > MAX_LINE:
                output.put(("too_large", None))
                break
            output.put(("line", raw))
    except OSError:
        output.put(("read_error", None))


def _send(proc, message):
    data = (json.dumps(message, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
    try:
        proc.stdin.write(data)
        proc.stdin.flush()
    except (BrokenPipeError, OSError, ValueError):
        raise PreflightError("STDIN_WRITE_FAILED") from None


def _wait_response(messages, timeout, process=None):
    """Bounded protocol reading; report safe early-exit and timeout codes."""
    deadline = time.monotonic() + timeout
    processed = 0
    while processed < 30:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PreflightError("INITIALIZE_RESPONSE_TIMEOUT")
        try:
            typ, raw = messages.get(timeout=min(remaining, 0.25))
        except queue.Empty:
            if process is not None and process.poll() is not None:
                # Give the reader a brief chance to enqueue a final response
                # before reporting that the child exited.
                try:
                    typ, raw = messages.get(timeout=min(0.15, max(0.01, deadline - time.monotonic())))
                except queue.Empty:
                    raise PreflightError("SERVER_EXITED_BEFORE_INITIALIZE") from None
            else:
                continue
        processed += 1
        if typ != "line":
            raise PreflightError("INVALID_STDIO_RESPONSE")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise PreflightError("INVALID_JSON_RESPONSE") from None
        if not isinstance(payload, dict):
            raise PreflightError("INVALID_JSON_RESPONSE")
        if payload.get("jsonrpc") != "2.0":
            raise PreflightError("INVALID_JSONRPC_VERSION")
        if "id" in payload and payload.get("id") != 1:
            raise PreflightError("RPC_ID_MISMATCH")
        if payload.get("id") == 1:
            if payload.get("error") is not None or not isinstance(payload.get("result"), dict):
                raise PreflightError("INITIALIZE_RPC_REJECTED")
            result = payload["result"]
            if (not isinstance(result.get("userAgent"), str)
                    or result.get("platformFamily") not in ("windows", "unix")
                    or not isinstance(result.get("codexHome"), str)):
                raise PreflightError("INITIALIZE_REPLY_SCHEMA_MISMATCH")
            return result
        if payload.get("method") not in ("error", "configWarning", "appServer/restartRequired"):
            raise PreflightError("UNEXPECTED_STDIO_NOTIFICATION")
    raise PreflightError("TOO_MANY_INITIALIZE_MESSAGES")

def _stop_child(proc):
    """Best-effort child-tree shutdown, without touching unrelated processes."""
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except OSError:
        pass
    if proc.poll() is None:
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                try:
                    subprocess.run(
                        ["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL, check=False, timeout=8
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass
            else:
                try:
                    import signal
                    os.killpg(proc.pid, signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    try:
        if proc.stdout:
            proc.stdout.close()
    except OSError:
        pass
    return proc.poll() is not None


def exchange(cmd, env, cwd, timeout=15):
    """One local stdio child, one initialize, one initialized; no turn creation."""
    kw = {"cwd": cwd, "env": env, "stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
          "stderr": subprocess.DEVNULL, "bufsize": 0, "shell": False}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    try:
        proc = subprocess.Popen(list(cmd), **kw)
    except OSError:
        raise PreflightError("APP_SERVER_START_FAILED") from None
    messages = queue.Queue(maxsize=32)
    thread = threading.Thread(target=_reader, args=(proc.stdout, messages), daemon=True)
    thread.start()
    finished = False
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"clientInfo": {
                         "name": "p11-stdio-preflight", "title": "P1.1 isolated H1",
                         "version": "0.1"}, "capabilities": None}})
        reply = _wait_response(messages, timeout, process=proc)
        if Path(reply["codexHome"]).resolve(strict=False) != Path(env["CODEX_HOME"]).resolve(strict=False):
            raise PreflightError("ISOLATED_HOME_MISMATCH")
        if (reply.get("platformOs") != ("windows" if os.name == "nt" else "linux")
                and not (os.name != "nt" and reply.get("platformOs") in ("linux", "macos"))):
            raise PreflightError("PLATFORM_MISMATCH")
        _send(proc, {"jsonrpc": "2.0", "method": "initialized"})
        return {"handshake": "PASS", "initialized_sent": True}
    finally:
        finished = _stop_child(proc)
        if not finished:
            raise PreflightError("CHILD_CLEANUP_UNVERIFIED")


def run_local_preflight():
    if os.name != "nt":
        raise PreflightError("WINDOWS_ONLY_PREFLIGHT")
    if ctypes.windll.shell32.IsUserAnAdmin():
        raise PreflightError("ELEVATED_SESSION_FORBIDDEN")
    if not CLI.is_file() or CLI.is_symlink():
        raise PreflightError("PINNED_CLI_MISSING")
    try:
        version = subprocess.run([str(CLI), "--version"], capture_output=True, timeout=12,
                                 check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        raise PreflightError("CLI_VERSION_PROBE_FAILED") from None
    if version.returncode != 0 or version.stdout.decode("utf-8", "replace").strip() != VERSION:
        raise PreflightError("PINNED_VERSION_MISMATCH")
    # Fresh temporary HOME; no user CODEX_HOME, no copied auth/TOML and no custom MCP.
    with tempfile.TemporaryDirectory(prefix="p11-h1-isolated-") as temp:
        home = Path(temp) / "codex-home"
        home.mkdir()
        env = env_for_isolated_home(home)
        result = exchange([str(CLI), "app-server", "--stdio"], env, temp)
    return {
        "status": "ISOLATED_STDIO_HANDSHAKE_PASS_UNATTESTED",
        "contract": "p1.1-appserver-h1-stdio-initialize-only-v1",
        "target_cli": VERSION,
        "messages_sent": ["initialize", "initialized"],
        "thread_start_sent": False,
        "turn_start_sent": False,
        "model_calls_made": 0,
        "isolated_home_temporary_removed": True,
        "handshake_successful": result["handshake"] == "PASS",
        "real_app_server_connected": True,
        "worker_delegation_independently_verified": False,
        "sandbox_mxc_effectiveness_verified": False,
        "network_isolation_verified": False,
        "child_tree_cleanup_independently_attested": False,
        "merge_pr14_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-local-preflight", action="store_true",
                        help="Explicitly start one isolated app-server, initialize only (NO model)")
    args = parser.parse_args(argv)
    try:
        result = run_local_preflight() if args.execute_local_preflight else plan()
    except (PreflightError, OSError, ValueError) as exc:
        # Never display exception text from OS, subprocess, JSON or the
        # app-server; only a fixed allowlisted local classification.
        print("STOP: H1_LOCAL_PREFLIGHT_FAILED:" + safe_error_code(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
