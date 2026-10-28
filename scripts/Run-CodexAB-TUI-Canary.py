#!/usr/bin/env python3
"""P1.1: one opt-in INTERACTIVE Codex TUI canary; no raw chats collected.

This is intentionally not codex exec. It uses the same preserved isolated
baseline configuration and a NEW disposable Git fixture, checks results with
independent unittest/Git, and does not execute the candidate or touch projects.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib

SPEC = importlib.util.spec_from_file_location(
    "codex_ab_runner", Path(__file__).with_name("Run-CodexAB.py")
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

SCHEMA = 1
MODEL = "gpt-6-luna"


def validate_paths(pilot, output, repo):
    """Refuse any existing output and any path within the protected locations."""
    pilot = Path(pilot).expanduser().resolve(strict=True)
    repo = Path(repo).resolve(strict=True)
    output = Path(output).expanduser().resolve()
    if not pilot.is_dir() or pilot.is_symlink():
        raise ValueError("PILOT_NOT_DIRECTORY")
    if (output.exists() or output == Path.home().resolve() or
            output == repo or repo in output.parents or
            output == pilot or pilot in output.parents or
            output == repo.parent or output == pilot.parent or
            output == Path(output.anchor)):
        raise ValueError("UNSAFE_OR_EXISTING_OUTPUT")
    return pilot, output


def declared_sandbox_policy(home):
    """Read only known TOML policy fields. Never print paths, secrets or raw TOML."""
    with (home / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)
    windows = config.get("windows", {})
    if not isinstance(windows, dict):
        raise ValueError("WINDOWS_CONFIG_INVALID")
    output = {}
    for name, value in (
        ("approval_policy", config.get("approval_policy")),
        ("sandbox_mode", config.get("sandbox_mode")),
        ("windows_sandbox", windows.get("sandbox")),
    ):
        if value is None:
            output[name] = "not_declared"
        elif isinstance(value, str) and value in {
            "never", "on-request", "untrusted", "on-failure",
            "read-only", "workspace-write", "danger-full-access",
            "elevated", "unelevated", "disabled", "mxc",
        }:
            output[name] = value
        else:
            output[name] = "other_or_unrecognized"
    return output


def sanitized_report(workspace, exit_code, elapsed, approval="on-request",
                     declared_policy=None, windows_sandbox=None,
                     config_snapshot_check=None):
    checks = runner.verification_detail(workspace)
    # No TUI tool/event stream is available to this wrapper; evidence from the
    # interactive UI must be assessed separately, never synthesized.
    return {
        "schema_version": SCHEMA,
        "execution_surface": "codex-interactive-tui-not-exec",
        "model": MODEL,
        "sandbox": "workspace-write",
        "approval_policy_override_requested": approval,
        "windows_sandbox_override_requested": windows_sandbox or "none",
        "baseline_config_snapshot_check": config_snapshot_check,
        "declared_policy": declared_policy,
        "policy_effectiveness": "not_runtime_attested",
        "codex_cli_exit_code": exit_code,
        "elapsed_s": round(elapsed, 3),
        "verification": checks,
        "functional_and_scope_pass": checks["functional_and_scope_pass"],
        "worker_delegation_independently_verified": False,
        "worker_evidence_required": "Observe actual worker lifecycle in interactive TUI; stdout is not collected.",
        "raw_chat_saved_by_wrapper": False,
        "profile_session_persistence": "Codex may save its interactive session in the isolated baseline-home.",
        "note": "A passing code change is not sufficient proof of delegation. No claim about quota or comparison against candidate.",
    }


SAFE_ERROR_CODES = frozenset({
    "EXPLICIT_EXECUTE_REQUIRED", "PILOT_NOT_DIRECTORY",
    "UNSAFE_OR_EXISTING_OUTPUT", "ISOLATED_PROFILE_INVALID",
    "ISOLATED_CONFIG_HASH_MISMATCH", "WINDOWS_SANDBOX_UNSUPPORTED",
    "WINDOWS_SANDBOX_DISABLED", "WINDOWS_SANDBOX_MODE_UNKNOWN",
    "SANDBOX_MODE_FULL_ACCESS_DECLARED", "ISOLATED_PROFILE_MISSING",
    "MODEL_MISMATCH", "BENCHMARK_CONFIG_MISMATCH",
    "ISOLATED_PROFILE_REQUIRES_LOGIN", "CODEX_NOT_FOUND",
    "APPROVAL_POLICY_INVALID", "TUI_CANARY_NOT_FOUND",
    "WINDOWS_CONFIG_INVALID", "WINDOWS_SANDBOX_OVERRIDE_UNSUPPORTED",
    "WINDOWS_SANDBOX_OVERRIDE_REQUIRES_WINDOWS",
    "ISOLATED_CONFIG_DRIFT_NOT_ALLOWLISTED",
    "ORIGINAL_CANDIDATE_CONFIG_CHANGED",
    "CONFIG_DRIFT_FLAG_REQUIRES_MXC_NEVER",
})
STATE_ERROR_CODES = {
    "invalid experiment state": "EXPERIMENT_STATE_INVALID",
    "AGENTS fingerprint mismatch: experiment must stop": "AGENTS_FINGERPRINT_MISMATCH",
    "Codex CLI version changed since preparation": "CODEX_VERSION_CHANGED",
}


def classified_error(exc):
    """Allowlist diagnostic labels; NEVER echo exception content or private paths."""
    if isinstance(exc, tomllib.TOMLDecodeError):
        return "TOML_PARSE_FAILED"
    if isinstance(exc, PermissionError):
        return "FILE_ACCESS_DENIED"
    if isinstance(exc, FileNotFoundError):
        return "REQUIRED_FILE_NOT_FOUND"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "CHILD_CHECK_TIMED_OUT"
    if isinstance(exc, ValueError):
        message = str(exc)
        if message in SAFE_ERROR_CODES:
            return message
        if message in STATE_ERROR_CODES:
            return STATE_ERROR_CODES[message]
    return "UNCLASSIFIED_PREFLIGHT_FAILURE"


def diagnose(args):
    """Zero-model, read-only status matrix. Never display hashes, paths or TOML text."""
    result = {
        "mode": "offline_preflight_diagnosis",
        "model_calls_made": 0,
        "codex_model_started": False,
        "files_changed_by_script": 0,
    }
    try:
        pilot = Path(args.pilot).expanduser().resolve(strict=True)
        root = pilot / "benchmark-state.json"
        state_data = json.loads(root.read_text(encoding="utf-8"))
        result["experiment_state_valid"] = (
            state_data.get("schema_version") == 1 and
            state_data.get("candidate_commit") == runner.COMMIT
        )
        checks = (
            ("baseline_agents_match", "baseline-home", "baseline_sha256"),
            ("candidate_agents_match", "candidate-home", "candidate_sha256"),
            ("routing_config_match", "baseline-home", "config_sha256"),
        )
        for name, home, expected_field in checks:
            file_name = "config.toml" if name == "routing_config_match" else "AGENTS.md"
            target = pilot / home / file_name
            expected = state_data.get(expected_field)
            try:
                actual = runner.digest(runner.read_file(target))
                result[name] = isinstance(expected, str) and actual == expected
            except (OSError, ValueError):
                result[name] = False
        try:
            version = runner.call_codex(["--version"])
            result["cli_version_matches"] = (
                version.returncode == 0 and
                version.stdout.strip() == state_data.get("cli_version")
            )
        except (OSError, subprocess.TimeoutExpired):
            result["cli_version_matches"] = False
        try:
            declared = declared_sandbox_policy(pilot / "baseline-home")
            result["toml_parseable"] = True
            result["declared_policy"] = declared
        except (OSError, ValueError):
            result["toml_parseable"] = False
            result["declared_policy"] = None
        # Explain configuration-fingerprint drift without showing hashes,
        # TOML contents, paths, or credential fields. Never accept mismatches.
        try:
            baseline_bytes = runner.read_file(pilot / "baseline-home" / "config.toml")
            candidate_bytes = runner.read_file(pilot / "candidate-home" / "config.toml")
            expected = state_data.get("config_sha256")
            result["baseline_candidate_config_bytes_match"] = (
                baseline_bytes == candidate_bytes
            )
            result["candidate_config_matches_record"] = (
                isinstance(expected, str) and runner.digest(candidate_bytes) == expected
            )
            try:
                result["baseline_candidate_config_semantics_match"] = (
                    tomllib.loads(baseline_bytes.decode("utf-8")) ==
                    tomllib.loads(candidate_bytes.decode("utf-8"))
                )
            except (UnicodeError, ValueError):
                result["baseline_candidate_config_semantics_match"] = False
        except (OSError, ValueError):
            result["baseline_candidate_config_bytes_match"] = False
            result["candidate_config_matches_record"] = False
            result["baseline_candidate_config_semantics_match"] = False
        result["preflight_ready"] = all(
            result.get(field) is True for field in (
                "experiment_state_valid", "baseline_agents_match",
                "candidate_agents_match", "routing_config_match",
                "cli_version_matches", "toml_parseable",
            )
        ) and result["declared_policy"]["windows_sandbox"] not in (
            "disabled", "other_or_unrecognized",
        ) and result["declared_policy"]["sandbox_mode"] != "danger-full-access"
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        result["preflight_ready"] = False
        result["diagnostic_error_code"] = classified_error(exc)
    print(json.dumps(result, ensure_ascii=True, indent=2), flush=True)
    return 0


def validate_baseline_config_snapshot(pilot, stored, *, allow_sandbox_key_drift=False):
    """No mutations: accept only explicitly opted-in narrow sandbox-key drift.

    The original candidate config is the immutable byte-for-byte snapshot.
    Never weaken other routing, agent, sandbox or approval fields.
    """
    base_path = pilot / "baseline-home" / "config.toml"
    candidate_path = pilot / "candidate-home" / "config.toml"
    if base_path.is_symlink() or candidate_path.is_symlink():
        raise ValueError("ISOLATED_CONFIG_DRIFT_NOT_ALLOWLISTED")
    original = runner.read_file(candidate_path)
    actual = runner.read_file(base_path)
    expected = stored.get("config_sha256")
    if runner.digest(original) != expected:
        raise ValueError("ORIGINAL_CANDIDATE_CONFIG_CHANGED")
    if runner.digest(actual) == expected:
        return "strict_original_snapshot"
    if not allow_sandbox_key_drift:
        raise ValueError("ISOLATED_CONFIG_HASH_MISMATCH")

    original_toml = tomllib.loads(original.decode("utf-8"))
    actual_toml = tomllib.loads(actual.decode("utf-8"))
    # Deep-copy plain TOML dictionaries, so no state or live file is changed.
    import copy
    left, right = copy.deepcopy(original_toml), copy.deepcopy(actual_toml)
    def without_windows_sandbox(tree):
        windows = tree.get("windows")
        if windows is None:
            return None
        if not isinstance(windows, dict):
            raise ValueError("WINDOWS_CONFIG_INVALID")
        value = windows.pop("sandbox", None)
        if not windows:
            tree.pop("windows", None)
        return value

    old_sandbox = without_windows_sandbox(left)
    new_sandbox = without_windows_sandbox(right)
    if (left != right or
            old_sandbox not in (None, "mxc", "elevated") or
            new_sandbox not in (None, "mxc", "elevated")):
        raise ValueError("ISOLATED_CONFIG_DRIFT_NOT_ALLOWLISTED")
    return "opt_in_sandbox_key_or_format_drift"


def policy(args):
    """No model call, no file write: display declared fields and planned CLI override."""
    pilot = Path(args.pilot).expanduser().resolve(strict=True)
    stored = runner.state(pilot)
    home = pilot / "baseline-home"
    if home.is_symlink() or (home / "config.toml").is_symlink():
        raise ValueError("ISOLATED_PROFILE_INVALID")
    if runner.digest(runner.read_file(home / "config.toml")) != stored.get("config_sha256"):
        raise ValueError("ISOLATED_CONFIG_HASH_MISMATCH")
    declared = declared_sandbox_policy(home)
    if declared["windows_sandbox"] in ("disabled", "other_or_unrecognized"):
        raise ValueError("WINDOWS_SANDBOX_UNSUPPORTED")
    if declared["sandbox_mode"] == "danger-full-access":
        raise ValueError("SANDBOX_MODE_FULL_ACCESS_DECLARED")
    output = {
        "mode": "read_only_policy_preflight",
        "model_calls_made": 0,
        "codex_version_checked": True,
        "profile": "isolated_baseline",
        "declared_policy": declared,
        "planned_cli_override": {
            "approval": "never",
            "sandbox": "workspace-write",
        },
        "effective_runtime_permissions_verified": False,
        "normal_user_config_modified": False,
    }
    print(json.dumps(output, ensure_ascii=True, indent=2))
    return 0


def run(args):
    if not args.execute:
        raise ValueError("EXPLICIT_EXECUTE_REQUIRED")
    pilot, output = validate_paths(args.pilot, args.output, args.repo)
    stored = runner.state(pilot)
    approval = getattr(args, "approval", "on-request")
    windows_sandbox = getattr(args, "windows_sandbox", None)
    accept_drift = getattr(args, "accept_sandbox_key_drift", False)
    if accept_drift and (windows_sandbox != "mxc" or approval != "never"):
        raise ValueError("CONFIG_DRIFT_FLAG_REQUIRES_MXC_NEVER")
    if windows_sandbox not in (None, "mxc"):
        raise ValueError("WINDOWS_SANDBOX_OVERRIDE_UNSUPPORTED")
    if windows_sandbox == "mxc" and os.name != "nt":
        raise ValueError("WINDOWS_SANDBOX_OVERRIDE_REQUIRES_WINDOWS")
    if approval not in ("never", "on-request"):
        raise ValueError("APPROVAL_POLICY_INVALID")
    if stored.get("model") != MODEL:
        raise ValueError("MODEL_MISMATCH")
    if stored.get("reasoning_effort") != "medium" or stored.get("sandbox") != "workspace-write":
        raise ValueError("BENCHMARK_CONFIG_MISMATCH")
    home = pilot / "baseline-home"
    if home.is_symlink() or not home.is_dir() or (home / "config.toml").is_symlink():
        raise ValueError("ISOLATED_PROFILE_MISSING")
    config_check = validate_baseline_config_snapshot(
        pilot, stored, allow_sandbox_key_drift=accept_drift
    )
    declared = declared_sandbox_policy(home)
    if declared["windows_sandbox"] == "disabled":
        raise ValueError("WINDOWS_SANDBOX_DISABLED")
    if declared["sandbox_mode"] == "danger-full-access":
        raise ValueError("SANDBOX_MODE_FULL_ACCESS_DECLARED")
    if declared["windows_sandbox"] == "other_or_unrecognized":
        raise ValueError("WINDOWS_SANDBOX_MODE_UNKNOWN")
    check = runner.call_codex(["login", "status"], env=runner.home_env(pilot, "baseline"))
    if check.returncode:
        raise ValueError("ISOLATED_PROFILE_REQUIRES_LOGIN")
    executable = runner.resolve_codex_executable()
    if not executable:
        raise ValueError("CODEX_NOT_FOUND")
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    runner.make_fixture(workspace)
    # Durable sentinel before launching TUI; never automatically retry a run.
    runner.save_json(output / "run-started.json", {
        "schema_version": SCHEMA,
        "profile": "baseline",
        "execution_surface": "interactive-tui",
        "execute_authorized": True,
        "model": MODEL,
        "workspace_seeded": True,
        "approval_policy_override_requested": approval,
        "windows_sandbox_override_requested": windows_sandbox or "none",
        "baseline_config_snapshot_check": config_check,
        "declared_policy": declared,
    })
    env = runner.home_env(pilot, "baseline")
    # Do not ingest user transcripts or credentials. Keep normal TUI I/O,
    # allowing operator to see actual worker activity directly.
    prompt = (
        runner.PROMPT
        + " This is a SINGLE controlled interactive canary in a disposable repo. "
        "Use the luna-medium worker to implement and verify the scoped fix. "
        "Show the worker dispatch and result in the Codex TUI. "
        "After reporting verified results, STOP; do not start a second task. "
        "Do not modify config, install dependencies, approve access outside the workspace, "
        "or run network operations."
    )
    if approval == "never":
        prompt += (
            " This run explicitly forbids interactive command approvals. "
            "If any operation cannot proceed within workspace-write, report "
            "BLOCKED and STOP; do not request administrator rights, alter "
            "Windows sandbox settings, disable safeguards or escalate."
        )
    cmd = [
        executable, "--cd", str(workspace),
        "--model", MODEL, "--sandbox", "workspace-write",
        "--ask-for-approval", approval,
    ]
    if windows_sandbox == "mxc":
        # One-shot native Windows sandbox selection, no TOML or admin change.
        cmd += ["-c", "windows.sandbox=mxc"]
    cmd += ["-c", "model_reasoning_effort=medium", prompt]
    print("START: launching interactive Codex TUI, exactly one disposable task.", flush=True)
    print("SAFE_POLICY: sandbox=workspace-write approval_override=" + approval +
          " windows_sandbox_override=" + (windows_sandbox or "none"), flush=True)
    print("CONFIG_DECLARED: " + json.dumps(declared, sort_keys=True), flush=True)
    print("CONFIG_SNAPSHOT_CHECK: " + config_check, flush=True)
    if approval == "never":
        print("STOP if Windows UAC/admin/sandbox provisioning prompts appear. Do not approve elevation.", flush=True)
    print("The UI may persist its session in isolated baseline-home; no chats are read by this wrapper.", flush=True)
    print("Once the worker finishes, use /exit or Ctrl+C to close the TUI and obtain offline verification.", flush=True)
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=workspace, env=env, check=False)
        code = proc.returncode
    except OSError:
        code = None
    elapsed = time.monotonic() - started
    report = sanitized_report(workspace, code, elapsed, approval, declared,
                              windows_sandbox, config_check)
    runner.save_json(output / "sanitized-tui-result.json", report)
    print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)
    return 0 if code == 0 and report["functional_and_scope_pass"] else 1


def inspect(args):
    root = Path(args.output).expanduser().resolve(strict=True)
    if root.is_symlink() or not (root / "run-started.json").is_file():
        raise ValueError("TUI_CANARY_NOT_FOUND")
    workspace = root / "workspace"
    # No Codex run. Rechecks only deterministic fixture, preserves old evidence.
    checks = runner.verification_detail(workspace)
    report = {
        "schema_version": SCHEMA,
        "mode": "offline-reinspection-no-model-calls",
        "verification": checks,
        "worker_delegation_independently_verified": False,
        "note": "The TUI worker lifecycle must be independently observed in its interface.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pd = sub.add_parser("diagnose", help="Read-only categorized preflight: no model, no secrets.")
    pd.add_argument("--pilot", required=True)
    p0 = sub.add_parser("policy", help="Read-only policy/CLI fingerprint preflight; no model.")
    p0.add_argument("--pilot", required=True)
    p = sub.add_parser("run", help="One explicitly authorized interactive TUI invocation.")
    p.add_argument("--pilot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    p.add_argument("--execute", action="store_true")
    p.add_argument("--approval", choices=("on-request", "never"),
                   default="on-request", help="Override approvals for only this TUI invocation.")
    p.add_argument("--windows-sandbox", choices=("mxc",), default=None,
                   help="Windows only: one-shot MXC, without modifying config.toml.")
    p.add_argument("--accept-sandbox-key-drift", action="store_true",
                   help="Only with MXC/never: allow an explicitly reviewed Windows sandbox key or formatting drift; candidate must remain original.")
    q = sub.add_parser("inspect", help="Offline deterministic post-TUI check.")
    q.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "diagnose":
            return diagnose(args)
        if args.command == "policy":
            return policy(args)
        return run(args) if args.command == "run" else inspect(args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("STOP: " + classified_error(exc) + " (no private data printed).",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
