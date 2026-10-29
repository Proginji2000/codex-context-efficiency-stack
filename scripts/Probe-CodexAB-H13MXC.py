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
    "COMPAT_STDOUT_INVALID",
    "COMPAT_STDERR_PRESENT",
    "COMPAT_EXIT_NONZERO",
    "WINDOWS_BUILD_QUERY_FAILED",
    "MXC_DOCUMENTED_BUILD_TOO_OLD",
    "MXC_BUILD_OUTSIDE_DOCUMENTED_MATRIX",
    "MXC_HOST_ENV_REQUIRED_MISSING",
    "MXC_HOST_SYSTEMDRIVE_INVALID",
    "MXC_DISPOSABLE_PROFILE_PARENT_UNSAFE",
})

STDERR_CLASSES = frozenset({
    "BACKEND_LAUNCH_ERROR", "SECURITY_WARNING", "CLI_USAGE_ERROR",
    "CONFIG_ERROR", "CHILD_PYTHON_ERROR", "GENERAL_WARNING",
    "UNRECOGNIZED_STDERR", "MXC_NATIVE_UNAVAILABLE",
    "MXC_LAUNCHER_FAILURE", "MXC_POLICY_RESTRICTION",
    "MXC_DENY_PATHS_UNAVAILABLE", "MXC_INVALID_LAUNCHER_REQUEST",
    "MXC_ENV_UNICODE_INVALID", "MXC_WINDOWS_VOLUME_ERROR",
    "MXC_PLATFORM_DIRECTORY_ERROR", "MXC_COM_INIT_ERROR",
    "MXC_WINDOWS_DIRECTORY_ERROR", "MXC_CWD_INVALID",
    "MXC_UNSUPPORTED_POLICY_MODE", "MXC_CHILD_WAIT_ERROR",
})
MARKER_FLAGS = frozenset({"MARKER_PRESENT", "MARKER_ABSENT"})
EXIT_FLAGS = frozenset({"EXIT_ZERO", "EXIT_NONZERO", "EXIT_UNKNOWN"})


def classify_stderr(data):
    """Only coarse fixed categories; no raw stderr, path, token or hash escapes."""
    if not isinstance(data, bytes):
        return "UNRECOGNIZED_STDERR"
    message = data[:MAX_CAPTURE].decode("utf-8", "replace").lower()
    if ("worldwritable" in message or "world writable" in message
            or "security warning" in message or "sandbox warning" in message):
        return "SECURITY_WARNING"
    # Fatal MXC errors take precedence over generic 'warning:' lines emitted
    # before the actual error. No raw error bytes leave this process.
    if ("native mxc is unavailable" in message or
            "mxc is unavailable on this windows build" in message):
        return "MXC_NATIVE_UNAVAILABLE"
    # Exact pinned rust-v0.165.0 diagnostics, from mxc-sandbox:
    # windows.rs, native.rs, policy.rs and lib.rs. Report only local
    # fixed category codes and NEVER publish SDK error_message/paths/HRESULT.
    if "cannot enforce native mxc deny paths" in message:
        return "MXC_DENY_PATHS_UNAVAILABLE"
    if "invalid mxc launcher request" in message:
        return "MXC_INVALID_LAUNCHER_REQUEST"
    if "mxc requires unicode environment variable" in message:
        return "MXC_ENV_UNICODE_INVALID"
    if "cannot enumerate windows volumes" in message:
        return "MXC_WINDOWS_VOLUME_ERROR"
    if "cannot locate required windows platform directory" in message:
        return "MXC_PLATFORM_DIRECTORY_ERROR"
    if "cannot initialize com" in message:
        return "MXC_COM_INIT_ERROR"
    if "cannot locate the windows directory" in message:
        return "MXC_WINDOWS_DIRECTORY_ERROR"
    if ("mxc requires an absolute policy working directory" in message
            or "mxc requires an absolute command working directory" in message):
        return "MXC_CWD_INVALID"
    if "mxc native launch does not support permissivelearningmode" in message:
        return "MXC_UNSUPPORTED_POLICY_MODE"
    if "waiting for the mxc command" in message:
        return "MXC_CHILD_WAIT_ERROR"
    if ("mxc launcher:" in message or
            "createprocesssecurityenvironment failed" in message or
            "failed to prepare mxc sandbox" in message):
        return "MXC_LAUNCHER_FAILURE"
    if ("allow_mxc" in message or
            "permission profile" in message and ("not found" in message or "denied" in message)
            or "mxc is disabled by policy" in message):
        return "MXC_POLICY_RESTRICTION"
    if ("windows sandbox failed" in message or
            "failed to build runtime" in message or
            "missing mxc wrapper" in message):
        return "BACKEND_LAUNCH_ERROR"
    if ("usage: codex" in message or "unexpected argument" in message
            or "unrecognized subcommand" in message
            or "invalid value for" in message
            or "the following required arguments" in message):
        return "CLI_USAGE_ERROR"
    if ("failed to load config" in message or
            "failed to parse config" in message or
            "invalid configuration" in message or
            "unknown config key" in message or
            "invalid type" in message):
        return "CONFIG_ERROR"
    if ("traceback (most recent call last)" in message or
            "modulenotfounderror" in message or
            "can't open file" in message or
            "fatal python error" in message):
        return "CHILD_PYTHON_ERROR"
    if ("warning:" in message or "warn:" in message):
        return "GENERAL_WARNING"
    return "UNRECOGNIZED_STDERR"


