#!/usr/bin/env python3
"""Read-only TUI A/B summary from independently checked disposable outputs.

Accepts an optional operator-supplied terminal capture. Only the allowlisted
BEGIN_INTERACTIVE_CANARY / Token usage / INDEPENDENT_CANARY_PASS lines are
parsed in memory. No raw log, Codex session, auth, or transcripts are saved.
No model calls, restores, worktree mutations, or configuration edits.
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = 1
DEFAULT_CONTRACT = "p1.1-git-diff-psfallback-v3"
ARMS = ("baseline", "candidate")
REQUIRED_CHECKS = (
    "fixture_present", "unittest_pass", "git_diff_check_pass",
    "modified_only_total_py", "no_untracked_files", "total_py_changed",
)
MAX_LOG_BYTES = 3_000_000
BEGIN = re.compile(r"^BEGIN_INTERACTIVE_CANARY: p(\d{2}):(baseline|candidate)$")
PASS = re.compile(r"^INDEPENDENT_CANARY_PASS: p(\d{2}):(baseline|candidate)$")
TOKEN = re.compile(
    r"^Token usage: total=([0-9\u202f\u00a0 ]+)"
    r" input=([0-9\u202f\u00a0 ]+)"
    r" \(\+ ([0-9\u202f\u00a0 ]+) cached\)"
    r" output=([0-9\u202f\u00a0 ]+)"
    r"(?: \(reasoning ([0-9\u202f\u00a0 ]+)\))?$"
)


class EvidenceError(ValueError):
    """Fixed, privacy-safe error codes only."""


def _finite_nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _strict_file(path):
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("MISSING_OR_LINKED_EVIDENCE")
    return path


def _number(text):
    value = text.replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    if not value.isascii() or not value.isdecimal():
        raise EvidenceError("TOKEN_FORMAT_INVALID")
    return int(value)


def planned_arms(start_pair, pairs):
    if type(start_pair) is not int or type(pairs) is not int or start_pair < 1 or pairs < 1 or pairs > 20:
        raise EvidenceError("INVALID_PAIR_RANGE")
    if start_pair + pairs - 1 > 99:
        raise EvidenceError("INVALID_PAIR_RANGE")
    return [
        (pair, arm)
        for pair in range(start_pair, start_pair + pairs)
        for arm in (("candidate", "baseline") if pair % 2 == 0 else ("baseline", "candidate"))
    ]


def _read_report(path, pair, arm, contract):
    report_path = _strict_file(path / "sanitized-tui-result.json")
    if report_path.stat().st_size > 100_000:
        raise EvidenceError("REPORT_TOO_LARGE")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError):
        raise EvidenceError("REPORT_UNREADABLE") from None
    if not isinstance(report, dict):
        raise EvidenceError("REPORT_INVALID")
    required = {
        "schema_version": 1,
        "arm": arm,
        "prompt_contract": contract,
        "execution_surface": "codex-interactive-tui-not-exec",
        "model": "gpt-6-luna",
        "sandbox": "workspace-write",
        "approval_policy_override_requested": "never",
        "windows_sandbox_override_requested": "mxc",
        "python_test_fallback_hint_requested": True,
        "codex_cli_exit_code": 0,
        "functional_and_scope_pass": True,
        "worker_delegation_independently_verified": False,
        "policy_effectiveness": "not_runtime_attested",
    }
    if any(type(report.get(k)) is not type(v) or report.get(k) != v for k, v in required.items()):
        raise EvidenceError("REPORT_CONTRACT_OR_ACCEPTANCE_MISMATCH")
    checks = report.get("verification")
    if (not isinstance(checks, dict) or
            any(checks.get(k) is not True for k in REQUIRED_CHECKS) or
            checks.get("unittest_exit_code") != 0 or
            checks.get("tracked_modified_file_count") != 1):
        raise EvidenceError("REPORT_QUALITY_GATES_FAILED")
    elapsed = report.get("elapsed_s")
    if not _finite_nonnegative(elapsed):
        raise EvidenceError("REPORT_ELAPSED_INVALID")
    return {"pair": pair, "arm": arm, "pass": True, "elapsed_s_including_operator": elapsed}, checks


def parse_terminal_capture(path, planned):
    """Extract numeric TUI counters with evidence order, never save raw text."""
    capture = _strict_file(Path(path))
    if capture.stat().st_size > MAX_LOG_BYTES:
        raise EvidenceError("TERMINAL_LOG_TOO_LARGE")
    try:
        lines = capture.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeError:
        raise EvidenceError("TERMINAL_LOG_UNREADABLE") from None
    current = None
    counters = {}
    passes = set()
    index = 0
    for line in lines:
        s = line.strip()
        started = BEGIN.fullmatch(s)
        finished = PASS.fullmatch(s)
        token_line = TOKEN.fullmatch(s)
        if started:
            key = (int(started.group(1)), started.group(2))
            if index >= len(planned) or key != planned[index]:
                raise EvidenceError("TERMINAL_ORDER_OR_DUPLICATE_INVALID")
            if current is not None and (current not in counters or current not in passes):
                raise EvidenceError("TERMINAL_EVIDENCE_INCOMPLETE")
            current = key
            index += 1
        elif s.startswith("Token usage:"):
            if current is None or current in counters or not token_line:
                raise EvidenceError("TERMINAL_USAGE_INVALID")
            total, input_tokens, cached_extra, output, reasoning = (
                _number(v) if v is not None else None for v in token_line.groups()
            )
            if total != input_tokens + output or (reasoning is not None and reasoning > output):
                raise EvidenceError("TERMINAL_USAGE_INCONSISTENT")
            counters[current] = {
                "total_reported_tokens": total,
                "input_reported_tokens": input_tokens,
                "additional_cached_reported_tokens": cached_extra,
                "output_reported_tokens": output,
                "reasoning_reported_tokens": reasoning,
            }
        elif finished:
            key = (int(finished.group(1)), finished.group(2))
            if key != current or key not in counters or key in passes:
                raise EvidenceError("TERMINAL_PASS_INVALID")
            passes.add(key)
    if index != len(planned) or len(counters) != len(planned) or len(passes) != len(planned):
        raise EvidenceError("TERMINAL_EVIDENCE_INCOMPLETE")
    return counters


def _pct(candidate, baseline):
    return round(100.0 * (candidate / baseline - 1), 2) if baseline else None


def analyze(output_base, start_pair=4, pairs=2, contract=DEFAULT_CONTRACT,
            terminal_log=None, recheck=False):
    if not isinstance(contract, str) or not re.fullmatch(r"p1\.1-[a-z0-9-]{1,80}", contract):
        raise EvidenceError("INVALID_CONTRACT")
    planned = planned_arms(start_pair, pairs)
    base = Path(output_base).expanduser()
    if base.is_symlink():
        raise EvidenceError("OUTPUT_BASE_LINK_FORBIDDEN")
    runs = []
    for pair, arm in planned:
        path = Path(str(base) + f"-pair{pair:02d}-{arm}")
        if path.is_symlink() or not path.is_dir():
            raise EvidenceError("MISSING_OR_LINKED_OUTPUT")
        row, reported_checks = _read_report(path, pair, arm, contract)
        if recheck:
            workspace = path / "workspace"
            if workspace.is_symlink() or not workspace.is_dir():
                raise EvidenceError("WORKSPACE_MISSING_OR_LINKED")
            # Offline deterministic Python/Git tests only; never opens Codex.
            module_path = Path(__file__).with_name("Run-CodexAB.py")
            spec = importlib.util.spec_from_file_location("codex_ab_tui_verifier", module_path)
            verifier = importlib.util.module_from_spec(spec)
            old_write_setting = sys.dont_write_bytecode
            try:
                sys.dont_write_bytecode = True
                spec.loader.exec_module(verifier)
            finally:
                sys.dont_write_bytecode = old_write_setting
            checks = verifier.verification_detail(workspace)
            names = (*REQUIRED_CHECKS, "unittest_exit_code", "tracked_modified_file_count")
            if any(checks.get(k) != reported_checks.get(k) for k in names):
                raise EvidenceError("INDEPENDENT_RECHECK_MISMATCH")
        runs.append(row)
    if terminal_log is not None:
        usage = parse_terminal_capture(terminal_log, planned)
        for run in runs:
            run["usage"] = usage[(run["pair"], run["arm"])]
    per_pair = []
    totals = {arm: {"reported_tokens": 0, "elapsed_s": 0.0} for arm in ARMS}
    for pair in range(start_pair, start_pair + pairs):
        two = {r["arm"]: r for r in runs if r["pair"] == pair}
        p = {"pair": pair, "both_pass": True}
        for arm in ARMS:
            totals[arm]["elapsed_s"] += two[arm]["elapsed_s_including_operator"]
            if terminal_log is not None:
                totals[arm]["reported_tokens"] += two[arm]["usage"]["total_reported_tokens"]
        if terminal_log is not None:
            b = two["baseline"]["usage"]["total_reported_tokens"]
            c = two["candidate"]["usage"]["total_reported_tokens"]
            p.update({"baseline_tokens": b, "candidate_tokens": c,
                      "candidate_delta_pct": _pct(c, b)})
        per_pair.append(p)
    for arm in ARMS:
        totals[arm]["elapsed_s"] = round(totals[arm]["elapsed_s"], 3)
        if terminal_log is None:
            totals[arm].pop("reported_tokens")
    combined = None
    if terminal_log is not None:
        combined = _pct(totals["candidate"]["reported_tokens"], totals["baseline"]["reported_tokens"])
    return {
        "schema_version": SCHEMA,
        "status": "functional_pass_efficiency_not_established",
        "contract": contract,
        "model_calls_made": 0,
        "restores_performed": 0,
        "files_written": 0,
        "run_count": len(runs),
        "runs": runs,
        "pairs": per_pair,
        "totals": totals,
        "candidate_combined_token_delta_pct_descriptive_only": combined,
        "token_source": "operator_supplied_terminal_capture" if terminal_log is not None else "not_available",
        "limitations": [
            "Terminal usage is a reported counter, not subscription quota or cost.",
            "Additional cached tokens are not added to reported totals.",
            "TUI worker lifecycle and effective sandbox policy are not independently attested.",
            "Two pairs do not establish a statistically reliable efficiency improvement.",
            "Duration includes operator interaction and cannot be treated as worker-only latency.",
            "Terminal text is parsed by allowlist in memory; provenance is operator supplied, not cryptographically bound to run outputs.",
        ],
        "merge_authorized": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-base", required=True, help="Prefix for existing disposable output directories")
    p.add_argument("--start-pair", type=int, default=4)
    p.add_argument("--pairs", type=int, default=2)
    p.add_argument("--contract", default=DEFAULT_CONTRACT)
    p.add_argument("--terminal-log", help="Optional operator-supplied terminal capture; processed in memory only")
    p.add_argument("--recheck", action="store_true", help="Rerun offline Python/Git acceptance checks")
    args = p.parse_args(argv)
    try:
        result = analyze(args.output_base, args.start_pair, args.pairs,
                         args.contract, args.terminal_log, args.recheck)
    except (EvidenceError, OSError, TypeError, KeyError) as exc:
        code = str(exc) if isinstance(exc, EvidenceError) else "OFFLINE_EVIDENCE_UNAVAILABLE"
        print("STOP: " + code, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
