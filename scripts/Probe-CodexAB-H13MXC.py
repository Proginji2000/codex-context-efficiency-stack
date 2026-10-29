#!/usr/bin/env python3
"""Explicit no-model standalone Windows MXC filesystem negative test.

Default: print plan, spawn nothing. With --execute-local-mxc-probe, uses a
fresh CODEX_HOME and disposable files. NOT an app-server turn attestation.
"""
import argparse
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("p11_h13_h1", HERE / "Probe-CodexAB-AppServerH1.py")
h1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h1)
CONTRACT = "p1.1-h13a-standalone-windows-mxc-fs-negative-v1"
MARKER = "P11_H13_CHILD_RESULT:"
MAX_CAPTURE = 8192
CHILD_CODE = r'''import errno, json, os, sys
from pathlib import Path
w = Path(os.environ["P11_H13_WORKSPACE"])
outside = Path(os.environ["P11_H13_OUTSIDE"])
inside_ok = False
outside_denied = False
try:
    with (w / "workspace-positive.canary").open("xb") as f:
        f.write(b"P11-H13-INSIDE-OK")
    inside_ok = True
except OSError:
    pass
try:
    with (outside / "outside-negative.canary").open("xb") as f:
        f.write(b"P11-H13-OUTSIDE-WRITE")
except PermissionError:
    outside_denied = True
except OSError as e:
    outside_denied = e.errno == errno.EACCES or getattr(e, "winerror", None) == 5
print("P11_H13_CHILD_RESULT:" + json.dumps(
    {"inside_ok": inside_ok, "outside_denied": outside_denied},
    separators=(",", ":"), sort_keys=True))
sys.exit(0 if inside_ok and outside_denied else 3)
'''

class ProbeError(Exception):
    pass

CODES = frozenset({
    "WINDOWS_ONLY", "NON_ADMIN_REQUIRED", "PINNED_CLI_MISSING",
    "PINNED_VERSION_FAILED", "PINNED_VERSION_MISMATCH",
    "TEMP_PRECONDITION_FAILED", "HOST_OUTSIDE_CONTROL_FAILED",
    "SANDBOX_START_FAILED", "SANDBOX_TIMEOUT", "SANDBOX_STDOUT_INVALID",
    "SANDBOX_STDERR_PRESENT", "SANDBOX_INSIDE_WRITE_FAILED",
    "SANDBOX_OUTSIDE_WRITE_NOT_DENIED", "SANDBOX_OUTSIDE_FILE_CHANGED",
    "SANDBOX_CHILD_FAILED", "PROCESS_CLEANUP_UNVERIFIED",
    "TEMPORARY_CLEANUP_FAILED",
})

def safe_reason(exc):
    if isinstance(exc, ProbeError) and len(exc.args) == 1 and exc.args[0] in CODES:
        return exc.args[0]
    return "OTHER_LOCAL_FAILURE"

def plan():
    return {
        "contract": CONTRACT, "mode": "PLAN_ONLY_NO_PROCESS",
        "cli_version": h1.VERSION, "backend_requested": "windows.sandbox=mxc",
        "permissions_requested": "workspace-write",
        "requires_explicit_nonadmin_flag": True,
        "standalone_mxc_runtime_verified": False,
        "appserver_turn_mxc_verified": False,
        "network_isolation_verified": False,
        "worker_provenance_verified": False,
        "child_tree_cleanup_attested": False,
        "model_calls_made": 0, "thread_start_sent": False,
        "turn_start_sent": False, "candidate_merge_authorized": False,
    }

def command_for(cli, python, child):
    return [str(cli), "-c", 'windows.sandbox="mxc"',
            "-c", 'sandbox_mode="workspace-write"',
            "sandbox", str(python), "-B", str(child)]

