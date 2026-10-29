#!/usr/bin/env python3
"""P1.1 H1.3c: gated no-model Windows Job Object descendant containment probe.

Default: print PLAN_ONLY_NO_PROCESS. Opt-in real run creates one suspended
Python runner, assigns it to a fresh kill-on-close Windows Job Object BEFORE
resuming, and has it launch one pinned standalone MXC sandbox canary. A
controlled sandbox Python child launches one sleeping leaf and writes only
synthetic PIDs in a disposable workspace. The parent verifies OS Job membership,
terminates the Job, and waits on pinned process handles. It never sends a model
turn, never reads real profiles, and never prints PIDs, paths, stderr or secrets.

IMPORTANT: Job termination is an explicit *harness action*, not proof that
Codex itself automatically cleans up descendants. Unknown descendants or
escaped processes are NOT exhaustively attested. Fail closed on missing OS
evidence. The parent must be nonadministrator.
"""
import argparse
import ctypes
from ctypes import wintypes
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "h13c_core", HERE / "Probe-CodexAB-H13MXC.py")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

CONTRACT = "p1.1-h13c-windows-mxc-job-controlled-descendant-v1"
MAX_JOB_PIDS = 64
READY_TIMEOUT_S = 14
JOB_CLOSE_WAIT_MS = 5000
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
SYNCHRONIZE = 0x00100000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
MAX_READY_BYTES = 256

RUNNER = r'''import json, os, subprocess, threading
from pathlib import Path
cmd = json.loads(os.environ["P11_H13C_CMD"])
w = Path(os.environ["P11_H13C_WORKSPACE"])
observed = w / "h13c-stderr-present"
watcher = w / "h13c-stderr-observer-ready"

# Raw stderr is read in memory and discarded, never printed or persisted.
# The first byte or any observer failure writes only a fixed boolean marker.
def observe(stream):
    try:
        first = stream.read(1)
        if first:
            observed.write_bytes(b"1")
            while stream.read(4096):
                pass
    except BaseException:
        observed.write_bytes(b"1")

with subprocess.Popen(
        cmd, cwd=os.getcwd(), env=os.environ.copy(),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE) as child:
    thread = threading.Thread(target=observe, args=(child.stderr,), daemon=True)
    thread.start()
    watcher.write_bytes(b"1")
    child.wait(timeout=25)
    thread.join(timeout=1)
    if thread.is_alive():
        observed.write_bytes(b"1")
'''

LEAF = r'''import time
time.sleep(25)
'''

CHILD = r'''import json, os, subprocess, sys, time
from pathlib import Path
w = Path(os.environ["P11_H13C_WORKSPACE"])
leaf = subprocess.Popen(
    [sys.executable, "-B", str(w / "leaf.py")], cwd=str(w),
    env=os.environ.copy(), stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
payload = json.dumps({"child_pid": os.getpid(), "leaf_pid": leaf.pid},
                     separators=(",", ":"), sort_keys=True)
tmp = w / "h13c-ready.tmp"
tmp.write_text(payload, encoding="ascii")
os.replace(tmp, w / "h13c-ready.json")
# Parent independently observes both processes and kills its Job Object.
time.sleep(25)
'''


class GateError(Exception):
    pass


SAFE_CODES = frozenset({
    "WINDOWS_ONLY", "WINDOWS_API_UNAVAILABLE", "JOB_CREATE_FAILED",
    "JOB_LIMIT_FAILED", "ROOT_CREATE_FAILED", "ROOT_JOB_ASSIGN_FAILED",
    "ROOT_RESUME_FAILED", "JOB_PROCESS_QUERY_FAILED",
    "JOB_PROCESS_LIST_OVERFLOW", "READY_TIMEOUT_OR_INVALID",
    "READY_PROCESS_NOT_IN_JOB", "ROOT_NOT_IN_JOB",
    "PROCESS_HANDLE_QUERY_FAILED", "PROCESS_NOT_RUNNING_AT_SNAPSHOT",
    "JOB_TERMINATE_FAILED", "JOB_PROCESS_STILL_ALIVE",
    "JOB_NOT_EMPTY_AFTER_TERMINATE", "TEMPORARY_CLEANUP_FAILED",
    "HARNESS_PRECONDITION_FAILED",
    "MXC_SANDBOX_STDERR_OBSERVED",
    "MXC_STDERR_OBSERVER_NOT_READY",
})