def safe_reason(exc):
    if isinstance(exc, ProbeError):
        if len(exc.args) == 1 and exc.args[0] in CODES:
            return exc.args[0]
        if (len(exc.args) == 4 and
                exc.args[0] in ("SANDBOX_STDERR_PRESENT", "COMPAT_STDERR_PRESENT") and
                exc.args[1] in STDERR_CLASSES and
                exc.args[2] in MARKER_FLAGS and
                exc.args[3] in EXIT_FLAGS):
            return ":".join(exc.args)
    return "OTHER_LOCAL_FAILURE"

DOCUMENTED_MINIMUM_UBR = 9278
DOCUMENTED_WIN11_BUILDS = frozenset({26100, 26200})


def assess_windows_build(build, ubr):
    """Documented OS-build threshold, not a check of native MXC capability."""
    if type(build) is not int or type(ubr) is not int or build < 0 or ubr < 0:
        raise ProbeError("WINDOWS_BUILD_QUERY_FAILED")
    if build not in DOCUMENTED_WIN11_BUILDS:
        return "OUTSIDE_DOCUMENTED_BUILD_MATRIX"
    if ubr < DOCUMENTED_MINIMUM_UBR:
        return "BELOW_DOCUMENTED_MINIMUM"
    return "DOCUMENTED_BUILD_THRESHOLD_MET"


def query_windows_build():
    """Read only nonpersonal OS build/UBR fields from HKLM; no process."""
    if os.name != "nt":
        raise ProbeError("WINDOWS_ONLY")
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
                0, winreg.KEY_READ) as handle:
            build_str = winreg.QueryValueEx(handle, "CurrentBuildNumber")[0]
            ubr = winreg.QueryValueEx(handle, "UBR")[0]
        if not isinstance(build_str, str) or not build_str.isdecimal():
            raise ValueError("bad build format")
        build = int(build_str)
        if type(ubr) is not int:
            raise ValueError("bad UBR")
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        raise ProbeError("WINDOWS_BUILD_QUERY_FAILED") from None
    return build, ubr


def windows_build_report(build, ubr):
    return {
        "contract": CONTRACT,
        "mode": "READ_ONLY_OS_BUILD_CHECK",
        "windows_build": build,
        "windows_revision": ubr,
        "documented_minimum_revision": DOCUMENTED_MINIMUM_UBR,
        "os_threshold_status": assess_windows_build(build, ubr),
        "mxc_native_capability_verified": False,
        "managed_policy_mxc_allowed_verified": False,
        "standalone_mxc_runtime_verified": False,
        "appserver_turn_mxc_verified": False,
        "processes_launched": 0,
        "model_calls_made": 0,
    }


