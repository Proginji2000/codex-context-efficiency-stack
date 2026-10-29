#!/usr/bin/env python3
"""Fail-closed, interactive repeat qualification for isolated Codex P1.1 V5.

Nothing is launched without --execute. One --execute authorizes at most
--pairs * 2 interactive TUI calls (maximum 4), with a fresh workspace each.
The operator must remain present for any folder-trust decision.
"""
import argparse
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
CONTRACT = "p1.1-git-diff-selfcheck-v2"
VERSION = "codex-cli 0.165.0"
REQUIRED_DIAG = (
    "experiment_state_valid", "baseline_agents_match",
    "candidate_agents_match", "routing_config_match",
    "candidate_config_matches_record",
    "baseline_candidate_config_bytes_match",
    "baseline_candidate_config_semantics_match",
    "cli_version_matches", "toml_parseable", "preflight_ready",
)
REQUIRED_CHECKS = (
    "fixture_present", "unittest_pass", "git_diff_check_pass",
    "modified_only_total_py", "no_untracked_files", "total_py_changed",
    "functional_and_scope_pass",
)


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def contexts():
    tui = module("p11_repeat_tui", "Run-CodexAB-TUI-Canary.py")
    baseline_restore = module("p11_repeat_baseline", "Restore-CodexAB-IsolatedBaseline.py")
    candidate_restore = module("p11_repeat_candidate", "Restore-CodexAB-IsolatedCandidate.py")
    return tui, baseline_restore, candidate_restore


def paths(pilot, repo, output_base, pairs):
    pilot = Path(pilot).expanduser().resolve(strict=True)
    repo = Path(repo).expanduser().resolve(strict=True)
    base = Path(output_base).expanduser().resolve()
    if base.is_symlink() or not pilot.is_dir() or not repo.is_dir():
        raise ValueError("UNSAFE_INPUT")
    planned = []
    for number in pairs:
        order = ("candidate", "baseline") if number == 2 else ("baseline", "candidate")
        for arm in order:
            output = Path(str(base) + "-pair%02d-%s" % (number, arm))
            planned.append((number, arm, output))
    if len({str(p) for _, _, p in planned}) != len(planned):
        raise ValueError("OUTPUT_COLLISION")
    return pilot, repo, planned


def check_cli_and_homes(tui, pilot):
    # Native executable resolution relies on the *temporary* caller PATH.
    runner = tui.runner
    actual = runner.call_codex(["--version"])
    if actual.returncode or actual.stdout.strip() != VERSION:
        raise ValueError("PINNED_CLI_VERSION_MISMATCH")
    state = runner.state(pilot)
    if state.get("cli_version") != VERSION:
        raise ValueError("PILOT_VERSION_MISMATCH")
    if (state.get("model") != "gpt-6-luna" or
            state.get("reasoning_effort") != "medium" or
            state.get("sandbox") != "workspace-write"):
        raise ValueError("PILOT_MODEL_POLICY_MISMATCH")
    for arm in ("baseline", "candidate"):
        home = pilot / (arm + "-home")
        if home.is_symlink() or not home.is_dir():
            raise ValueError("ISOLATED_HOME_INVALID")
        status = runner.call_codex(["login", "status"], env=runner.home_env(pilot, arm))
        if status.returncode:
            raise ValueError("ISOLATED_LOGIN_REQUIRED_" + arm.upper())
    return state


def restoration_target(tui, pilot, state):
    # Exactly one trusted source may be used if the other home drifted.
    expected = state["config_sha256"]
    actual = {}
    for arm in ("baseline", "candidate"):
        home = pilot / (arm + "-home")
        target = home / "config.toml"
        if home.is_symlink() or target.is_symlink():
            raise ValueError("CONFIG_SYMLINK")
        actual[arm] = tui.runner.digest(tui.runner.read_file(target)) == expected
    if all(actual.values()):
        return None
    if not any(actual.values()):
        raise ValueError("BOTH_CONFIGS_DRIFTED_NO_AUTOMATIC_RECOVERY")
    return "candidate" if actual["baseline"] else "baseline"


def preflight(tui, pilot):
    # Read-only checks; the candidate run already has a strict paired gate.
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = tui.diagnose(SimpleNamespace(pilot=str(pilot)))
    if rc:
        raise ValueError("DIAGNOSE_FAILED")
    diag = json.loads(out.getvalue())
    if not all(diag.get(k) is True for k in REQUIRED_DIAG):
        raise ValueError("PAIRED_PREFLIGHT_FAILED")
    for arm in ("baseline", "candidate"):
        with contextlib.redirect_stdout(io.StringIO()):
            rc = tui.policy(SimpleNamespace(pilot=str(pilot), arm=arm))
        if rc:
            raise ValueError("ARM_POLICY_FAILED_" + arm.upper())
    print("PAIR_PREFLIGHT_PASS: snapshots, role parity, sandbox policy and CLI", flush=True)