def safe_error(exc):
    if isinstance(exc, GateError) and len(exc.args) == 1 and exc.args[0] in SAFE_CODES:
        return exc.args[0]
    if isinstance(exc, core.ProbeError):
        return core.safe_reason(exc)
    return "UNCLASSIFIED_LOCAL_FAILURE"


def plan():
    return {
        "contract": CONTRACT,
        "mode": "PLAN_ONLY_NO_PROCESS",
        "target_cli": core.h1.VERSION,
        "backend_requested": "windows.sandbox=mxc",
        "permissions_requested": ":workspace",
        "real_test_requires_explicit_flag": True,
        "suspended_root_assigned_before_resume": True,
        "job_kill_on_close_requested": True,
        "controlled_child_and_leaf_required": True,
        "independent_job_membership_required": True,
        "independent_handle_signaled_after_harness_termination": True,
        "real_windows_job_invoked": False,
        "codex_automatic_descendant_cleanup_verified": False,
        "all_unknown_descendants_attested": False,
        "appserver_turn_mxc_verified": False,
        "worker_provenance_verified": False,
        "model_calls_made": 0,
        "thread_start_sent": False,
        "turn_start_sent": False,
        "candidate_merge_authorized": False,
    }


def verify_snapshot(job_pids, root_pid, child_pid, leaf_pid):
    """Pure validation, OS data must be supplied by QueryInformationJobObject."""
    if (not isinstance(job_pids, (tuple, list)) or
            len(job_pids) > MAX_JOB_PIDS or
            not all(type(x) is int and x > 0 for x in job_pids) or
            len(set(job_pids)) != len(job_pids)):
        raise GateError("JOB_PROCESS_QUERY_FAILED")
    expected = (root_pid, child_pid, leaf_pid)
    if not all(type(x) is int and x > 0 for x in expected) or len(set(expected)) != 3:
        raise GateError("READY_TIMEOUT_OR_INVALID")
    if root_pid not in job_pids:
        raise GateError("ROOT_NOT_IN_JOB")
    if child_pid not in job_pids or leaf_pid not in job_pids:
        raise GateError("READY_PROCESS_NOT_IN_JOB")
    return {
        "root_observed_in_job": True,
        "controlled_child_observed_in_job": True,
        "controlled_leaf_observed_in_job": True,
        "job_snapshot_at_least_three_processes": len(job_pids) >= 3,
    }


def verify_cleanup(handle_signaled, remaining_job_pids):
    """Only known observed process handles + the enumerated Job at end."""
    if (not isinstance(handle_signaled, dict) or
            set(handle_signaled) != {"root", "child", "leaf"} or
            not all(v is True for v in handle_signaled.values())):
        raise GateError("JOB_PROCESS_STILL_ALIVE")
    if (not isinstance(remaining_job_pids, list) or remaining_job_pids):
        raise GateError("JOB_NOT_EMPTY_AFTER_TERMINATE")
    return {
        "root_handle_signaled_after_harness_job_termination": True,
        "controlled_child_handle_signaled_after_harness_job_termination": True,
        "controlled_leaf_handle_signaled_after_harness_job_termination": True,
        "job_empty_after_harness_termination": True,
    }


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class JOB_BASIC_LIMIT(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOB_EXTENDED_LIMIT(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOB_BASIC_LIMIT),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]


class JOB_PID_LIST(ctypes.Structure):
    _fields_ = [
        ("NumberOfAssignedProcesses", wintypes.DWORD),
        ("NumberOfProcessIdsInList", wintypes.DWORD),
        ("ProcessIdList", ctypes.c_size_t * MAX_JOB_PIDS),
    ]


def kernel32():
    if os.name != "nt":
        raise GateError("WINDOWS_ONLY")
    try:
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k.SetInformationJobObject.restype = wintypes.BOOL
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.AssignProcessToJobObject.restype = wintypes.BOOL
        k.CreateProcessW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPWSTR,
            ctypes.c_void_p, ctypes.c_void_p,
            wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p,
            wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFOW),
            ctypes.POINTER(PROCESS_INFORMATION)]
        k.CreateProcessW.restype = wintypes.BOOL
        k.ResumeThread.argtypes = [wintypes.HANDLE]
        k.ResumeThread.restype = wintypes.DWORD
        k.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
            wintypes.DWORD, ctypes.c_void_p]
        k.QueryInformationJobObject.restype = wintypes.BOOL
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k.TerminateJobObject.restype = wintypes.BOOL
        k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k.TerminateProcess.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        return k
    except (OSError, AttributeError, TypeError, ValueError):
        raise GateError("WINDOWS_API_UNAVAILABLE") from None