def _is_host_env_present(key, env):
    # Windows environment variable names are case-insensitive; returning only
    # a boolean avoids leaking the actual user-specific variable values.
    return any(k.upper() == key.upper() and isinstance(v, str) and bool(v)
               for k, v in env.items())


def _windows_systemdrive(env):
    """Extract only a canonical drive designator; never print user values."""
    for name, value in env.items():
        if name.upper() != "SYSTEMDRIVE":
            continue
        if (not isinstance(value, str) or len(value) != 2 or
                not value[0].isascii() or not value[0].isalpha() or
                value[1] != ":"):
            raise ProbeError("MXC_HOST_SYSTEMDRIVE_INVALID")
        return value[0].upper() + ":"
    raise ProbeError("MXC_HOST_ENV_REQUIRED_MISSING")


def mxc_env_for_isolated_home(home, source=None):
    """H1-safe child env plus the single upstream-required SystemDrive key.

    Keep H1.2's original global SAFE_ENV unchanged. Codex rust-v0.165.0
    mxc-sandbox/src/transport.rs explicitly reads host SystemDrive.
    No other ambient variable is copied. No system/user settings change.
    """
    source = os.environ if source is None else source
    child = h1.env_for_isolated_home(home, source)
    child["SystemDrive"] = _windows_systemdrive(source)
    if not _is_host_env_present("LOCALAPPDATA", child):
        raise ProbeError("MXC_HOST_ENV_REQUIRED_MISSING")
    return child


def host_environment_report(env=None):
    """Read-only, zero-process launch prerequisites from pinned MXC transport."""
    if os.name != "nt":
        raise ProbeError("WINDOWS_ONLY")
    env = os.environ if env is None else env
    keys = {
        "system_drive_present": _is_host_env_present("SystemDrive", env),
        "local_app_data_present": _is_host_env_present("LOCALAPPDATA", env),
        "system_root_present": _is_host_env_present("SystemRoot", env),
    }
    try:
        valid_drive = bool(_windows_systemdrive(env))
    except ProbeError:
        valid_drive = False
    keys["system_drive_format_valid"] = valid_drive
    return {
        "contract": CONTRACT,
        "mode": "READ_ONLY_MXC_HOST_ENV_CHECK",
        **keys,
        "required_mxc_transport_host_env_present":
            keys["system_drive_present"] and keys["local_app_data_present"],
        "mxc_native_capability_verified": False,
        "standalone_mxc_runtime_verified": False,
        "appserver_turn_mxc_verified": False,
        "processes_launched": 0,
        "model_calls_made": 0,
    }


def plan():
    return {
        "contract": CONTRACT, "mode": "PLAN_ONLY_NO_PROCESS",
        "cli_version": h1.VERSION, "backend_requested": "windows.sandbox=mxc",
        "permissions_requested": ":workspace",
        "preflight": "official_mxc_compatibility_echo_before_fs_negative_test",
        "requires_explicit_nonadmin_flag": True,
        "read_only_os_build_check_available": True,
        "compat_only_diagnostic_available": True,
        "read_only_host_env_check_available": True,
        "standalone_mxc_runtime_verified": False,
        "appserver_turn_mxc_verified": False,
        "network_isolation_verified": False,
        "worker_provenance_verified": False,
        "child_tree_cleanup_attested": False,
        "model_calls_made": 0, "thread_start_sent": False,
        "turn_start_sent": False, "candidate_merge_authorized": False,
    }

def command_for(cli, python, child):
    # Exact explicit MXC and :workspace permissions profile from the
    # official Codex Windows diagnostic instructions (CLI >= 0.162.0).
    # The -- separator prevents flags to the child being parsed by Codex.
    return [str(cli), "-c", "windows.sandbox=mxc",
            "sandbox", "--include-managed-config",
            "--permission-profile", ":workspace", "--",
            str(python), "-B", str(child)]


def compatibility_command(cli):
    # No file writes or model; run BEFORE the filesystem negative test.
    return [str(cli), "-c", "windows.sandbox=mxc",
            "sandbox", "--include-managed-config",
            "--permission-profile", ":workspace", "--",
            "cmd.exe", "/d", "/c", "echo", "MXC_OK"]


