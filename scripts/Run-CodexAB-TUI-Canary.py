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
            "elevated", "unelevated", "disabled",
        }:
            output[name] = value
        else:
            output[name] = "other_or_unrecognized"
    return output


def sanitized_report(workspace, exit_code, elapsed, approval="on-request", declared_policy=None):
    checks = runner.verification_detail(workspace)
    # No TUI tool/event stream is available to this wrapper; evidence from the
    # interactive UI must be assessed separately, never synthesized.
    return {
        "schema_version": SCHEMA,
        "execution_surface": "codex-interactive-tui-not-exec",
        "model": MODEL,
        "sandbox": "workspace-write",
        "approval_policy_override_requested": approval,
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


def run(args):
    if not args.execute:
        raise ValueError("EXPLICIT_EXECUTE_REQUIRED")
    pilot, output = validate_paths(args.pilot, args.output, args.repo)
    stored = runner.state(pilot)
    approval = getattr(args, "approval", "on-request")
    if approval not in ("never", "on-request"):
        raise ValueError("APPROVAL_POLICY_INVALID")
    if stored.get("model") != MODEL:
        raise ValueError("MODEL_MISMATCH")
    if stored.get("reasoning_effort") != "medium" or stored.get("sandbox") != "workspace-write":
        raise ValueError("BENCHMARK_CONFIG_MISMATCH")
    home = pilot / "baseline-home"
    if home.is_symlink() or not home.is_dir() or (home / "config.toml").is_symlink():
        raise ValueError("ISOLATED_PROFILE_MISSING")
    if runner.digest(runner.read_file(home / "config.toml")) != stored.get("config_sha256"):
        raise ValueError("ISOLATED_CONFIG_HASH_MISMATCH")
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
        "-c", "model_reasoning_effort=medium", prompt,
    ]
    print("START: launching interactive Codex TUI, exactly one disposable task.", flush=True)
    print("SAFE_POLICY: sandbox=workspace-write approval_override=" + approval, flush=True)
    print("CONFIG_DECLARED: " + json.dumps(declared, sort_keys=True), flush=True)
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
    report = sanitized_report(workspace, code, elapsed, approval, declared)
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
    p = sub.add_parser("run", help="One explicitly authorized interactive TUI invocation.")
    p.add_argument("--pilot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    p.add_argument("--execute", action="store_true")
    p.add_argument("--approval", choices=("on-request", "never"),
                   default="on-request", help="Override approvals for only this TUI invocation.")
    q = sub.add_parser("inspect", help="Offline deterministic post-TUI check.")
    q.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        return run(args) if args.command == "run" else inspect(args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired):
        print("STOP: TUI_CANARY_PRECONDITION_OR_INSPECTION_FAILED; no private data printed.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