def open_job(k):
    handle = k.CreateJobObjectW(None, None)
    if not handle:
        raise GateError("JOB_CREATE_FAILED")
    cfg = JOB_EXTENDED_LIMIT()
    cfg.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not k.SetInformationJobObject(
            handle, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(cfg), ctypes.sizeof(cfg)):
        k.CloseHandle(handle)
        raise GateError("JOB_LIMIT_FAILED")
    return handle


def create_suspended_runner(k, python_exe, runner_path, env, cwd):
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(startup)
    info = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer(subprocess.list2cmdline(
        [str(python_exe), "-B", str(runner_path)]))
    pairs = sorted(env.items(), key=lambda kv: kv[0].upper())
    env_block = ctypes.create_unicode_buffer(
        "\x00".join(k + "=" + v for k, v in pairs) + "\x00\x00")
    success = k.CreateProcessW(
        str(python_exe), cmd, None, None, False,
        CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
        ctypes.cast(env_block, ctypes.c_void_p), str(cwd),
        ctypes.byref(startup), ctypes.byref(info))
    if not success:
        raise GateError("ROOT_CREATE_FAILED")
    return info


def job_pids(k, job):
    packet = JOB_PID_LIST()
    if not k.QueryInformationJobObject(
            job, JOB_OBJECT_BASIC_PROCESS_ID_LIST,
            ctypes.byref(packet), ctypes.sizeof(packet), None):
        raise GateError("JOB_PROCESS_QUERY_FAILED")
    count = int(packet.NumberOfProcessIdsInList)
    if packet.NumberOfAssignedProcesses > MAX_JOB_PIDS or count > MAX_JOB_PIDS:
        raise GateError("JOB_PROCESS_LIST_OVERFLOW")
    out = [int(packet.ProcessIdList[i]) for i in range(count)]
    if len(set(out)) != len(out) or any(i <= 0 for i in out):
        raise GateError("JOB_PROCESS_QUERY_FAILED")
    return out


def ready_pids(path):
    try:
        if not path.is_file() or path.stat().st_size > MAX_READY_BYTES:
            raise ValueError()
        payload = json.loads(path.read_text(encoding="ascii"))
        if not isinstance(payload, dict) or set(payload) != {"child_pid", "leaf_pid"}:
            raise ValueError()
        if any(type(payload[k]) is not int or payload[k] <= 0
               for k in ("child_pid", "leaf_pid")):
            raise ValueError()
        if payload["child_pid"] == payload["leaf_pid"]:
            raise ValueError()
        return payload
    except (OSError, UnicodeError, ValueError, TypeError):
        raise GateError("READY_TIMEOUT_OR_INVALID") from None