def evaluate_compatibility(out, err, rc):
    # A warning is never silently ignored, even if MXC_OK is printed.
    if not isinstance(out, bytes) or len(out) > MAX_CAPTURE:
        raise ProbeError("COMPAT_STDOUT_INVALID")
    if not isinstance(err, bytes) or len(err) > MAX_CAPTURE:
        raise ProbeError("COMPAT_STDOUT_INVALID")
    if err:
        marker = "MARKER_PRESENT" if out.strip() == b"MXC_OK" else "MARKER_ABSENT"
        code = ("EXIT_ZERO" if rc == 0 else "EXIT_NONZERO"
                if isinstance(rc, int) else "EXIT_UNKNOWN")
        raise ProbeError("COMPAT_STDERR_PRESENT", classify_stderr(err), marker, code)
    if rc != 0:
        raise ProbeError("COMPAT_EXIT_NONZERO")
    if out.strip() != b"MXC_OK":
        raise ProbeError("COMPAT_STDOUT_INVALID")
    return True


def evaluate(out, err, rc, inside_ok, outside_unchanged):
    if not isinstance(out, bytes) or len(out) > MAX_CAPTURE:
        raise ProbeError("SANDBOX_STDOUT_INVALID")
    if not isinstance(err, bytes) or len(err) > MAX_CAPTURE:
        raise ProbeError("SANDBOX_STDERR_PRESENT")
    if err:
        # Retain fail-closed semantics: ANY stderr is STOP. Only emit fixed
        # diagnostics derived from bounded text, stdout marker presence and
        # exit-code class. Never echo or hash stderr (which may contain secrets).
        marker_flag = ("MARKER_PRESENT" if isinstance(out, bytes) and
                       out.startswith(MARKER.encode("utf-8"))
                       else "MARKER_ABSENT")
        exit_flag = ("EXIT_ZERO" if rc == 0 else
                     "EXIT_NONZERO" if isinstance(rc, int) else "EXIT_UNKNOWN")
        raise ProbeError("SANDBOX_STDERR_PRESENT", classify_stderr(err),
                         marker_flag, exit_flag)
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
        "permissions_requested": ":workspace",
        "documented_compatibility_probe_pass": True,
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

def require_pinned_nonadmin_windows():
    """Preflight both isolated runtime modes; never elevate or change config."""
    if os.name != "nt":
        raise ProbeError("WINDOWS_ONLY")
    if ctypes.windll.shell32.IsUserAnAdmin():
        raise ProbeError("NON_ADMIN_REQUIRED")
    build, ubr = query_windows_build()
    status = assess_windows_build(build, ubr)
    if status == "BELOW_DOCUMENTED_MINIMUM":
        raise ProbeError("MXC_DOCUMENTED_BUILD_TOO_OLD")
    if status != "DOCUMENTED_BUILD_THRESHOLD_MET":
        raise ProbeError("MXC_BUILD_OUTSIDE_DOCUMENTED_MATRIX")
    if not host_environment_report()["required_mxc_transport_host_env_present"]:
        raise ProbeError("MXC_HOST_ENV_REQUIRED_MISSING")
    # Reject malformed SystemDrive before invoking Codex; do not synthesize
    # a drive letter or silently substitute a different system volume.
    _windows_systemdrive(os.environ)
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


def validate_disposable_parent(home_path, system_temp_path):
    """Pure policy check against the Codex arg0 CODEX_HOME-under-TEMP guard."""
    try:
        home = Path(home_path)
        if home.is_symlink():
            raise ProbeError("MXC_DISPOSABLE_PROFILE_PARENT_UNSAFE")
        actual_home = home.resolve(strict=True)
        actual_temp = Path(system_temp_path).resolve(strict=True)
        if (not actual_home.is_dir() or actual_home == actual_temp or
                actual_home.is_relative_to(actual_temp)):
            raise ProbeError("MXC_DISPOSABLE_PROFILE_PARENT_UNSAFE")
        return actual_home
    except (OSError, RuntimeError, ValueError, TypeError):
        raise ProbeError("MXC_DISPOSABLE_PROFILE_PARENT_UNSAFE") from None


