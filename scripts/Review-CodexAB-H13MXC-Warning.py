#!/usr/bin/env python3
"""Opt-in, LOCAL-SCREEN-ONLY review of one H1.3 native MXC stderr warning.

Important: shows the exact stderr in a local Windows message box solely for
operator review. Raw stderr is never printed to terminal, written to disk,
uploaded or included in a GitHub artifact. The warning remains STOP.
No filesystem negative canary, model, thread or turn is executed.
"""
import argparse
import ctypes
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("p11_h13_review_core",
                                                 ROOT / "Probe-CodexAB-H13MXC.py")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

CONTRACT = "p1.1-h13-private-local-warning-review-v1"


class ReviewError(Exception):
    pass


ERROR_CODES = frozenset({
    "LOCAL_DIALOG_UNAVAILABLE",
    "LOCAL_WARNING_TOO_LARGE",
    "LOCAL_WARNING_ABSENT",
    "TEMPORARY_CLEANUP_FAILED",
})


def show_only_on_local_screen(stderr_text):
    """Never return the message or print it to stdout/stderr."""
    title = "PRIVATE MXC WARNING — DO NOT COPY INTO CHAT OR GITHUB"
    heading = (
        "Native Codex MXC stderr. Review ONLY on this PC.\n"
        "Do not screenshot, upload or paste raw paths, account data or tokens.\n"
        "Describe only the non-sensitive warning type afterward.\n\n"
    )
    try:
        # Parent runs non-admin on interactive Windows desktop. MessageBoxW
        # transfers text to local UI, not network or disk.
        result = ctypes.windll.user32.MessageBoxW(
            None, heading + stderr_text, title, 0x00000040)
    except (AttributeError, OSError, ValueError, TypeError):
        raise ReviewError("LOCAL_DIALOG_UNAVAILABLE") from None
    if result == 0:
        raise ReviewError("LOCAL_DIALOG_UNAVAILABLE")


def inspect_result(stdout, stderr, rc, display=show_only_on_local_screen):
    """Review-only outcome; NEVER turns stderr into a pass or security proof."""
    if not isinstance(stderr, bytes) or len(stderr) > core.MAX_CAPTURE:
        raise ReviewError("LOCAL_WARNING_TOO_LARGE")
    if not stderr:
        # A normal successful command does not require a private warning UI.
        core.evaluate_compatibility(stdout, stderr, rc)
        return {
            "contract": CONTRACT,
            "status": "MXC_COMPAT_ECHO_PASS_NO_WARNING_NOT_ENFORCEMENT",
            "stderr_present": False,
            "native_filesystem_enforcement_verified": False,
            "appserver_turn_mxc_verified": False,
            "model_calls_made": 0,
            "turn_start_sent": False,
        }
    if not isinstance(stdout, bytes) or len(stdout) > core.MAX_CAPTURE:
        raise core.ProbeError("COMPAT_STDOUT_INVALID")
    display(stderr.decode("utf-8", "replace"))
    marker = "MARKER_PRESENT" if stdout.strip() == b"MXC_OK" else "MARKER_ABSENT"
    status = "EXIT_ZERO" if rc == 0 else "EXIT_NONZERO" if isinstance(rc, int) else "EXIT_UNKNOWN"
    return {
        "contract": CONTRACT,
        "status": "LOCAL_WARNING_REVIEWED_STILL_STOP",
        "stderr_present": True,
        "stderr_category": core.classify_stderr(stderr),
        "stdout_marker": marker,
        "child_exit_class": status,
        "raw_stderr_shared_or_persisted": False,
        "native_filesystem_enforcement_verified": False,
        "appserver_turn_mxc_verified": False,
        "model_calls_made": 0,
        "turn_start_sent": False,
    }


def run_single_review():
    # Pinned CLI 0.165.0, nonadmin, eligible Windows build, exact host
    # prerequisites, no privileges or global configuration modification.
    core.require_pinned_nonadmin_windows()
    try:
        with tempfile.TemporaryDirectory(prefix="p11-h13-review-") as d:
            root = Path(d)
            home, workspace = root / "codex-home", root / "workspace"
            home.mkdir()
            workspace.mkdir()
            env = core.mxc_env_for_isolated_home(home)
            stdout, stderr, rc = core.run_subprocess(
                core.compatibility_command(core.h1.CLI), env, str(workspace))
            result = inspect_result(stdout, stderr, rc)
    except OSError:
        raise ReviewError("TEMPORARY_CLEANUP_FAILED") from None
    result["temporary_profile_and_workspace_removed"] = True
    return result


def plan():
    return {
        "contract": CONTRACT,
        "mode": "PLAN_ONLY_NO_PROCESS",
        "explicit_single_review_flag_required": True,
        "exact_stderr_visible_only_in_private_local_dialog": True,
        "raw_stderr_printed_to_terminal": False,
        "raw_stderr_written_to_disk": False,
        "actual_native_mxc_invoked": False,
        "native_filesystem_enforcement_verified": False,
        "appserver_turn_mxc_verified": False,
        "model_calls_made": 0,
        "turn_start_sent": False,
        "candidate_merge_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-one-private-local-review", action="store_true",
                        help="Run ONE native MXC echo; show raw warning locally only")
    args = parser.parse_args(argv)
    try:
        outcome = run_single_review() if args.execute_one_private_local_review else plan()
    except ReviewError as exc:
        code = exc.args[0] if len(exc.args) == 1 and exc.args[0] in ERROR_CODES else "LOCAL_REVIEW_UNKNOWN_ERROR"
        print("STOP: H13_PRIVATE_WARNING_REVIEW_FAILED:" + code, file=sys.stderr)
        return 2
    except (core.ProbeError, OSError, ValueError, TypeError) as exc:
        print("STOP: H13_PRIVATE_WARNING_REVIEW_FAILED:" + core.safe_reason(exc), file=sys.stderr)
        return 2
    print(json.dumps(outcome, indent=2, ensure_ascii=True))
    # Warning remains STOP even when child's exit code was 0.
    if outcome["status"] == "LOCAL_WARNING_REVIEWED_STILL_STOP":
        print("STOP: H13_NATIVE_WARNING_REQUIRES_OPERATOR_REVIEW", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