def evaluate(out, err, rc, inside_ok, outside_unchanged):
    if not isinstance(out, bytes) or len(out) > MAX_CAPTURE:
        raise ProbeError("SANDBOX_STDOUT_INVALID")
    if not isinstance(err, bytes) or len(err) > MAX_CAPTURE or err:
        raise ProbeError("SANDBOX_STDERR_PRESENT")
    try:
        lines = out.decode("utf-8").strip().splitlines()
        if len(lines) != 1 or not lines[0].startswith(MARKER):
            raise ValueError()
        result = json.loads(lines[0][len(MARKER):])
    except (ValueError, UnicodeError):
        raise ProbeError("SANDBOX_STDOUT_INVALID") from None
    if not isinstance(result, dict) or set(result) != {"inside_ok", "outside_denied"}:
        raise ProbeError("SANDBOX_STDOUT_INVALID")
    if result["inside_ok"] is not True or inside_ok is not True:
        raise ProbeError("SANDBOX_INSIDE_WRITE_FAILED")
    if result["outside_denied"] is not True:
        raise ProbeError("SANDBOX_OUTSIDE_WRITE_NOT_DENIED")
    if outside_unchanged is not True:
        raise ProbeError("SANDBOX_OUTSIDE_FILE_CHANGED")
    if rc != 0:
        raise ProbeError("SANDBOX_CHILD_FAILED")
    return {
        "contract": CONTRACT,
        "status": "STANDALONE_MXC_FILESYSTEM_NEGATIVE_PASS_NOT_APPSERVER",
        "backend_requested": "windows.sandbox=mxc",
        "host_outside_control_writable": True,
        "inside_workspace_write_observed": True,
        "outside_write_denied_observed": True,
        "outside_file_unchanged": True,
        "real_standalone_sandbox_invoked": True,
        "appserver_turn_mxc_verified": False, "network_isolation_verified": False,
        "worker_provenance_verified": False, "child_tree_cleanup_attested": False,
        "model_calls_made": 0, "thread_start_sent": False,
        "turn_start_sent": False, "candidate_merge_authorized": False,
    }

def stop_child(proc):
    if proc.poll() is None:
        if os.name == "nt":
            try:
                subprocess.run(["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=7, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
    try:
        proc.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        raise ProbeError("PROCESS_CLEANUP_UNVERIFIED") from None

def run_subprocess(cmd, env, cwd, timeout=25):
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, shell=False,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0))
    except OSError:
        raise ProbeError("SANDBOX_START_FAILED") from None
    try:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise ProbeError("SANDBOX_TIMEOUT") from None
        return out, err, proc.returncode
    finally:
        stop_child(proc)

def run_local():
    if os.name != "nt":
        raise ProbeError("WINDOWS_ONLY")
    if ctypes.windll.shell32.IsUserAnAdmin():
        raise ProbeError("NON_ADMIN_REQUIRED")
    if not h1.CLI.is_file() or h1.CLI.is_symlink():
        raise ProbeError("PINNED_CLI_MISSING")
    try:
        v = subprocess.run([str(h1.CLI), "--version"], check=False,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        raise ProbeError("PINNED_VERSION_FAILED") from None
    if v.returncode != 0 or v.stdout.decode("utf-8", "replace").strip() != h1.VERSION:
        raise ProbeError("PINNED_VERSION_MISMATCH")
    try:
        with tempfile.TemporaryDirectory(prefix="p11-h13-work-") as rt:
            # Outside is a NEW single-purpose directory in the user profile,
            # not %TEMP%; temp root might be implicitly writable by sandbox.
            with tempfile.TemporaryDirectory(prefix="p11-h13-outside-", dir=Path.home()) as ot:
                root, outside = Path(rt), Path(ot)
                workspace, home = root / "workspace", root / "codex-home"
                workspace.mkdir()
                home.mkdir()
                target = outside / "outside-negative.canary"
                inside = workspace / "workspace-positive.canary"
                control = outside / "host-control.canary"
                try:
                    control.write_bytes(b"P11-H13-HOST-CONTROL")
                    if control.read_bytes() != b"P11-H13-HOST-CONTROL":
                        raise OSError()
                    control.unlink()
                except OSError:
                    raise ProbeError("HOST_OUTSIDE_CONTROL_FAILED") from None
                if inside.exists() or target.exists():
                    raise ProbeError("TEMP_PRECONDITION_FAILED")
                child = workspace / "child.py"
                child.write_text(CHILD_CODE, encoding="utf-8")
                env = h1.env_for_isolated_home(home)
                env["P11_H13_WORKSPACE"] = str(workspace)
                env["P11_H13_OUTSIDE"] = str(outside)
                out, err, rc = run_subprocess(
                    command_for(h1.CLI, Path(sys.executable), child),
                    env, str(workspace))
                result = evaluate(out, err, rc,
                    inside.exists() and inside.read_bytes() == b"P11-H13-INSIDE-OK",
                    not target.exists())
    except OSError:
        raise ProbeError("TEMPORARY_CLEANUP_FAILED") from None
    result["temporary_directories_removed"] = True
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-local-mxc-probe", action="store_true",
                        help="Explicit standalone Windows MXC negative test; no model")
    args = parser.parse_args(argv)
    try:
        result = run_local() if args.execute_local_mxc_probe else plan()
    except (ProbeError, OSError, ValueError, TypeError) as exc:
        print("STOP: H13_STANDALONE_MXC_FAILED:" + safe_reason(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