def private_probe_parent():
    """Private user profile, never SYSTEM TEMP or the existing CODEX_HOME."""
    return validate_disposable_parent(Path.home(), tempfile.gettempdir())


def disposable_probe_root(prefix):
    """Construct only a fresh random temporary directory under user home."""
    return tempfile.TemporaryDirectory(prefix=prefix, dir=private_probe_parent())


def run_compatibility_only():
    """One exact documented native MXC echo; NO filesystem negative canary.

    Creates only a disposable CODEX_HOME and empty workspace. Does not read
    real sessions, run app-server, change ACLs or fall back to another sandbox.
    """
    require_pinned_nonadmin_windows()
    try:
        with disposable_probe_root("p11-h13-compat-") as rt:
            root = Path(rt)
            home, workspace = root / "codex-home", root / "workspace"
            home.mkdir()
            workspace.mkdir()
            env = mxc_env_for_isolated_home(home)
            out, err, rc = run_subprocess(
                compatibility_command(h1.CLI), env, str(workspace))
            evaluate_compatibility(out, err, rc)
    except OSError:
        raise ProbeError("TEMPORARY_CLEANUP_FAILED") from None
    return {
        "contract": CONTRACT,
        "status": "MXC_COMPAT_STANDALONE_ECHO_PASS_NOT_ENFORCEMENT",
        "target_cli": h1.VERSION,
        "mode": "EXPLICIT_COMPAT_ONLY_NO_MODEL",
        "windows_build_threshold_met": True,
        "mxc_cli_backend_requested": True,
        "compatibility_echo_observed": True,
        "stderr_empty": True,
        "filesystem_negative_test_executed": False,
        "appserver_turn_mxc_verified": False,
        "standalone_filesystem_isolation_verified": False,
        "network_isolation_verified": False,
        "worker_provenance_verified": False,
        "child_tree_cleanup_independently_attested": False,
        "model_calls_made": 0,
        "turn_start_sent": False,
        "temporary_profile_and_workspace_deleted": True,
        "candidate_merge_authorized": False,
    }


def run_local():
    require_pinned_nonadmin_windows()
    try:
        with disposable_probe_root("p11-h13-work-") as rt:
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
                env = mxc_env_for_isolated_home(home)
                env["P11_H13_WORKSPACE"] = str(workspace)
                env["P11_H13_OUTSIDE"] = str(outside)
                # One documented MXC compatibility launch first. A failed
                # or warning-emitting compatibility check blocks all subsequent
                # filesystem test activity.
                compat_out, compat_err, compat_rc = run_subprocess(
                    compatibility_command(h1.CLI), env, str(workspace))
                evaluate_compatibility(compat_out, compat_err, compat_rc)

                # Only after the compatibility gate: single standalone
                # filesystem negative probe. No model, auth or agent turn.
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
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--execute-local-mxc-probe", action="store_true",
                       help="Explicit standalone Windows MXC negative test; no model")
    group.add_argument("--check-windows-build", action="store_true",
                       help="Read only Windows build and UBR from HKLM, no subprocess")
    group.add_argument("--execute-local-mxc-compat-only", action="store_true",
                       help="One pinned MXC echo only, no filesystem negative test or model")
    group.add_argument("--check-mxc-host-environment", action="store_true",
                       help="Read-only presence of MXC host env prerequisites, no process")
    args = parser.parse_args(argv)
    try:
        if args.check_windows_build:
            result = windows_build_report(*query_windows_build())
        elif args.check_mxc_host_environment:
            result = host_environment_report()
        elif args.execute_local_mxc_compat_only:
            result = run_compatibility_only()
        elif args.execute_local_mxc_probe:
            result = run_local()
        else:
            result = plan()
    except (ProbeError, OSError, ValueError, TypeError) as exc:
        print("STOP: H13_STANDALONE_MXC_FAILED:" + safe_reason(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