def open_live_handles(k, expected_pids):
    handles = {}
    try:
        for label, pid in expected_pids.items():
            h = k.OpenProcess(
                SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                raise GateError("PROCESS_HANDLE_QUERY_FAILED")
            handles[label] = h
            if k.WaitForSingleObject(h, 0) != WAIT_TIMEOUT:
                raise GateError("PROCESS_NOT_RUNNING_AT_SNAPSHOT")
        return handles
    except BaseException:
        for h in handles.values():
            k.CloseHandle(h)
        raise


def report(snapshot, cleanup):
    return {
        "contract": CONTRACT,
        "status": "H13C_CONTROLLED_JOB_DESCENDANTS_TERMINATED_BY_HARNESS_PASS",
        "target_cli": core.h1.VERSION,
        "root_assigned_suspended_before_resume": True,
        "job_kill_on_close_enabled": True,
        "sandbox_stderr_boolean_marker_absent": True,
        **snapshot, **cleanup,
        "termination_actor": "test_harness_terminate_job_object",
        "codex_automatic_descendant_cleanup_verified": False,
        "unknown_descendant_escapes_independently_excluded": False,
        "complete_child_tree_cleanup_independently_attested": False,
        "worker_provenance_verified": False,
        "appserver_turn_mxc_verified": False,
        "network_isolation_verified": False,
        "model_calls_made": 0,
        "thread_start_sent": False,
        "turn_start_sent": False,
        "candidate_merge_authorized": False,
    }


def run_real():
    core.require_pinned_nonadmin_windows()
    k = kernel32()
    try:
        with core.disposable_probe_root("p11-h13c-job-") as root_name:
            root = Path(root_name)
            home, workspace = root / "codex-home", root / "workspace"
            home.mkdir()
            workspace.mkdir()
            for name, source in (
                ("runner.py", RUNNER), ("child.py", CHILD), ("leaf.py", LEAF)):
                (workspace / name).write_text(source, encoding="utf-8")
            env = core.mxc_env_for_isolated_home(home)
            env["P11_H13C_WORKSPACE"] = str(workspace)
            env["P11_H13C_CMD"] = json.dumps(core.command_for(
                core.h1.CLI, Path(sys.executable), workspace / "child.py"))
            # Echo compatibility first; it is NOT process tree evidence.
            out, err, rc = core.run_subprocess(
                core.compatibility_command(core.h1.CLI), env, str(workspace))
            core.evaluate_compatibility(out, err, rc)

            job = None
            info = None
            handles = {}
            snapshot = None
            cleanup = None
            failure = None
            assigned = False
            try:
                job = open_job(k)
                info = create_suspended_runner(
                    k, sys.executable, workspace / "runner.py", env, workspace)
                if not k.AssignProcessToJobObject(job, info.hProcess):
                    raise GateError("ROOT_JOB_ASSIGN_FAILED")
                assigned = True
                if k.ResumeThread(info.hThread) == 0xFFFFFFFF:
                    raise GateError("ROOT_RESUME_FAILED")

                ready = workspace / "h13c-ready.json"
                observed_stderr = workspace / "h13c-stderr-present"
                watcher_ready = workspace / "h13c-stderr-observer-ready"
                deadline = time.monotonic() + READY_TIMEOUT_S
                while not ready.exists() and time.monotonic() < deadline:
                    if observed_stderr.exists():
                        raise GateError("MXC_SANDBOX_STDERR_OBSERVED")
                    time.sleep(0.05)
                if observed_stderr.exists():
                    raise GateError("MXC_SANDBOX_STDERR_OBSERVED")
                if not watcher_ready.exists():
                    raise GateError("MXC_STDERR_OBSERVER_NOT_READY")
                ids = ready_pids(ready)
                root_pid = int(info.dwProcessId)
                snapshot = verify_snapshot(
                    job_pids(k, job), root_pid,
                    ids["child_pid"], ids["leaf_pid"])
                handles = open_live_handles(k, {
                    "root": root_pid,
                    "child": ids["child_pid"],
                    "leaf": ids["leaf_pid"],
                })
            except (GateError, OSError, ValueError, TypeError) as exc:
                failure = exc
            finally:
                # Always attempt targeted job termination on assigned root.
                terminated = False
                if job and assigned:
                    terminated = bool(k.TerminateJobObject(job, 1))
                if job and assigned and not terminated:
                    failure = GateError("JOB_TERMINATE_FAILED")
                if snapshot and handles and terminated:
                    signaled = {
                        label: k.WaitForSingleObject(h, JOB_CLOSE_WAIT_MS) == WAIT_OBJECT_0
                        for label, h in handles.items()
                    }
                    try:
                        cleanup = verify_cleanup(signaled, job_pids(k, job))
                    except GateError as exc:
                        failure = exc
                for h in handles.values():
                    k.CloseHandle(h)
                if info:
                    # Suspend-before-assign avoids an uncontained spawn race.
                    # If assign/resume failed, terminate the still-suspended
                    # directly-created disposable process before closing it.
                    if not assigned:
                        try:
                            if not k.TerminateProcess(info.hProcess, 1):
                                failure = GateError("JOB_TERMINATE_FAILED")
                        except (AttributeError, OSError):
                            failure = GateError("JOB_TERMINATE_FAILED")
                    k.CloseHandle(info.hThread)
                    k.CloseHandle(info.hProcess)
                if job:
                    k.CloseHandle(job)
            # Enforce a final independent check even if the child warning
            # appeared after ready and before the test harness terminated it.
            if (workspace / "h13c-stderr-present").exists():
                failure = GateError("MXC_SANDBOX_STDERR_OBSERVED")
            if failure:
                raise failure
            if not snapshot or not cleanup:
                raise GateError("JOB_PROCESS_QUERY_FAILED")
            output = report(snapshot, cleanup)
    except OSError:
        raise GateError("TEMPORARY_CLEANUP_FAILED") from None
    output["temporary_probe_directories_removed"] = True
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-local-job-tree-probe", action="store_true",
                        help="One pinned standalone MXC Job Object descendant test; no model")
    args = parser.parse_args(argv)
    try:
        result = run_real() if args.execute_local_job_tree_probe else plan()
    except (core.ProbeError, GateError, OSError, ValueError, TypeError) as exc:
        print("STOP: H13C_JOB_TREE_FAILED:" + safe_error(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