def restore_one(tui, restorers, pilot, state, pair, arm, allowed):
    target = restoration_target(tui, pilot, state)
    if target is None:
        return
    if not allowed:
        raise ValueError("DRIFT_REQUIRES_EXPLICIT_AUDITED_RESTORE")
    # No copy of secrets, AGENTS or session data: the existing audited
    # restorers archive only the changing isolated routing TOML.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    label = "backup-%s-p%02d-before-%s" % (stamp, pair, arm)
    print("AUDITED_CONFIG_RESTORE: " + target + " " + label, flush=True)
    restorer = restorers[0] if target == "baseline" else restorers[1]
    rc = restorer.restore(str(pilot), label, execute=True)
    if rc:
        raise ValueError("AUDITED_RESTORE_FAILED")
    if restoration_target(tui, pilot, state) is not None:
        raise ValueError("AUDITED_RESTORE_INCOMPLETE")


def verify_report(tui, output, arm):
    report_file = output / "sanitized-tui-result.json"
    if not report_file.is_file() or report_file.is_symlink():
        raise ValueError("RUN_REPORT_MISSING")
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if (report.get("arm") != arm or report.get("prompt_contract") != CONTRACT or
            report.get("model") != "gpt-6-luna" or
            report.get("windows_sandbox_override_requested") != "mxc" or
            report.get("approval_policy_override_requested") != "never" or
            report.get("codex_cli_exit_code") != 0 or
            report.get("functional_and_scope_pass") is not True):
        raise ValueError("RUN_ATTESTATION_MISMATCH")
    verified = tui.runner.verification_detail(output / "workspace")
    if not all(verified.get(k) is True for k in REQUIRED_CHECKS):
        raise ValueError("INDEPENDENT_REINSPECTION_FAILED")
    if not all(report["verification"].get(k) == verified.get(k) for k in REQUIRED_CHECKS):
        raise ValueError("REPORT_REINSPECTION_MISMATCH")
    return {
        "arm": arm, "prompt_contract": CONTRACT, "pass": True,
        "elapsed_s_including_operator": report["elapsed_s"],
        "worker_delegation_independently_verified": False,
        "token_counts": "not_collected_by_wrapper",
    }


def run(args):
    tui, baseline_restore, candidate_restore = contexts()
    pair_ids = tuple(range(args.start_pair, args.start_pair + args.pairs))
    if any(p not in (2, 3) for p in pair_ids):
        raise ValueError("PAIRS_MUST_BE_02_OR_03")
    pilot, repo, planned = paths(args.pilot, args.repo, args.output_base, pair_ids)
    state = check_cli_and_homes(tui, pilot)
    for _, _, output in planned:
        # Validate all destinations *before* the first model invocation.
        tui.validate_paths(str(pilot), str(output), str(repo))
    target = restoration_target(tui, pilot, state)
    print("P1.1_REPEAT_PLAN: " + ",".join(
        "p%02d:%s" % (p, arm) for p, arm, _ in planned), flush=True)
    print("PINNED_VERSION: " + VERSION, flush=True)
    print("PROMPT_CONTRACT: " + CONTRACT, flush=True)
    print("MAX_MODEL_CALLS: " + str(len(planned)), flush=True)
    if target:
        print("CONFIG_REQUIRES_AUDITED_RESTORE: " + target, flush=True)
    if not args.execute:
        print("PLAN_ONLY: no model calls, no configuration changes", flush=True)
        return 0
    if not args.audited_restore:
        raise ValueError("EXPLICIT_AUDITED_RESTORE_REQUIRED")
    summaries = []
    for pair, arm, output in planned:
        # Fresh independent gates before *every* paid call. Bail out on any
        # failure; never retry an existing output or run remaining trials.
        check_cli_and_homes(tui, pilot)
        restore_one(tui, (baseline_restore, candidate_restore),
                    pilot, state, pair, arm, allowed=args.audited_restore)
        preflight(tui, pilot)
        tui.validate_paths(str(pilot), str(output), str(repo))
        print("BEGIN_INTERACTIVE_CANARY: p%02d:%s" % (pair, arm), flush=True)
        rc = tui.run(SimpleNamespace(
            pilot=str(pilot), output=str(output), repo=str(repo),
            arm=arm, execute=True, approval="never", windows_sandbox="mxc",
            accept_sandbox_key_drift=False, python_test_fallback_hint=True,
        ))
        if rc:
            raise ValueError("RUN_FAILED_P%02d_%s_EVIDENCE_PRESERVED" % (pair, arm.upper()))
        record = verify_report(tui, output, arm)
        record["pair"] = pair
        summaries.append(record)
        print("INDEPENDENT_CANARY_PASS: p%02d:%s" % (pair, arm), flush=True)
    print(json.dumps({"qualification": "EXPERIMENTAL_REPEATS_PASS",
                      "results": summaries, "statistical_claim": False},
                     ensure_ascii=True, indent=2), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--repo", default=str(ROOT.parent))
    parser.add_argument("--output-base", required=True)
    parser.add_argument("--start-pair", type=int, choices=(2, 3), default=2)
    parser.add_argument("--pairs", type=int, choices=(1, 2), default=1)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--audited-restore", action="store_true",
                        help="Explicitly authorize archival and reset of drifted isolated TOMLs")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        # Only fixed internal error codes; never paths, config contents or auth.
        code = str(exc)
        safe = (
            code.isascii() and len(code) <= 100 and
            all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in code)
        )
        print("STOP: " + (code if safe else "QUALIFICATION_PRECONDITION_FAILED"),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
